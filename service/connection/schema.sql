-- Таблиця станів користувачів (для бота)
CREATE TABLE IF NOT EXISTS user_states (
    phone_number TEXT PRIMARY KEY,
    current_state TEXT DEFAULT 'START',
    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблиця користувачів
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    full_name TEXT,
    is_active INTEGER DEFAULT 1
);

-- Таблиця прав доступу для ролей
CREATE TABLE IF NOT EXISTS role_permissions (
    role TEXT NOT NULL,
    module_name TEXT NOT NULL,
    can_read INTEGER DEFAULT 0,
    can_write INTEGER DEFAULT 0,
    can_delete INTEGER DEFAULT 0,
    PRIMARY KEY (role, module_name)
);

-- Таблиця супровідних документів
CREATE TABLE IF NOT EXISTS support_docs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_by INTEGER NOT NULL,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'DRAFT',
    city TEXT,
    support_number TEXT,
    payload TEXT,

    -- Зовнішній ключ: якщо видалити юзера, його документи видаляться теж (або можна прибрати ON DELETE CASCADE)
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
);

-- Таблиця задач (Канбан)
CREATE TABLE IF NOT EXISTS task (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_by INTEGER NOT NULL,
    assignee INTEGER,
    task_status VARCHAR(50) DEFAULT 'NEW',
    task_type VARCHAR(50) DEFAULT '',
    task_subject VARCHAR(255) NOT NULL,
    task_details TEXT,
    task_deadline DATETIME,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_date DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Зовнішні ключі
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (assignee) REFERENCES users(id) ON DELETE SET NULL
);


CREATE TABLE IF NOT EXISTS dbr_docs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_by INTEGER NOT NULL,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'DRAFT',        -- 'DRAFT' або 'COMPLETED'
    out_number TEXT,                    -- Вихідний номер
    out_date TEXT,                      -- Дата відправки
    payload TEXT,                       -- JSON масив з обраними особами

    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
);

