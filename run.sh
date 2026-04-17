#!/bin/bash

cd "C:/work/install/nginx-1.28.3/"
./nginx.exe -s stop 2>/dev/null
sleep 2

echo ">>> Запуск Nginx..."
# Запускаємо nginx у фоновому режимі
cd "C:/work/install/nginx-1.28.3/"
./nginx.exe &

echo ">>> Запуск бота..."
cd "C:/work/SignalBot"
source venv/Scripts/activate
python bot.py
