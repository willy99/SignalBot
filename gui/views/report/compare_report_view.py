"""
compare_report_view.py
======================
Порівняння зовнішнього Excel-файлу з основною базою СЗЧ.

Step 1 — Маппінг полів:
  - Завантаження xlsx-файлу
  - Відображення колонок файлу (ліворуч) і GENERAL_FIELDS бази (праворуч)
  - Drag-and-drop маппінг + інтелектуальний авто-маппінг

Step 2 — Вибір полів для порівняння:
  - Чекбокси для полів файлу (ліворуч) і бази (праворуч)
  - Кнопка «Порівняти» → таблиця diff-результатів
"""

import io

import openpyxl
from nicegui import ui, events

from dics.deserter_xls_dic import (
    GENERAL_FIELDS,
    COLUMN_NAME,
    COLUMN_ID_NUMBER,
    COLUMN_BIRTHDAY,
    NA,
)
from gui.services.auth_manager import AuthManager

# ---------------------------------------------------------------------------
# Ключові поля для пошуку (виділяємо зірочкою в UI)
# ---------------------------------------------------------------------------
KEY_FIELDS = {COLUMN_NAME, COLUMN_ID_NUMBER, COLUMN_BIRTHDAY}

# ---------------------------------------------------------------------------
# Авто-маппінг: ключові слова для кожного GENERAL_FIELD
# Якщо назва колонки у завантаженому файлі містить будь-яке ключове слово —
# одразу проводимо лінію маппінгу.
# ---------------------------------------------------------------------------
_AUTO_MATCH: dict[str, list[str]] = {
    COLUMN_NAME:      ['піб', 'pib', 'прізвище', 'фіо', 'name', 'fullname', 'full_name', "ім'я", 'имя'],
    COLUMN_ID_NUMBER: ['рнокпп', 'rnokpp', 'інн', 'inn', 'ідн', 'taxid', 'код платника', 'ікн'],
    COLUMN_BIRTHDAY:  ['народження', 'birthday', 'birth', 'дн', 'д.н.', 'дата нар'],
    'Дата СЗЧ':       ['сзч', 'szch', 'дата сзч', 'дата залишення'],
    'Військове звання': ['звання', 'rank', 'чин'],
    'Підрозділ':      ['підрозділ', 'підрозд', 'unit', 'субюніт'],
    'Адреса проживання': ['адрес', 'address', 'місце проживання'],
    '№ телефону':     ['телефон', 'phone', 'mobile', 'моб'],
}


def _smart_map(upload_cols: list[str]) -> dict[str, str]:
    """
    Повертає {general_field: upload_col} — авто-маппінг за ключовими словами.
    Перший знайдений збіг для кожного поля бази.
    """
    mapping: dict[str, str] = {}
    for gen_field, keywords in _AUTO_MATCH.items():
        if gen_field not in GENERAL_FIELDS:
            continue
        for col in upload_cols:
            col_lower = col.lower().strip()
            if any(kw in col_lower for kw in keywords):
                mapping[gen_field] = col
                break
    return mapping


