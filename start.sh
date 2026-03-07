#!/bin/bash

# Запускаем веб-сервер в фоне
uvicorn web_server:app --host 0.0.0.0 --port $PORT &

# Запускаем Telegram-бота в фоне
python bot.py &

# Запускаем Celery-воркера в фоне
celery -A celery_worker.celery_app worker --loglevel=info &

# Ждем завершения процессов (чтобы контейнер не упал)
wait -n
