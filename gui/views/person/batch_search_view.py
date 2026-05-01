import regex as re
from nicegui import ui
from datetime import datetime
import config
from config_examples.config_mac import EXCEL_DATE_FORMAT
from dics.deserter_xls_dic import PATTERN_NAME_WITH_CASE, PATTERN_DATE, MIL_UNITS
from gui.services.auth_manager import AuthManager
from utils.regular_expressions import extract_desertion_date_from_erdr_cond
from utils.utils import get_file_year_month, clean_text

# --- РЕГУЛЯРКИ ---
PATTERN_UNIT = r'[АAА-Яa-zA-Z]\s*\d{4}'


def is_date_within_range(szch_date_str: str, path_year: int, path_month: int) -> bool:
    """Перевіряє, чи дата файлу відхиляється від дати СЗЧ не більше ніж на 1 місяць."""
    if not path_year or not path_month:
        return False

    if szch_date_str == "Не визначено":
        return True  # Якщо дата СЗЧ невідома, беремо всі файли по цій людині

    try:
        szch_date = datetime.strptime(szch_date_str, EXCEL_DATE_FORMAT)
        diff_in_months = abs((szch_date.year - path_year) * 12 + (szch_date.month - path_month))
        return diff_in_months <= 1
    except Exception:
        return False


def get_full_source_path(row_data, base_dir):
    """Формує повний шлях до файлу."""
    filename = row_data['name']
    folder_path = row_data['path']
    base_dir = base_dir.rstrip('\\/')
    match = re.match(r'^\\\\[^\\]+\\[^\\]+', base_dir)
    share_root = match.group(0) if match else base_dir

    if folder_path == "(Коренева папка)":
        return f"{base_dir}\\{filename}"
    else:
        return f"{share_root}\\{folder_path}\\{filename}"


