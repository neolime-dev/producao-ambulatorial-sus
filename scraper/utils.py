"""
Funções auxiliares para o Scraper DATASUS TabNet
"""
import os
import re
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)


def setup_logging(log_dir=None):
    """Configura logging para o scraper."""
    if log_dir is None:
        from scraper.config import BASE_DIR
        log_dir = os.path.join(BASE_DIR, "data")

    os.makedirs(log_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"scraper_{timestamp}.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler()
        ]
    )
    logger.info(f"Log iniciado em: {log_file}")
    return log_file


def sanitize_filename(name: str) -> str:
    """Remove caracteres especiais de nomes de arquivo."""
    name = re.sub(r'[^\w\s\-.]', '', name)
    name = re.sub(r'\s+', '_', name)
    return name


def parse_tabnet_csv(content: str, separator: str = ";") -> list:
    """
    Faz parsing do conteúdo CSV retornado pelo TabNet.
    Remove cabeçalhos e rodapés extras que o TabNet inclui.
    """
    lines = content.strip().split("\n")
    data_lines = []
    in_data = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_data:
                break
            continue

        # Detecta início dos dados (primeira linha com separador após cabeçalho)
        if separator in stripped and not stripped.startswith("\"Fonte"):
            in_data = True
            data_lines.append(stripped)
        elif in_data:
            if stripped.startswith("\"Fonte") or stripped.startswith("\"Total"):
                # Podemos incluir Total ou não
                if stripped.startswith("\"Total"):
                    data_lines.append(stripped)
                break
            data_lines.append(stripped)

    return data_lines


def retry_with_backoff(func, max_retries=3, initial_delay=5):
    """
    Executa uma função com retry e backoff exponencial.
    """
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"Falha após {max_retries} tentativas: {e}")
                raise
            delay = initial_delay * (2 ** attempt)
            logger.warning(f"Tentativa {attempt + 1} falhou: {e}. Aguardando {delay}s...")
            time.sleep(delay)


def format_period_label(period_code: str) -> str:
    """Converte código de período (qabrYYMM.dbf) para label legível (Mmm/YYYY)."""
    from scraper.config import PERIODO_LABELS
    return PERIODO_LABELS.get(period_code, period_code)
