import os
import logging
import httpx
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.resolve()
FONT_FILENAME = "DejaVuSans.ttf"
FONT_PATH = BASE_DIR / FONT_FILENAME
# Исправленная ссылка (папка ttf)
FONT_URL = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf"

def ensure_font_exists() -> str:
    """
    Проверяет наличие шрифта. Если его нет — скачивает.
    Возвращает путь к шрифту.
    """
    if FONT_PATH.exists():
        logger.info(f"✅ Шрифт найден: {FONT_PATH}")
        return str(FONT_PATH)

    logger.info(f"⬇️ Скачиваю шрифт с {FONT_URL}...")
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            response = client.get(FONT_URL)
            response.raise_for_status()
            
            with open(FONT_PATH, "wb") as f:
                f.write(response.content)
                
        logger.info(f"✅ Шрифт успешно сохранён: {FONT_PATH}")
        return str(FONT_PATH)
    except Exception as e:
        logger.error(f"❌ Ошибка скачивания шрифта: {e}")
        return None