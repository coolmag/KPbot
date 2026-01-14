from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Путь к локальному шрифту в репозитории
FONT_PATH = Path(__file__).parent / "assets" / "fonts" / "DejaVuSans.ttf"

def ensure_font_exists() -> str | None:
    """
    Проверяет, существует ли шрифт локально в репозитории.
    Возвращает путь к файлу или None, если он отсутствует.
    """
    if FONT_PATH.exists():
        logger.info(f"✅ Шрифт найден локально: {FONT_PATH}")
        return str(FONT_PATH)

    # Если файл не найден, выводим критическую ошибку.
    # Скачивания из интернета больше нет.
    logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА: Файл шрифта не найден по пути {FONT_PATH}. "
                 f"Пожалуйста, добавьте DejaVuSans.ttf в директорию 'assets/fonts/'.")
    return None
