"""Скрипт для скачивания шрифта с поддержкой кириллицы."""
import urllib.request
import os
import sys

url = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/fonts/DejaVuSans.ttf"
output = "DejaVuSans.ttf"

# Проверяем, существует ли файл, чтобы не качать лишний раз
if os.path.exists(output):
    print(f"✅ Шрифт {output} уже существует.")
    sys.exit(0)

print(f"Скачиваю шрифт...")
try:
    urllib.request.urlretrieve(url, output)
    print(f"✅ Шрифт сохранён: {output}")
except Exception as e:
    print(f"❌ Ошибка скачивания шрифта: {e}")
    sys.exit(1)