# ---------------------------------------------------------------------------
# Головна функція рендеру
# ---------------------------------------------------------------------------
def render_compare_report_page(report_ctrl, auth_manager: AuthManager):
    """Рендер сторінки порівняння файлів."""

    state: dict = {
        'file_bytes':   None,
        'upload_cols':  [],       # колонки з завантаженого файлу
        'mapping':      {},       # {gen_field: upload_col} — маппінг ключів
        'sel_upload':   [],       # вибрані колонки файлу (Step 2), порядок важливий
        'sel_general':  [],       # вибрані колонки бази (Step 2), порядок важливий
    }

    with ui.column().classes('w-full p-4 gap-2'):
        ui.label('Порівняння файлів').classes('text-h5 font-bold')
        ui.label(
            'Завантажте Excel-файл, налаштуйте маппінг полів і '
            'оберіть колонки для порівняння з основною базою СЗЧ.'
        ).classes('text-grey text-sm max-w-3xl')

    content = ui.column().classes('w-full px-4 pb-4 gap-4')

    # -----------------------------------------------------------------------
    # Step 1
    # -----------------------------------------------------------------------
    def render_step1():
        content.clear()
        with content:
            _render_stepper(1)

            # Upload card
            with ui.card().classes('w-full p-4'):
                ui.label('1. Завантажте файл для порівняння').classes(
                    'text-subtitle1 font-bold mb-2'
                )

                mapping_area = ui.column().classes('w-full')

                async def handle_upload(e: events.UploadEventArguments):
                    state['file_bytes'] = await e.file.read()
                    try:
                        wb = openpyxl.load_workbook(
                            io.BytesIO(state['file_bytes']),
                            read_only=True,
                            data_only=True,
                        )
                        ws = wb.active
                        headers = [
                            str(cell).strip()
                            for cell in next(
                                ws.iter_rows(min_row=1, max_row=1, values_only=True)
                            )
                            if cell is not None
                        ]
                        wb.close()

                        state['upload_cols'] = headers
                        state['mapping'] = _smart_map(headers)
                        auto_count = len(state['mapping'])

                        ui.notify(
                            f'Завантажено: {e.file.name} — {len(headers)} колонок, '
                            f'авто-маппінг: {auto_count} полів',
                            type='positive',
                        )
                        _render_mapping_ui(mapping_area, state, on_next=render_step2)

                    except Exception as ex:
                        ui.notify(f'Помилка читання файлу: {ex}', type='negative')

                ui.upload(
                    label='Оберіть .xlsx файл',
                    auto_upload=True,
                    max_files=1,
                    on_upload=handle_upload,
                ).props('accept=.xlsx').classes('w-full max-w-lg')

    # -----------------------------------------------------------------------
    # Step 2
    # -----------------------------------------------------------------------
    def render_step2():
        if not state['mapping']:
            ui.notify(
                'Налаштуйте маппінг хоча б одного ключового поля (ПІБ, РНОКПП або дата нар.)',
                type='warning',
            )
            return
        # Дефолтний вибір тільки при першому переході:
        # ліворуч — колонки файлу, що відповідають ПІБ і РНОКПП
        # праворуч — тільки ПІБ і РНОКПП з бази
        if not state['sel_upload']:
            default_gen = {COLUMN_NAME, COLUMN_ID_NUMBER}
            for gf, uc in state['mapping'].items():
                if gf in default_gen and uc not in state['sel_upload']:
                    state['sel_upload'].append(uc)
        if not state['sel_general']:
            for gf in (COLUMN_NAME, COLUMN_ID_NUMBER):
                if gf in state['mapping'] and gf not in state['sel_general']:
                    state['sel_general'].append(gf)

        content.clear()
        with content:
            _render_stepper(2)
            _render_field_selection(state, report_ctrl, auth_manager, on_back=render_step1)

    render_step1()


# ---------------------------------------------------------------------------
# Stepper
# ---------------------------------------------------------------------------
def _render_stepper(current: int):
    steps = ['Маппінг полів', 'Вибір та порівняння']
    with ui.row().classes('w-full items-center gap-0 mb-2'):
        for i, label in enumerate(steps, 1):
            done  = i < current
            active = i == current
            circle_cls = (
                'bg-primary text-white' if active
                else ('bg-green-500 text-white' if done else 'bg-grey-3 text-grey-7')
            )
            with ui.row().classes('items-center gap-2'):
                with ui.element('div').classes(
                    f'rounded-full w-7 h-7 flex items-center justify-center '
                    f'text-sm font-bold {circle_cls}'
                ):
                    ui.label(str(i))
                ui.label(label).classes(
                    'text-sm' + (' font-bold text-primary' if active else
                                 ' text-green-600' if done else ' text-grey')
                )
            if i < len(steps):
                ui.element('div').classes('flex-1 h-px bg-grey-3 mx-2').style('min-width:32px')


