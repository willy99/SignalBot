css_button = 'border-radius: 4px !important; margin-left: 5px !important;'
css_tab_button = """
    /* Контейнер для табів */
    .tab-container button {
        border-radius: 0px !important; /* Робимо кути гострими */
        margin: 0 -1px 0 0 !important; /* Накладаємо рамки одна на одну */
        border: 1px solid #ccc !important;
    }
    /* Закруглюємо тільки крайні кути */
    .tab-container button:first-child { border-top-left-radius: 8px !important; }
    .tab-container button:last-child { border-top-right-radius: 8px !important; }

    /* Колір неактивної кнопки (сірий) */
    .btn-outline-primary {
        background-color: #f8f9fa !important;
        color: #6c757d !important;
        border-color: #dee2e6 !important;
    }        
"""
