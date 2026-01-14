"""Скрипт для скачивания шрифта с поддержкой кириллицы."""
import urllib.request
import os

url = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/fonts/DejaVuSans.ttf"
output = "DejaVuSans.ttf"

print(f"Скачиваю шрифт...")
try:
    urllib.request.urlretrieve(url, output)
    print(f"✅ Шрифт сохранён: {output}")
except Exception as e:
    print(f"❌ Ошибка: {e}")
    print("Альтернатива: скачай вручную с https://dejavu-fonts.github.io/Download.html")
