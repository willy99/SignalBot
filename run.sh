#!/bin/bash

# 1. Шляхи краще винести в змінні для зручності
NGINX_PATH="C:/work/install/nginx-1.28.3/"
SIGNAL_PATH="c:/work/install/signal-cli-0.14.2/bin"
BOT_PATH="C:/work/SignalBot"

echo ">>> Зупинка старих процесів..."
# Вбиваємо попередні екземпляри, якщо вони зависли
taskkill //F //IM nginx.exe //T 2>/dev/null
taskkill //F //IM java.exe //T 2>/dev/null # signal-cli працює на java

sleep 2

# 2. Запуск Nginx
echo ">>> Запуск Nginx..."
cd "$NGINX_PATH"
start ./nginx.exe  # Команда start у Windows краща для GUI/сервісних додатків

# 3. Запуск Signal CLI у фоновому режимі
echo ">>> Запуск Signal CLI (Daemon)..."
cd "$SIGNAL_PATH"
# Використовуємо '&', щоб bash не чекав, і перенаправляємо вивід у лог
./signal-cli --account +380938513200 daemon --tcp 127.0.0.1:1234 > "$BOT_PATH/signal_cli.log" 2>&1 &

# Даємо трохи часу демону ініціалізуватися
sleep 10

# 4. Запуск основного бота
echo ">>> Запуск основного бота..."
cd "$BOT_PATH"
source venv/Scripts/activate

# Запускаємо бота (він буде активним процесом у цьому вікні)
python bot.py