# ---------------------------------------------------------------------------
# Step 1: Drag-and-Drop mapping UI
# ---------------------------------------------------------------------------
def _render_mapping_ui(container: ui.column, state: dict, on_next):
    container.clear()
    upload_cols = state['upload_cols']
    mapping     = state['mapping']      # {gen_field: upload_col}

    if not upload_cols:
        return

    # Словник badge-контейнерів для кожного gen_field (щоб оновлювати на drop)
    badge_containers: dict[str, ui.element] = {}

    with container:
        with ui.card().classes('w-full p-4 mt-3'):
            ui.label('2. Налаштуйте маппінг полів').classes('text-subtitle1 font-bold')
            ui.label(
                'Перетягніть колонки зліва на відповідні поля бази справа. '
                'Поля зі ★ є ключовими для пошуку (ПІБ, РНОКПП, дата нар.).'
            ).classes('text-grey text-sm mb-3')

            with ui.row().classes('w-full gap-4 items-start'):

                # ---- Ліва панель ----
                with ui.column().classes('gap-2').style('min-width:220px; flex:1'):
                    ui.label('Колонки вашого файлу').classes(
                        'text-caption text-grey font-bold uppercase'
                    )
                    for col in upload_cols:
                        (
                            ui.chip(col, icon='drag_indicator')
                            .classes(
                                'upload-col-chip cursor-grab bg-blue-1 text-blue-9 '
                                'w-full justify-start'
                            )
                            .props(f'data-col="{col}"')
                        )

                # ---- Права панель ----
                with ui.column().classes('gap-1').style('flex:1'):
                    ui.label('Поля основної бази СЗЧ').classes(
                        'text-caption text-grey font-bold uppercase'
                    )
                    for gen_field in GENERAL_FIELDS:
                        is_key = gen_field in KEY_FIELDS
                        current_mapped = mapping.get(gen_field, '')

                        with ui.row().classes(
                            'general-field-row w-full items-center gap-2 px-2 py-1 rounded '
                            'border border-grey-3 hover:border-primary transition-all'
                        ).props(f'data-field="{gen_field}"'):

                            if is_key:
                                ui.icon('star', color='orange', size='xs').classes('flex-shrink-0')
                            else:
                                ui.element('div').classes('w-4 flex-shrink-0')

                            ui.label(gen_field).classes('text-sm flex-1')

                            badge_cont = ui.element('div').classes('flex-shrink-0')
                            with badge_cont:
                                if current_mapped:
                                    ui.badge(current_mapped, color='primary').classes('text-xs')
                                else:
                                    ui.label('—').classes('text-grey text-xs')
                            badge_containers[gen_field] = badge_cont

            # Підсумок маппінгу
            summary = ui.column().classes('w-full mt-3 p-3 bg-grey-1 rounded gap-1')
            _refresh_summary(summary, mapping)

            with ui.row().classes('w-full justify-end gap-3 mt-4'):
                ui.button(
                    'Скинути', icon='clear',
                    on_click=lambda: _clear_mapping(state, badge_containers, summary),
                ).props('flat')
                ui.button(
                    'Далі →', icon='arrow_forward',
                    on_click=on_next,
                ).props('elevated color=primary')

    # ---- Python-обробник drop-події ----
    def handle_mapped(e):
        args = e.args if hasattr(e, 'args') else {}
        gen_field  = args.get('gen_field', '')
        upload_col = args.get('upload_col', '')
        if not gen_field or not upload_col:
            return

        state['mapping'][gen_field] = upload_col

        badge_cont = badge_containers.get(gen_field)
        if badge_cont:
            badge_cont.clear()
            with badge_cont:
                ui.badge(upload_col, color='primary').classes('text-xs')

        _refresh_summary(summary, state['mapping'])

    ui.on('field_mapped', handle_mapped)

    # ---- Inject drag-and-drop JS ----
    ui.timer(0.25, _inject_dnd_js, once=True)


