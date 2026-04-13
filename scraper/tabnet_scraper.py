#!/usr/bin/env python3
"""
Robô de Extração de Dados - DATASUS TabNet
Produção Ambulatorial (SIA/SUS) - Por local de atendimento - a partir de 2008

Extrai dados de Quantidade Aprovada e Valor Aprovado por Município e Subgrupo
de Procedimento, para o período de Jan/2024 a Jan/2026.

Uso:
    python -m scraper.tabnet_scraper [--test] [--months N]
"""

import os
import sys
import time
import argparse
import logging
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    StaleElementReferenceException, WebDriverException
)

try:
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    ChromeDriverManager = None

from scraper.config import (
    TABNET_FORM_URL, CSV_OUTPUT_DIR, PERIODOS,
    PERIODO_LABELS, CONTEUDOS, FORM_VALUES,
    DELAY_BETWEEN_REQUESTS, PAGE_LOAD_TIMEOUT, ELEMENT_WAIT_TIMEOUT
)
from scraper.utils import setup_logging, sanitize_filename, retry_with_backoff

logger = logging.getLogger(__name__)


class TabNetScraper:
    """Scraper para extração de dados do DATASUS TabNet."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
        self.wait = None
        self.extracted_files = []
        self.errors = []

    def _init_driver(self):
        """Inicializa o Chrome WebDriver."""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # Preferências para download
        prefs = {
            "download.default_directory": CSV_OUTPUT_DIR,
            "download.prompt_for_download": False,
        }
        chrome_options.add_experimental_option("prefs", prefs)

        try:
            if ChromeDriverManager:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                self.driver = webdriver.Chrome(options=chrome_options)
        except WebDriverException:
            # Fallback: try without service manager
            self.driver = webdriver.Chrome(options=chrome_options)

        self.driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        self.wait = WebDriverWait(
            self.driver, ELEMENT_WAIT_TIMEOUT,
            ignored_exceptions=[StaleElementReferenceException]
        )
        logger.info("WebDriver Chrome inicializado com sucesso")

    def _navigate_to_form(self):
        """Navega até o formulário do TabNet."""
        logger.info(f"Navegando para: {TABNET_FORM_URL}")
        self.driver.get(TABNET_FORM_URL)
        # Aguardar carregamento do formulário
        self.wait.until(EC.presence_of_element_located((By.NAME, "Linha")))
        logger.info("Formulário TabNet carregado com sucesso")

    def _select_option(self, select_name: str, value: str, by_visible_text: bool = True):
        """Seleciona uma opção em um campo SELECT."""
        try:
            element = self.wait.until(
                EC.presence_of_element_located((By.NAME, select_name))
            )
            select = Select(element)
            if by_visible_text:
                select.select_by_visible_text(value)
            else:
                select.select_by_value(value)
            logger.info(f"Selecionado {select_name} = '{value}'")
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Erro ao selecionar {select_name}='{value}': {e}")
            # Tenta alternativas
            select = Select(self.driver.find_element(By.NAME, select_name))
            options_text = [opt.text for opt in select.options]
            logger.info(f"Opções disponíveis para {select_name}: {options_text[:10]}...")
            # Tenta match parcial
            for opt in select.options:
                if value.lower() in opt.text.lower():
                    select.select_by_visible_text(opt.text)
                    logger.info(f"Match parcial: selecionado '{opt.text}'")
                    return
            raise

    def _select_periods(self, period_codes: list):
        """Seleciona os períodos no multi-select."""
        try:
            element = self.wait.until(
                EC.presence_of_element_located((By.NAME, "Arquivos"))
            )
            select = Select(element)

            # Desselecionar tudo primeiro
            try:
                select.deselect_all()
            except Exception:
                pass

            selected_count = 0
            for code in period_codes:
                try:
                    select.select_by_value(code)
                    selected_count += 1
                except NoSuchElementException:
                    logger.warning(f"Período não encontrado: {code}")

            logger.info(f"Selecionados {selected_count}/{len(period_codes)} períodos")
            return selected_count > 0
        except Exception as e:
            logger.error(f"Erro ao selecionar períodos: {e}")
            raise

    def _select_content(self, content_value: str):
        """Seleciona o conteúdo (Qtd.aprovada ou Valor aprovado)."""
        try:
            element = self.wait.until(
                EC.presence_of_element_located((By.NAME, "Incremento"))
            )
            select = Select(element)
            select.select_by_visible_text(content_value)
            logger.info(f"Conteúdo selecionado: {content_value}")
        except Exception:
            # Tenta match parcial
            element = self.driver.find_element(By.NAME, "Incremento")
            select = Select(element)
            for opt in select.options:
                if content_value.lower().replace(" ", "") in opt.text.lower().replace(" ", ""):
                    select.select_by_visible_text(opt.text)
                    logger.info(f"Conteúdo selecionado (match parcial): {opt.text}")
                    return
            raise

    def _check_zeradas(self):
        """Marca a checkbox 'Exibir linhas zeradas'."""
        try:
            checkboxes = self.driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
            for cb in checkboxes:
                name = cb.get_attribute("name") or ""
                value = cb.get_attribute("value") or ""
                # A checkbox de zeradas pode ter diferentes atributos
                if "zero" in name.lower() or "zero" in value.lower() or "zerada" in name.lower():
                    if not cb.is_selected():
                        cb.click()
                        logger.info("Checkbox 'Exibir linhas zeradas' marcada")
                    return True

            # Tenta encontrar por texto próximo
            labels = self.driver.find_elements(By.TAG_NAME, "label")
            for label in labels:
                if "zerada" in label.text.lower():
                    cb = label.find_element(By.TAG_NAME, "input")
                    if not cb.is_selected():
                        cb.click()
                    logger.info("Checkbox 'Exibir linhas zeradas' marcada (via label)")
                    return True

            # Tenta encontrar checkbox genérica para linhas zeradas
            # No TabNet, geralmente há checkboxes sem labels explícitas
            for cb in checkboxes:
                parent_text = cb.find_element(By.XPATH, "..").text.lower()
                if "zerada" in parent_text or "zero" in parent_text:
                    if not cb.is_selected():
                        cb.click()
                    logger.info("Checkbox zeradas marcada (via parent text)")
                    return True

            logger.warning("Checkbox 'Exibir linhas zeradas' não encontrada")
            return False
        except Exception as e:
            logger.warning(f"Erro ao marcar zeradas: {e}")
            return False

    def _select_csv_format(self):
        """Seleciona o formato 'Colunas separadas por ;' (prn)."""
        try:
            radios = self.driver.find_elements(By.CSS_SELECTOR, "input[type='radio'][name='formato']")
            for radio in radios:
                value = radio.get_attribute("value") or ""
                if value.lower() == "prn":
                    radio.click()
                    logger.info("Formato CSV/PRN selecionado (value='prn')")
                    return True

            logger.warning("Radio de formato prn não encontrado")
            return False
        except Exception as e:
            logger.warning(f"Erro ao selecionar formato prn: {e}")
            return False

    def _click_mostra(self):
        """Clica no botão 'Mostra' para submeter o formulário."""
        try:
            button = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input[value='Mostra']"))
            )
            button.click()
            logger.info("Botão 'Mostra' clicado - aguardando resultado...")
            time.sleep(3)
            return True
        except Exception:
            # Tenta alternativas
            try:
                buttons = self.driver.find_elements(By.CSS_SELECTOR, "input[type='submit'], input[type='button']")
                for btn in buttons:
                    if "mostra" in (btn.get_attribute("value") or "").lower():
                        btn.click()
                        logger.info("Botão 'Mostra' clicado (alternativo)")
                        time.sleep(3)
                        return True
            except Exception as e2:
                logger.error(f"Não foi possível clicar em Mostra: {e2}")
            return False

    def _extract_csv_content(self) -> str:
        """
        Após clicar Mostra, extrai o conteúdo CSV da página de resultados.
        O TabNet redireciona para uma página com a tabela ou CSV.
        """
        try:
            # Aguardar redirecionamento
            time.sleep(5)

            # Verificar se há um link para download de CSV
            links = self.driver.find_elements(By.TAG_NAME, "a")
            csv_link = None
            for link in links:
                href = link.get_attribute("href") or ""
                text = link.text.lower()
                if ".csv" in href.lower() or "csv" in text or "separad" in text:
                    csv_link = href
                    break

            if csv_link:
                # Navegar para o link do CSV
                self.driver.get(csv_link)
                time.sleep(3)
                content = self.driver.find_element(By.TAG_NAME, "body").text
                logger.info(f"CSV obtido via link. Tamanho: {len(content)} chars")
                return content

            # Se não houver link, o conteúdo está na própria página
            # TabNet no modo CSV mostra texto puro com delimitador ;
            body = self.driver.find_element(By.TAG_NAME, "body")
            content = body.text

            # Verificar se é conteúdo PRE (texto pré-formatado)
            try:
                pre = self.driver.find_element(By.TAG_NAME, "pre")
                content = pre.text
                logger.info(f"CSV obtido via tag PRE. Tamanho: {len(content)} chars")
                return content
            except NoSuchElementException:
                pass

            # Verificar se há tabela HTML (modo tabela com bordas)
            try:
                tables = self.driver.find_elements(By.TAG_NAME, "table")
                if tables:
                    # Converter tabela HTML para CSV
                    return self._table_to_csv(tables[0])
            except Exception:
                pass

            logger.info(f"Conteúdo obtido do body. Tamanho: {len(content)} chars")
            return content

        except Exception as e:
            logger.error(f"Erro ao extrair conteúdo CSV: {e}")
            raise

    def _table_to_csv(self, table_element) -> str:
        """Converte uma tabela HTML para formato CSV com separador ;."""
        rows = table_element.find_elements(By.TAG_NAME, "tr")
        csv_lines = []
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "th") + row.find_elements(By.TAG_NAME, "td")
            values = [cell.text.strip().replace(";", ",") for cell in cells]
            csv_lines.append(";".join(values))
        return "\n".join(csv_lines)

    def _save_csv(self, content: str, content_type: str, period_label: str) -> str:
        """Salva o conteúdo CSV em arquivo."""
        os.makedirs(CSV_OUTPUT_DIR, exist_ok=True)
        filename = sanitize_filename(
            f"producao_ambulatorial_{content_type}_{period_label}.csv"
        )
        filepath = os.path.join(CSV_OUTPUT_DIR, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"CSV salvo: {filepath} ({len(content)} bytes)")
        return filepath

    def extract_single(self, period_code: str, content_key: str, content_label: str) -> str:
        """
        Extrai dados para um único período e tipo de conteúdo.
        Retorna o caminho do arquivo CSV salvo.
        """
        period_label = PERIODO_LABELS.get(period_code, period_code)
        logger.info(f"=== Extraindo: {content_label} - {period_label} ===")

        try:
            # Navegar para o formulário
            self._navigate_to_form()
            time.sleep(2)

            # Configurar campos do formulário
            self._select_option("Linha", FORM_VALUES["linha"])
            self._select_option("Coluna", FORM_VALUES["coluna"])
            self._select_content(content_label)
            self._select_periods([period_code])
            self._check_zeradas()
            self._select_csv_format()

            # Submeter
            if not self._click_mostra():
                raise Exception("Falha ao clicar no botão Mostra")

            # Extrair resultado
            content = self._extract_csv_content()

            if not content or len(content) < 50:
                logger.error(f"TEXTO OBTIDO: '{content}'")
                raise Exception(f"Conteúdo CSV muito pequeno ou vazio: {len(content) if content else 0} chars")

            # Salvar
            filepath = self._save_csv(content, content_key, period_label.replace("/", "-"))
            self.extracted_files.append(filepath)
            return filepath

        except Exception as e:
            error_msg = f"Erro na extração {content_label}/{period_label}: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            return ""

    def extract_all(self, periodos: list = None, conteudos: dict = None):
        """
        Executa extração completa para todos os períodos e conteúdos.
        """
        if periodos is None:
            periodos = PERIODOS
        if conteudos is None:
            conteudos = CONTEUDOS

        total = len(periodos) * len(conteudos)
        current = 0

        logger.info(f"Iniciando extração de {total} combinações")
        logger.info(f"Períodos: {len(periodos)}, Conteúdos: {len(conteudos)}")

        for content_key, content_label in conteudos.items():
            for period_code in periodos:
                current += 1
                logger.info(f"--- Progresso: {current}/{total} ---")

                try:
                    def do_extract():
                        return self.extract_single(period_code, content_key, content_label)

                    filepath = retry_with_backoff(do_extract, max_retries=3, initial_delay=5)

                    if filepath:
                        logger.info(f"✓ Sucesso: {filepath}")
                    else:
                        logger.warning(f"✗ Falha sem exceção para {content_key}/{period_code}")

                except Exception as e:
                    logger.error(f"✗ Falha definitiva: {content_key}/{period_code}: {e}")

                # Delay entre requisições
                if current < total:
                    delay = DELAY_BETWEEN_REQUESTS
                    logger.info(f"Aguardando {delay}s antes da próxima extração...")
                    time.sleep(delay)

        # Relatório final
        logger.info("=" * 60)
        logger.info("EXTRAÇÃO FINALIZADA")
        logger.info(f"Arquivos extraídos: {len(self.extracted_files)}/{total}")
        logger.info(f"Erros: {len(self.errors)}")
        if self.errors:
            for err in self.errors:
                logger.error(f"  - {err}")
        logger.info("=" * 60)

    def start(self):
        """Inicializa o driver."""
        self._init_driver()

    def stop(self):
        """Encerra o driver."""
        if self.driver:
            self.driver.quit()
            logger.info("WebDriver encerrado")


def main():
    parser = argparse.ArgumentParser(description="DATASUS TabNet Scraper - Produção Ambulatorial")
    parser.add_argument("--test", action="store_true", help="Modo teste: extrai apenas 1 mês")
    parser.add_argument("--months", type=int, default=0, help="Número de meses a extrair (0=todos)")
    parser.add_argument("--no-headless", action="store_true", help="Executar com navegador visível")
    parser.add_argument("--content", choices=["qtd", "valor", "ambos"], default="ambos",
                        help="Tipo de conteúdo a extrair")
    args = parser.parse_args()

    setup_logging()

    # Configurar períodos
    periodos = PERIODOS
    if args.test:
        periodos = PERIODOS[:1]  # Apenas Jan/2024
        logger.info("MODO TESTE: Extraindo apenas 1 período")
    elif args.months > 0:
        periodos = PERIODOS[:args.months]
        logger.info(f"Extraindo {args.months} primeiros períodos")

    # Configurar conteúdos
    conteudos = CONTEUDOS
    if args.content == "qtd":
        conteudos = {"quantidade_aprovada": CONTEUDOS["quantidade_aprovada"]}
    elif args.content == "valor":
        conteudos = {"valor_aprovado": CONTEUDOS["valor_aprovado"]}

    scraper = TabNetScraper(headless=not args.no_headless)

    try:
        scraper.start()
        scraper.extract_all(periodos=periodos, conteudos=conteudos)
    except KeyboardInterrupt:
        logger.info("Extração interrompida pelo usuário")
    finally:
        scraper.stop()

    # Resumo
    print(f"\n{'='*60}")
    print(f"Arquivos extraídos: {len(scraper.extracted_files)}")
    print(f"Erros: {len(scraper.errors)}")
    for f in scraper.extracted_files:
        print(f"  ✓ {f}")
    print(f"{'='*60}")

    return 0 if not scraper.errors else 1


if __name__ == "__main__":
    sys.exit(main())
