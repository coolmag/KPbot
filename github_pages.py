import base64
import requests
import os
import logging

logger = logging.getLogger(__name__)

# Загружаем токен и настройки из переменных окружения
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OWNER = os.getenv("GITHUB_OWNER", "coolmag")
REPO = os.getenv("GITHUB_REPO", "KPbot")


def upload_page(filename: str, content: str):
    """
    Загружает сгенерированную HTML страницу в репозиторий GitHub через API.
    Это создает или перезаписывает файл.
    """
    if not GITHUB_TOKEN:
        logger.error("GITHUB_TOKEN не найден! Не могу загрузить страницу на GitHub.")
        return

    path = f"proposals/{filename}"
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{path}"

    # Кодируем контент в Base64
    encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')

    # Данные для коммита
    data = {
        "message": f"feat: Add/update proposal {filename}",
        "content": encoded_content,
        "committer": {
            "name": "KPbot AI",
            "email": "bot@kp-generator.ai"
        }
    }
    
    # Заголовки для аутентификации
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    try:
        # Проверяем, существует ли файл в ветке gh-pages, чтобы получить SHA для обновления
        get_response = requests.get(url, headers=headers, params={"ref": "gh-pages"})
        if get_response.status_code == 200:
            data['sha'] = get_response.json()['sha']
            logger.info(f"Файл {path} существует в ветке gh-pages. Обновляю его.")
        else:
            logger.info(f"Файл {path} не найден в ветке gh-pages. Создаю новый.")

        # Указываем ветку gh-pages для коммита
        data['branch'] = 'gh-pages'

        # Отправляем запрос на создание/обновление файла
        response = requests.put(url, json=data, headers=headers)
        response.raise_for_status()  # Вызовет исключение для статусов 4xx/5xx
        
        logger.info(f"✅ Успешно загружен файл {filename} в ветку 'gh-pages' репозитория {OWNER}/{REPO}.")
        logger.debug(f"Ответ GitHub API: {response.json()}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при загрузке файла в GitHub: {e}")
        if e.response is not None:
            logger.error(f"Тело ответа: {e.response.text}")