def _inject_dnd_js():
    ui.run_javascript('''
        (function setup_dnd() {
            const chips = document.querySelectorAll('.upload-col-chip');
            const rows  = document.querySelectorAll('.general-field-row');

            if (!chips.length || !rows.length) {
                // DOM ще не готовий — спробуємо ще раз
                setTimeout(setup_dnd, 150);
                return;
            }

            chips.forEach(el => {
                el.setAttribute('draggable', 'true');
                el.addEventListener('dragstart', function(ev) {
                    window._dndCol = this.getAttribute('data-col') || this.innerText.trim();
                    ev.dataTransfer.effectAllowed = 'copy';
                    this.style.opacity = '0.45';
                });
                el.addEventListener('dragend', function() {
                    this.style.opacity = '1';
                });
            });

            rows.forEach(el => {
                el.addEventListener('dragover', function(ev) {
                    ev.preventDefault();
                    ev.dataTransfer.dropEffect = 'copy';
                    this.style.background = '#e3f2fd';
                });
                el.addEventListener('dragleave', function() {
                    this.style.background = '';
                });
                el.addEventListener('drop', function(ev) {
                    ev.preventDefault();
                    this.style.background = '';
                    const genField  = this.getAttribute('data-field');
                    const uploadCol = window._dndCol;
                    if (genField && uploadCol) {
                        emitEvent('field_mapped', {gen_field: genField, upload_col: uploadCol});
                    }
                });
            });
        })();
    ''')


def _refresh_summary(container: ui.column, mapping: dict):
    container.clear()
    if not mapping:
        with container:
            ui.label('Маппінг ще не налаштовано').classes('text-grey text-sm')
        return
    with container:
        ui.label('Поточний маппінг:').classes('text-caption text-grey')
        for gen_field, upload_col in mapping.items():
            star = '★ ' if gen_field in KEY_FIELDS else ''
            with ui.row().classes('gap-2 items-center'):
                ui.label(upload_col).classes('text-sm text-blue-9 font-medium')
                ui.icon('arrow_forward', size='xs').classes('text-grey')
                ui.label(f'{star}{gen_field}').classes('text-sm')


def _clear_mapping(state, badge_containers, summary):
    state['mapping'].clear()
    for gen_field, badge_cont in badge_containers.items():
        badge_cont.clear()
        with badge_cont:
            ui.label('—').classes('text-grey text-xs')
    _refresh_summary(summary, {})
    ui.notify('Маппінг скинуто', type='info')


# ---------------------------------------------------------------------------
# Step 2: Вибір полів + Порівняння
# ---------------------------------------------------------------------------
def _render_field_selection(state: dict, report_ctrl, auth_manager, on_back):
    upload_cols = state['upload_cols']
    sel_upload  = state['sel_upload']   # list — порядок зберігається
    sel_general = state['sel_general']  # list — порядок зберігається

    left_checks:  dict[str, ui.checkbox] = {}
    right_checks: dict[str, ui.checkbox] = {}

    with ui.card().classes('w-full p-4'):
        ui.label('3. Оберіть поля для порівняння').classes('text-subtitle1 font-bold')
        ui.label(
            'Позначте колонки файлу (ліворуч) і поля бази (праворуч) '
            'для відображення у diff-звіті. Порядок вибору = порядок колонок у звіті.'
        ).classes('text-grey text-sm mb-3')

        with ui.row().classes('w-full gap-6 items-start'):

            # ---- Ліва панель ----
            with ui.column().classes('gap-1').style('flex:1'):
                with ui.row().classes('w-full items-center justify-between mb-1'):
                    ui.label('Колонки файлу').classes(
                        'text-caption font-bold uppercase text-grey'
                    )
                    ui.button(
                        'Всі', icon='select_all',
                        on_click=lambda: _select_all(upload_cols, sel_upload, left_checks),
                    ).props('flat dense size=xs')
                    ui.button(
                        'Жодного', icon='deselect',
                        on_click=lambda: _deselect_all(sel_upload, left_checks),
                    ).props('flat dense size=xs')

                for col in upload_cols:
                    cb = ui.checkbox(
                        col,
                        value=(col in sel_upload),
                        on_change=lambda e, c=col: _toggle(sel_upload, c, e.value, e.sender),
                    ).classes('text-sm')
                    left_checks[col] = cb

            # ---- Права панель ----
            with ui.column().classes('gap-1').style('flex:1'):
                with ui.row().classes('w-full items-center justify-between mb-1'):
                    ui.label('Поля бази СЗЧ').classes(
                        'text-caption font-bold uppercase text-grey'
                    )
                    ui.button(
                        'Всі', icon='select_all',
                        on_click=lambda: _select_all(
                            list(GENERAL_FIELDS), sel_general, right_checks
                        ),
                    ).props('flat dense size=xs')
                    ui.button(
                        'Жодного', icon='deselect',
                        on_click=lambda: _deselect_all(sel_general, right_checks),
                    ).props('flat dense size=xs')

                for gen_field in GENERAL_FIELDS:
                    is_key = gen_field in KEY_FIELDS
                    label  = ('★ ' if is_key else '') + gen_field
                    cb = ui.checkbox(
                        label,
                        value=(gen_field in sel_general),
                        on_change=lambda e, f=gen_field: _toggle(sel_general, f, e.value, e.sender),
                    ).classes('text-sm' + (' text-orange font-bold' if is_key else ''))
                    right_checks[gen_field] = cb

    # Результати
    compare_results = ui.column().classes('w-full mt-2')

    # Кнопки — "Назад" ліворуч, "Завантажити" і "Порівняти" праворуч на одному рівні
    with ui.row().classes('w-full justify-between items-center gap-3 mt-2'):
        ui.button('← Назад', icon='arrow_back', on_click=on_back).props('flat')
        with ui.row().classes('gap-2 items-center'):
            export_btn = ui.button(
                'Завантажити xlsx', icon='download',
                on_click=lambda: _export_compare(
                    state.get('_last_rows', []),
                    list(state['sel_upload']),
                    list(state['sel_general']),
                    state['mapping'],
                ),
            ).props('elevated color=green')
            export_btn.set_visibility(False)
            state['_export_btn'] = export_btn

            ui.button(
                'Порівняти', icon='compare_arrows',
                on_click=lambda: ui.timer(
                    0,
                    lambda: _do_compare(state, report_ctrl, auth_manager, compare_results),
                    once=True,
                ),
            ).props('elevated color=primary')


