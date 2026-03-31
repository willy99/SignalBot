-- ==========================================
-- ІНДЕКСИ ДЛЯ ТАБЛИЦІ ЗАДАЧ
-- ==========================================
-- Прискорює вибірку задач для конкретного юзера (Канбан дошка)
CREATE INDEX IF NOT EXISTS idx_task_assignee_status ON task(assignee, task_status);

-- Прискорює фоновий таймер (будильник дедлайнів)
CREATE INDEX IF NOT EXISTS idx_task_assignee_deadline ON task(assignee, task_deadline);

-- Прискорює пошук всіх задач, створених певним офіцером
CREATE INDEX IF NOT EXISTS idx_task_created_by ON task(created_by);

-- ==========================================
-- ІНДЕКСИ ДЛЯ ТАБЛИЦІ ДОКУМЕНТІВ
-- ==========================================
CREATE INDEX IF NOT EXISTS idx_support_docs_created_by ON support_docs(created_by);
CREATE INDEX IF NOT EXISTS idx_support_docs_status ON support_docs(status);

-- ==========================================
-- ІНДЕКСИ ДЛЯ КОРИСТУВАЧІВ
-- (username вже має UNIQUE індекс під капотом)
-- ==========================================
-- Прискорює пошук активних юзерів для випадаючого списку виконавців
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);



CREATE INDEX IF NOT EXISTS idx_dbr_docs_created_by ON dbr_docs(created_by);
CREATE INDEX IF NOT EXISTS idx_dbr_docs_status ON dbr_docs(status);

CREATE INDEX IF NOT EXISTS idx_notif_docs_created_by ON notif_docs(created_by);
CREATE INDEX IF NOT EXISTS idx_notif_docs_status ON notif_docs(status);


CREATE UNIQUE INDEX IF NOT EXISTS udx_support_out_number
ON support_docs(out_number)
WHERE out_number IS NOT NULL AND out_number != '' AND deleted = 0;

CREATE UNIQUE INDEX IF NOT EXISTS udx_dbr_out_number
ON dbr_docs(out_number)
WHERE out_number IS NOT NULL AND out_number != '' AND deleted = 0;

CREATE UNIQUE INDEX IF NOT EXISTS udx_notif_out_number
ON notif_docs(out_number)
WHERE out_number IS NOT NULL AND out_number != '' AND deleted = 0;
