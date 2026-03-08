#!/bin/bash

# Ожидаем доступности Redis (опционально, но полезно)
sleep 2

# 1. Запуск Telegram-бота в фоновом режиме
python bot.py &

# 2. Запуск Celery-воркера для тяжелых задач (генерация КП, AI, PDF) в фоновом режиме
celery -A celery_worker.celery_app worker --loglevel=info &

# 3. Запуск FastAPI-сервера (для обработки вебхуков телеметрии и AI-агента с фронтенда)
uvicorn web_server:app --host 0.0.0.0 --port ${PORT:-8080}