def _toggle(sel_list: list, field: str, value: bool, sender=None):
    """
    Додає або видаляє поле зі списку, зберігаючи порядок вибору.
    sender — посилання на чекбокс; захищає від stale-подій (напр. швидкий клік
    + одразу 'Жодного'): якщо поточне значення чекбоксу вже False, ігноруємо.
    """
    if value:
        # Перевіряємо реальний стан чекбоксу — міг вже бути скинутий batch-операцією
        if sender is not None and not sender.value:
            return
        if field not in sel_list:
            sel_list.append(field)
    else:
        if field in sel_list:
            sel_list.remove(field)


def _select_all(fields: list, sel_list: list, checks: dict):
    """Додає всі поля в порядку їх появи у списку."""
    sel_list.clear()
    for f in fields:
        sel_list.append(f)
    for cb in checks.values():
        cb.value = True


def _deselect_all(sel_list: list, checks: dict):
    """Скидає всі поля. Спочатку очищуємо список, потім знімаємо чекбокси."""
    sel_list.clear()
    for cb in checks.values():
        cb.value = False


# ---------------------------------------------------------------------------
# Порівняння (виклик контролера)
# ---------------------------------------------------------------------------
async def _do_compare(state: dict, report_ctrl, auth_manager, results_container):
    if not state['file_bytes']:
        ui.notify('Немає файлу для порівняння', type='warning')
        return
    if not state['mapping']:
        ui.notify('Налаштуйте маппінг ключових полів', type='warning')
        return

    results_container.clear()
    with results_container:
        ui.spinner(size='lg').classes('mt-4')
        ui.label('Завантажуємо дані та шукаємо збіги...').classes('text-grey mt-2')

    try:
        rows = await auth_manager.execute(
            report_ctrl.compare_file_with_db,
            auth_manager.get_current_context(),
            state['file_bytes'],
            state['mapping'],
            list(state['sel_upload']),
            list(state['sel_general']),
        )

        results_container.clear()
        if not rows:
            with results_container:
                ui.label('Не знайдено жодного рядка з даними.').classes('text-warning')
            return

        state['_last_rows'] = rows
        export_btn = state.get('_export_btn')
        if export_btn:
            export_btn.set_visibility(True)

        with results_container:
            _render_compare_table(rows, state)

    except Exception as e:
        results_container.clear()
        with results_container:
            ui.label(f'Помилка: {e}').classes('text-negative')
        ui.notify(f'Помилка порівняння: {e}', type='negative')


