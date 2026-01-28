from database import get_user_state, set_user_state

def get_response_and_move(user_id, text):
    current_state = get_user_state(user_id)
    text = text.lower()

    # Логіка переходів
    if text == "меню":
        set_user_state(user_id, "MAIN_MENU")
        return "Ви у Головному меню:\n1. Техпідтримка\n2. Баланс\n3. Вихід"

    if current_state == "MAIN_MENU":
        if text == "1":
            set_user_state(user_id, "SUPPORT")
            return "Опишіть вашу проблему або натисніть 0 для повернення."
        elif text == "2":
            return "Ваш баланс: 100 грн. Натисніть 0 для повернення."
        elif text == "3":
            set_user_state(user_id, "START")
            return "До зустрічі! Напишіть 'меню', щоб почати."

    if current_state == "SUPPORT":
        if text == "0":
            set_user_state(user_id, "MAIN_MENU")
            return "Повертаємось... Ви у Головному меню:\n1. Техпідтримка\n2. Баланс"
        else:
            return f"Ваш запит '{text}' прийнято. (0 - назад)"

    return "Напишіть 'меню' для початку роботи."