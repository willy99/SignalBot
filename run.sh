#!/bin/bash

echo ">>> Запуск Nginx..."
# Запускаємо nginx у фоновому режимі
cd "C:/work/install/nginx-1.28.3/"
./nginx.exe &

echo ">>> Запуск бота..."
cd "C:/work/SignalBot"
source venv/Scripts/activate
python bot.py