# ---------------------------------------------------------------------------
# Таблиця результатів
# ---------------------------------------------------------------------------
def _render_compare_table(rows: list[dict], state: dict):
    # Берємо списки — порядок такий, як обрав користувач
    sel_upload  = state['sel_upload']
    sel_general = state['sel_general']

    found_count   = sum(1 for r in rows if r.get('found'))
    missing_count = sum(1 for r in rows if not r.get('found'))
    diff_count    = sum(1 for r in rows if r.get('has_diff'))

    with ui.row().classes('w-full gap-4 mb-3'):
        _stat_card('Рядків у файлі', len(rows),      'blue-grey')
        _stat_card('Знайдено в базі', found_count,   'positive')
        _stat_card('Не знайдено',     missing_count, 'negative')
        if diff_count:
            _stat_card('З розбіжностями', diff_count, 'warning')

    ui.label(f'Результатів: {len(rows)}').classes('text-right text-grey w-full text-sm mb-1')

    # Колонки — у порядку вибору користувача. sort_order не є колонкою в таблиці —
    # лише поле у рядку для pre-sort. Quasar сортує "Статус" по рядку '❓' < '✅'.
    columns = [
        {'name': 'row',    'label': '№',      'field': 'row',    'align': 'center',
         'style': 'width:55px', 'sortable': True},
        {'name': 'status', 'label': 'Статус', 'field': 'status', 'align': 'center',
         'style': 'width:130px', 'sortable': True},
    ]
    for col in sel_upload:
        columns.append({
            'name': f'f_{col}', 'label': f'📄 {col}',
            'field': f'f_{col}', 'align': 'left', 'sortable': True,
        })
    for gf in sel_general:
        columns.append({
            'name': f'db_{gf}', 'label': f'🗄 {gf}',
            'field': f'db_{gf}', 'align': 'left', 'sortable': True,
        })

    table_rows = []
    for i, r in enumerate(rows, 1):
        found = r.get('found', False)
        tr = {
            'id':         i,
            'row':        i,
            'status':     '❓ Не знайдено' if not found else '✅ Знайдено',
            'found':      found,
            'sort_order': 0 if not found else 1,
        }
        for col in sel_upload:
            tr[f'f_{col}'] = r.get('file_data', {}).get(col, '')
        for gf in sel_general:
            tr[f'db_{gf}'] = r.get('db_data', {}).get(gf, '')
        table_rows.append(tr)

    # Дефолтне сортування: ненайдені першими
    table_rows.sort(key=lambda r: r['sort_order'])

    # Стан фільтрів: {field: lower_string}
    filters: dict[str, str] = {}
    result_label = ui.label(f'Результатів: {len(table_rows)}').classes(
        'text-right text-grey w-full text-sm mb-1'
    )

    # ---- Таблиця ----
    t = ui.table(columns=columns, rows=list(table_rows), row_key='id').classes(
        'w-full compare-table'
    )
    t.props(
        'bordered separator=cell flat dense virtual-scroll '
        'style="height:calc(100vh - 480px); min-height:300px;"'
    )

    # ---- Per-column header slots з фільтром.
    # Використовуємо окремий header-cell-{name} слот для кожної колонки —
    # це не порушує alignment на відміну від заміни всього `header` слота.
    # 'row' і 'status' — без фільтра.
    # emitEvent — NiceGUI global, надійніший ніж $parent.$emit з вкладених елементів.
    def _filter_slot(field: str) -> str:
        return (
            '<q-th :props="props" style="vertical-align:top; padding-bottom:4px;">'
            '<div style="margin-bottom:3px; white-space:normal;">{{ props.col.label }}</div>'
            '<q-input dense outlined clearable hide-bottom-space '
            'placeholder="фільтр…" '
            'style="min-width:60px; font-weight:normal;" '
            "@update:model-value=\"val => emitEvent('col_filter', {field: '" + field + "', value: val || ''})\" "
            "@clear=\"emitEvent('col_filter', {field: '" + field + "', value: ''})\" "
            '@click.stop />'
            '</q-th>'
        )

    for col_def in columns:
        if col_def['name'] not in ('row', 'status'):
            t.add_slot(f'header-cell-{col_def["name"]}', _filter_slot(col_def['field']))

    # ---- Слот body-cell-status: кольоровий бейдж ----
    t.add_slot('body-cell-status', '''
        <q-td :props="props">
            <q-badge
                :color="props.row.found ? 'positive' : 'negative'"
                :label="props.value"
                class="text-xs"
            />
        </q-td>
    ''')

    # ---- Python-обробник фільтрації ----
    def on_col_filter(e):
        args  = e.args if hasattr(e, 'args') else {}
        field = args.get('field', '')
        value = (args.get('value') or '').strip().lower()

        if value:
            filters[field] = value
        else:
            filters.pop(field, None)

        filtered = [
            r for r in table_rows
            if all(
                fv in str(r.get(ff, '')).lower()
                for ff, fv in filters.items()
            )
        ]
        t.rows = filtered
        t.update()
        suffix = f' (фільтр активний: {len(filters)} пол.)' if filters else ''
        result_label.set_text(f'Результатів: {len(filtered)} / {len(table_rows)}{suffix}')

    t.on('col_filter', on_col_filter)

    # ---- CSS: sticky header + висота рядка хедера з фільтром ----
    ui.add_head_html('''
        <style>
        .compare-table thead tr th {
            position: sticky !important;
            top: 0;
            z-index: 2;
            background: white;
        }
        </style>
    ''')


