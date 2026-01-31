from datetime import datetime, timedelta
import config
import os
import shutil
from processing.process_doc import find_next_paragraph_docx, find_next_paragraph_doc, find_next_paragraph_pdf
from processing.process_xlx import update_excel_status
from pathlib import Path

def handle_attachment(attachment_id, original_filename):
    effective_date = get_effective_date()

    # 1. Формуємо назви для кожного рівня
    year_folder = effective_date.strftime(config.FOLDER_YEAR_FORMAT)
    month_folder = effective_date.strftime(config.FOLDER_MONTH_FORMAT)
    day_folder = effective_date.strftime(config.FOLDER_DAY_FORMAT)

    # 2. Будуємо повний шлях: .../signal-data/2026/01/2026.01.28/
    target_path = os.path.join(
        config.DATA_DIR,
        year_folder,
        month_folder,
        day_folder
    )

    # Створюємо всю ієрархію папок
    os.makedirs(target_path, exist_ok=True)

    source_file = os.path.join(config.SIGNAL_ATTACHMENTS_DIR, attachment_id)

    # Додаємо таймстамп для унікальності
    # unique_name = f"{int(effective_date.timestamp())}_{original_filename}"
    destination_file = os.path.join(target_path, original_filename)

    if os.path.exists(source_file):
        shutil.copy2(source_file, destination_file)
        if config.PROCESS_DOC:

            extension = Path(destination_file).suffix
            print("Пошук тексту..." + extension)
            if extension.lower() == '.doc':
                print(find_next_paragraph_doc(destination_file, 'стислі демографічні дані'))
            elif extension.lower() == '.docx':
                print(find_next_paragraph_docx(destination_file, 'стислі демографічні дані'))
            elif extension.lower() == '.pdf':
                print(find_next_paragraph_pdf(destination_file, '3. Прізвище, ім’я,'))
            print("...Пошук закінчено")
        if config.PROCESS_XLS:
            update_excel_status(config.DESERTER_XLSX, "КОЗАЧУК Вячеслав Вікторович")
        print(f"📁 Файл впорядковано: {destination_file}")

        return True
    else:
        print(f"❌ Файл {attachment_id} не знайдено в системній папці.")
        return False


def get_effective_date():
    """Визначає 'робочу' дату з урахуванням години переходу."""
    now = datetime.now()

    # Якщо поточна година більша або дорівнює встановленій (напр. 16)
    if now.hour >= config.DAY_ROLLOVER_HOUR:
        # Вважаємо, що вже наступний день
        return now + timedelta(days=1)

    return now