def render_bulk_search_page(person_ctrl, file_cache_manager, auth_manager: AuthManager):
    ui.label('Масовий аналіз та пошук осіб').classes('w-full text-center text-3xl font-bold mb-6')

    with ui.card().classes('w-full max-w-5xl mx-auto p-6 shadow-md'):
        ui.label('Вставте текст (рапорти, списки з біографіями):').classes('text-lg font-medium text-gray-700 mb-2')
        text_input = ui.textarea(
            placeholder='ГАЛУШКО Сергій Юрійович ... ЗСУ-вч-А4444 ... з 25.11.2025 ...') \
            .classes('w-full mb-4').props('outlined rows=6')

        search_btn = ui.button('Проаналізувати та Знайти', icon='manage_search').props('color="primary" size="lg"').classes('w-full mb-2')

    results_container = ui.column().classes('w-full mt-8 gap-2 px-2 sm:px-8')

    def parse_text_blocks(raw_text: str):
        parsed_data = []
        blocks = [b.strip() for b in re.split(r'\n\s*\n|\n', raw_text) if b.strip()]

        for block in blocks:
            block = clean_text(block)
            units_found = re.findall(PATTERN_UNIT, block, flags=re.IGNORECASE)
            normalized_units = [u.replace(' ', '').upper().replace('A', 'А') for u in units_found]

            if normalized_units and MIL_UNITS[0] not in normalized_units:
                continue

            name_match = re.search(PATTERN_NAME_WITH_CASE, block)
            if not name_match:
                continue

            name = name_match.group(0).strip(' ,;')
            szch_date = extract_desertion_date_from_erdr_cond(block)

            parsed_data.append({
                'name': name,
                'mil_unit': MIL_UNITS[0],
                'szch_date': szch_date,
                'raw_block': block
            })

        return parsed_data

    # --- ДІЇ ДЛЯ КОЖНОГО ОКРЕМОГО ФАЙЛУ ---
    async def copy_single_file_to_outbox(file_data):
        source_path = get_full_source_path(file_data, config.DOCUMENT_STORAGE_PATH)
        filename = file_data['name']
        dest_path = f"{config.OUTBOX_DIR_PATH}{file_cache_manager.get_file_separator()}{auth_manager.get_current_context().user_login}{file_cache_manager.get_file_separator()}{filename}"

        try:
            await auth_manager.execute(file_cache_manager.copy_to_local, auth_manager.get_current_context(), source_path, dest_path)
            ui.notify(f"✅ Файл {filename} скопійовано в Outbox", type='positive')
        except Exception as ex:
            ui.notify(f"❌ Помилка копіювання {filename}: {ex}", type='negative')

    async def download_single_file(file_data):
        source_path = get_full_source_path(file_data, config.DOCUMENT_STORAGE_PATH)
        filename = file_data['name']
        with ui.notification(message=f'Підготовка до завантаження {filename}...', spinner=True, timeout=0) as n:
            try:
                # Читаємо файл у буфер через клієнт
                file_buffer = await auth_manager.execute(file_cache_manager.client.get_file_buffer, auth_manager.get_current_context(), source_path)
                ui.download(file_buffer.read(), filename)
                n.message = 'Завантаження розпочато!'
                n.type = 'positive'
                n.spinner = False
                n.timeout = 2
            except Exception as ex:
                n.message = f'Помилка завантаження: {ex}'
                n.type = 'negative'
                n.spinner = False
                n.timeout = 5

    async def perform_bulk_search():
        raw_text = text_input.value or ""

        if not raw_text.strip():
            ui.notify("Введіть текст для пошуку!", type='warning')
            return

        search_btn.disable()
        search_btn.props('icon="hourglass_empty" loading')

        try:
            parsed_items = parse_text_blocks(raw_text)

            unique_items = []
            seen_names = set()
            for item in parsed_items:
                if item['name'] not in seen_names:
                    unique_items.append(item)
                    seen_names.add(item['name'])

            if not unique_items:
                ui.notify("Не знайдено жодної особи з А0224!", type='negative')
                results_container.clear()
                return

            names_to_search = [item['name'] for item in unique_items]

            db_results = await auth_manager.execute(person_ctrl.batch_search_names, auth_manager.get_current_context(), names_to_search)
            db_map = {}
            for res in db_results:
                name = res['name']
                if name not in db_map or res['found']:
                    db_map[name] = res

            table_rows = []
            found_count = 0

            for item in unique_items:
                db_info = db_map.get(item['name'], {'found': False})
                if db_info['found']:
                    found_count += 1

                # ПОШУК ФАЙЛІВ
                full_name = item['name']
                all_person_files = file_cache_manager.search(full_name)
                if not all_person_files or len(all_person_files) == 0:
                    surname = item['name'].split()[0]
                    all_person_files = file_cache_manager.search(surname)


                matched_files = []
                for f in all_person_files:
                    # Передаємо і шлях, і ім'я файлу для розумного пошуку дати
                    f_year, f_month = get_file_year_month(f['path'], f['name'])
                    if is_date_within_range(item['szch_date'], f_year, f_month):
                        matched_files.append(f)

                display_unit = db_info.get('mil_unit') if db_info.get('found') else item['mil_unit']

                table_rows.append({
                    'mil_unit': display_unit,
                    'name': item['name'],
                    'szch_date': item['szch_date'],
                    'found': db_info['found'],
                    'rnokpp': db_info.get('rnokpp', '—'),
                    'docs_count': len(matched_files),
                    'matched_files': matched_files
                })

            results_container.clear()
            with results_container:

                with ui.row().classes('w-full justify-between items-end mb-2'):
                    ui.label(f'Всього розпізнано: {len(unique_items)} (тільки А0224)').classes('font-bold text-gray-800 text-xl')
                    ui.label(f'✅ В базі: {found_count} | ❌ Відсутні: {len(unique_items) - found_count}').classes('text-sm font-bold text-gray-600')

                # Зменшили кількість колонок, прибравши "Дії" (вони тепер біля кожного файлу)
                columns = [
                    {'name': 'mil_unit', 'label': 'В/Ч', 'field': 'mil_unit', 'align': 'left', 'sortable': True},
                    {'name': 'name', 'label': 'ПІБ', 'field': 'name', 'align': 'left', 'sortable': True},
                    {'name': 'szch_date', 'label': 'Дата СЗЧ', 'field': 'szch_date', 'align': 'center'},
                    {'name': 'status', 'label': 'Наявність в БД', 'field': 'found', 'align': 'center', 'sortable': True},
                    {'name': 'docs', 'label': 'Знайдені Довідки та Дії', 'field': 'docs_count', 'align': 'left'},
                ]

                table = ui.table(columns=columns, rows=table_rows, row_key='name').classes('w-full bg-white shadow-sm border border-gray-200')

                table.add_slot('body-cell-name', '''
                    <q-td :props="props">
                        <div class="font-bold text-base text-gray-900">{{ props.row.name }}</div>
                        <div v-if="props.row.found" class="text-xs text-blue-600 font-medium">РНОКПП: {{ props.row.rnokpp }}</div>
                    </q-td>
                ''')

                table.add_slot('body-cell-status', '''
                    <q-td :props="props">
                        <q-chip v-if="props.row.found" color="positive" text-color="white" icon="check_circle" size="sm" class="font-bold">
                            Є в базі
                        </q-chip>
                        <q-chip v-else color="negative" text-color="white" icon="cancel" size="sm" class="font-bold">
                            Відсутній
                        </q-chip>
                    </q-td>
                ''')

                table.add_slot('body-cell-docs', '''
                                    <q-td :props="props">
                                        <div v-if="props.row.docs_count > 0" class="flex flex-col gap-1 w-full min-w-[350px]">
                                            <div v-for="f in props.row.matched_files" :key="f.name" class="flex items-center w-full bg-gray-50 p-1 px-2 rounded border border-gray-200 shadow-sm hover:bg-blue-50 transition-colors">

                                                <div class="text-xs text-gray-800 font-medium truncate flex-grow mr-2" :title="f.name">
                                                    <q-icon name="description" color="primary" size="xs" class="mr-1"/>{{ f.name }}
                                                </div>

                                                <div class="flex flex-nowrap gap-1 shrink-0 ml-auto">
                                                    <q-btn size="xs" color="blue" flat icon="download" @click="$parent.$emit('download_single', f)">
                                                        <q-tooltip>Завантажити</q-tooltip>
                                                    </q-btn>
                                                    <q-btn size="xs" color="orange" flat icon="forward_to_inbox" @click="$parent.$emit('outbox_single', f)">
                                                        <q-tooltip>Копіювати в Outbox</q-tooltip>
                                                    </q-btn>
                                                </div>

                                            </div>
                                        </div>
                                        <span v-else class="text-xs text-gray-400 italic">Довідок не знайдено</span>
                                    </q-td>
                                ''')

                table.on('download_single', lambda e: download_single_file(e.args))
                table.on('outbox_single', lambda e: copy_single_file_to_outbox(e.args))

            ui.notify('Аналіз та пошук файлів завершено!', type='positive')

        except Exception as e:
            ui.notify(f"Помилка масового аналізу: {e}", type="negative")

        finally:
            search_btn.enable()
            search_btn.props(remove='loading')

    search_btn.on('click', perform_bulk_search)