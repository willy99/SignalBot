import os
import re
from nicegui import ui
from config import LOG_MONITORING_MAX_LINES
from gui.components import menu

# Регулярний вираз для парсингу логу: Дата/Час - РІВЕНЬ - Повідомлення
LOG_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2},\d{3})\s-\s([A-Z]+)\s-\s(.*)$")

def format_log_line(line: str) -> str:
    """Форматує рядок логу в HTML з кольорами"""
    line = line.strip()
    if not line:
        return ""

    # Екрануємо символи < та >, щоб логи не ламали HTML-верстку
    line = line.replace('<', '&lt;').replace('>', '&gt;')

    match = LOG_PATTERN.match(line)
    if match:
        timestamp, level, msg = match.groups()

        # Визначаємо колір для рівня логу
        if level == "DEBUG":
            level_color = "text-purple-400"
        elif level == "INFO":
            level_color = "text-green-400"
        elif level == "WARNING":
            level_color = "text-yellow-400"
        elif level in ["ERROR", "CRITICAL"]:
            level_color = "text-red-500 font-bold"
        else:
            level_color = "text-gray-400"

        # Формуємо HTML
        return f'<div class="mb-1"><span class="text-cyan-400">[{timestamp}]</span> <span class="{level_color}">[{level}]</span> <span class="text-gray-300">{msg}</span></div>'
    else:
        # Якщо рядок не відповідає формату (наприклад, traceback помилки)
        return f'<div class="mb-1 text-gray-500">{line}</div>'


def render_logs_page(log_file_path: str):
    menu()
    ui.label('Моніторинг системи (Logs)').classes('text-2xl font-bold mb-4')

    # Контейнер для логів: темний фон, моноширинний шрифт, скрол
    log_container = ui.html('', sanitize=False).classes(
        'w-full h-[75vh] overflow-y-auto bg-slate-900 p-4 rounded-lg shadow-inner font-mono text-sm leading-relaxed log-scroll-area'
    )

    # Стан для відстеження читання файлу
    state = {
        'last_pos': 0,
        'lines': []
    }

    def update_logs():
        if not os.path.exists(log_file_path):
            return

        file_size = os.path.getsize(log_file_path)

        # Якщо файл зменшився (наприклад, ротація логів), скидаємо позицію
        if file_size < state['last_pos']:
            state['last_pos'] = 0

        # Якщо розмір не змінився — нових даних немає, просто виходимо
        if file_size == state['last_pos']:
            return

        # Читаємо тільки НОВІ дані з останньої позиції
        with open(log_file_path, 'r', encoding='utf-8', errors='replace') as f:
            f.seek(state['last_pos'])
            new_lines = f.readlines()
            state['last_pos'] = f.tell() # Запам'ятовуємо нову позицію

        if new_lines:
            for line in new_lines:
                formatted = format_log_line(line)
                if formatted:
                    state['lines'].append(formatted)

            # Обрізаємо старі рядки, щоб браузер не гальмував
            if len(state['lines']) > LOG_MONITORING_MAX_LINES:
                state['lines'] = state['lines'][-LOG_MONITORING_MAX_LINES:]

            # Оновлюємо вміст на сторінці
            log_container.content = "".join(state['lines'])

            # JavaScript для автоматичного прокручування вниз
            ui.run_javascript('''
                const logBox = document.querySelector('.log-scroll-area');
                if (logBox) {
                    logBox.scrollTop = logBox.scrollHeight;
                }
            ''')

    # ІНІЦІАЛІЗАЦІЯ (Виконується 1 раз при відкритті сторінки)
    if os.path.exists(log_file_path):
        file_size = os.path.getsize(log_file_path)
        if file_size > 20000:
            state['last_pos'] = file_size - 20000
            with open(log_file_path, 'r', encoding='utf-8', errors='replace') as f:
                f.seek(state['last_pos'])
                f.readline()  # Відкидаємо обрізаний рядок
                state['last_pos'] = f.tell()

    # Запускаємо таймер, який перевіряє файл кожну 1 секунду
    log_timer = ui.timer(1.0, update_logs)

    # Викликаємо вручну для першого завантаження
    update_logs()

    # Кнопки керування
    with ui.row().classes('mt-4 gap-4'):
        ui.button('Очистити екран', on_click=lambda: (state['lines'].clear(), update_logs())).props('outline')