def _stat_card(label: str, value: int, color: str):
    with ui.card().classes(f'p-3 text-center bg-{color}-50 flex-shrink-0'):
        ui.label(str(value)).classes('text-h5 font-bold')
        ui.label(label).classes('text-xs text-grey')


# ---------------------------------------------------------------------------
# Експорт результатів у xlsx
# ---------------------------------------------------------------------------
def _export_compare(rows: list[dict], sel_upload: list, sel_general: list, mapping: dict):
    import io as _io
    from openpyxl import Workbook
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

    wb = Workbook()
    ws = wb.active
    ws.title = 'Порівняння'

    bold     = Font(bold=True)
    c_align  = Alignment(horizontal='center', vertical='center', wrap_text=True)
    l_align  = Alignment(horizontal='left',   vertical='center', wrap_text=True)
    hdr_fill = PatternFill('solid', fgColor='E0E0E0')
    fill_ok  = PatternFill('solid', fgColor='C6EFCE')
    fill_err = PatternFill('solid', fgColor='FFC7CE')
    border   = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'),  bottom=Side(style='thin'),
    )

    headers = (
        ['№', 'Статус']
        + [f'Файл: {c}' for c in sel_upload]
        + [f'База: {g}' for g in sel_general]
    )
    for ci, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=ci, value=h)
        cell.font      = bold
        cell.fill      = hdr_fill
        cell.alignment = c_align
        cell.border    = border

    for ri, r in enumerate(rows, 2):
        vals = (
            [ri - 1, 'Знайдено' if r.get('found') else 'Не знайдено']
            + [r.get('file_data', {}).get(col, '') for col in sel_upload]
            + [r.get('db_data',   {}).get(gf,  '') for gf  in sel_general]
        )
        row_fill = fill_ok if r.get('found') else fill_err
        for ci, val in enumerate(vals, 1):
            cell = ws.cell(row=ri, column=ci, value=str(val) if val else '')
            cell.border    = border
            cell.alignment = c_align if ci <= 2 else l_align
            cell.fill      = row_fill

    ws.freeze_panes = 'A2'
    ws.column_dimensions['A'].width = 6
    ws.column_dimensions['B'].width = 14
    for i in range(3, len(headers) + 1):
        from openpyxl.utils import get_column_letter
        ws.column_dimensions[get_column_letter(i)].width = 20

    buf = _io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    ui.download(buf.getvalue(), filename='compare_result.xlsx')
    ui.notify('Файл завантажується...', type='positive')
