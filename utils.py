import os
import logging
import httpx
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.resolve()
FONT_FILENAME = "DejaVuSans.ttf"
FONT_PATH = BASE_DIR / FONT_FILENAME

# FIX: Используем Google Fonts CDN для стабильности
FONT_URL = (
    "https://fonts.gstatic.com/s/"
    "dejavusans/v27/DejaVuSans.ttf"
)

def ensure_font_exists() -> str | None:
    """
    Проверяет наличие шрифта. Если его нет — скачивает.
    Возвращает путь к шрифту или None (graceful degradation).
    """
    try:
        if FONT_PATH.exists():
            logger.info(f"✅ Шрифт найден: {FONT_PATH}")
            return str(FONT_PATH)

        logger.info(f"⬇️ Скачиваю шрифт с {FONT_URL}...")
        
        # Используем httpx с таймаутом для надежности, как и ранее
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            response = client.get(FONT_URL)
            response.raise_for_status() # Вызывает исключение для HTTP ошибок

            FONT_PATH.write_bytes(response.content) # Сохраняем как байты
            
        logger.info("✅ Шрифт успешно сохранён.")
        return str(FONT_PATH)

    except Exception:
        logger.exception("❌ Не удалось загрузить шрифт")
        return None