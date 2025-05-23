class Texts:
    # Основные команды
    START = "👋 Привет! Это бот со шпаргалками для студентов.\n\nВы можете искать шпаргалки по предметам, семестрам и типам, или загружать свои."
    HELP = "ℹ️ Помощь:\n\n- Используйте кнопки меню для навигации\n- Для поиска шпаргалок выберите предмет, семестр и тип\n- Чтобы загрузить шпаргалку, нажмите 'Добавить шпаргалку'"
    
    # Меню
    SEARCH_CHEATSHEET = "🔍 Поиск шпаргалок"
    ADD_CHEATSHEET = "📤 Добавить шпаргалку"
    MY_CHEATSHEETS = "📚 Мои шпаргалки"
    BALANCE = "💰 Баланс"
    DEPOSIT = "💳 Пополнить баланс"
    
    FEEDBACK = "📝 Обратная связь"
    FEEDBACK_PROMPT = "Напишите ваше предложение, идею или отзыв (максимум 1000 символов):"
    FEEDBACK_TOO_LONG = "Сообщение слишком длинное (максимум 1000 символов)"
    FEEDBACK_SENT = "✅ Ваш отзыв отправлен. Спасибо!"
    FEEDBACK_NOTIFICATION = (
        "🆕 Новый отзыв #{id}\n"
        "👤 Пользователь: @{username} (ID: {user_id})\n"
        "📝 Сообщение:\n\n{message}\n\n"
        "🕒 Дата: {date}"
    )
    FEEDBACK_APPROVED = "✅ Ваш отзыв был рассмотрен и принят. Спасибо!"
    FEEDBACK_REJECTED = "❌ Ваш отзыв был отклонен."
    
    # Кнопки
    BACK_BUTTON = "⬅️ Назад"
    CANCEL_BUTTON = "❌ Отмена"
    CANCEL_SEARCH = "❌ Отменить поиск"
    APPROVE_BUTTON = "✅ Одобрить"
    REJECT_BUTTON = "❌ Отклонить"
    BUY_BUTTON = "🛒 Купить за {price} руб."
    FREE_ACCESS = "📄 Открыть"
    
    # Добавление шпаргалки
    SELECT_SUBJECT = "Выберите предмет:"
    SELECT_SEMESTER = "Выберите семестр:"
    SELECT_TYPE = "Выберите тип шпаргалки:"
    SEND_FILE = "Отправьте файл шпаргалки (PDF, изображение) или текст:"
    SET_PRICE = "Установите цену для шпаргалки (в рублях) или 0 для бесплатного доступа:"
    CHEATSHEET_SENT_FOR_REVIEW = "✅ Ваша шпаргалка отправлена на модерацию. После проверки она будет доступна другим пользователям."
    ENTER_NAME = "Введите название шпаргалки:"
    NAME_TOO_LONG = "Название слишком длинное (максимум 100 символов)"
    
    # Поиск и просмотр шпаргалок
    NO_CHEATSHEETS = "😕 По вашему запросу ничего не найдено."
    CHEATSHEET_INFO = (
        "📚 {name}\n"
        "📖 Предмет: {subject}\n"
        "🔢 Семестр: {semester}\n"
        "📝 Тип: {type}\n"
        "👤 Автор: {author}\n"
        "💰 Цена: {price} руб.\n"
        "🕒 Опубликовано: {approved_at}"
    )
    FILTER_BY_SUBJECT = "Выберите предмет для фильтрации:"
    ALL_CHEATSHEETS_HEADER = "Все шпаргалки:"
    CHEATSHEETS_STATS_HEADER = "Статистика шпаргалок:"
    TOTAL_CHEATSHEETS = "Всего шпаргалок"
    
    # Статусы шпаргалок
    CHEATSHEET_STATUS_APPROVED = "✅ Одобрена"
    CHEATSHEET_STATUS_PENDING = "⏳ На модерации"
    CHEATSHEET_STATUS_REJECTED = "❌ Отклонена"
    
    # Покупка
    NOT_ENOUGH_MONEY = "❌ Недостаточно средств на балансе."
    PURCHASE_SUCCESS = "✅ Покупка успешна! Вот ваша шпаргалка:"
    SOLD_NOTIFICATION = "💰 Ваша шпаргалка '{name}' была куплена пользователем {user}. Вы получили {amount} руб."
    
    # Баланс и платежи
    BALANCE_INFO = "💰 Ваш баланс: {balance} руб."
    BALANCE_UPDATED = "✅ Баланс пользователя {user_id} пополнен на {amount} руб.\nНовый баланс: {new_balance} руб."
    BALANCE_NOTIFICATION = "💰 Ваш баланс пополнен на {amount} руб.\nТекущий баланс: {balance} руб."
    ENTER_AMOUNT = "Отправьте сумму пополнения цифрами (например: 500):"
    PAYMENT_PROOF = (
        "Теперь отправьте скриншот подтверждения платежа (фото или документ PDF/JPG/PNG),\n"
        "или текстовое описание платежа (номер транзакции и т.д.):"
    )
    REQUEST_SENT = "✅ Ваш запрос отправлен на рассмотрение"
    REQUEST_ERROR = "Ошибка при создании запроса"
    
    WITHDRAW = "💸 Вывести средства"
    WITHDRAW_REQUEST = (
        "🆕 Запрос на вывод средств #{id}\n"
        "👤 Пользователь: @{username} (ID: {user_id})\n"
        "💰 Сумма: {amount} руб.\n"
        "📱 Реквизиты: {details}\n"
        "🕒 Дата: {date}"
    )
    WITHDRAW_REQUEST_SENT = (
        "✅ Ваш запрос на вывод {amount} руб. отправлен на рассмотрение.\n"
        "Администратор: {admin_username}"
    )
    ENTER_WITHDRAW_AMOUNT = "Введите сумму для вывода (в рублях):"
    ENTER_WITHDRAW_DETAILS = "Введите реквизиты для перевода (номер карты/телефона и банк):"
    INVALID_WITHDRAW_AMOUNT = "❌ Неверная сумма. Укажите положительное число, не превышающее ваш баланс."
    
    # Административные
    NEW_CHEATSHEET_FOR_REVIEW = (
        "📥 Новая шпаргалка на модерацию:\n\n"
        "🏷 Название: {name}\n"
        "📚 Предмет: {subject}\n"
        "🔢 Семестр: {semester}\n"
        "📝 Тип: {type}\n"
        "💰 Цена: {price} ₽\n"
        "👤 Автор: {author}"
    )
    CHEATSHEET_APPROVED = "Шпаргалка одобрена и добавлена в каталог."
    CHEATSHEET_REJECTED = "Шпаргалка отклонена."
    SELECT_USER_ID = "Введите ID пользователя для пополнения баланса:"
    
    BROADCAST_START = "✉️ Отправьте сообщение для рассылки (текст, фото или файл):"
    BROADCAST_CANCEL = "❌ Рассылка отменена"
    BROADCAST_CONFIRM = (
        "✅ Сообщение готово к отправке:\n\n"
        "{content}\n\n"
        "Количество получателей: {users_count}\n"
        "Отправить?"
    )
    BROADCAST_SUCCESS = "✅ Рассылка успешно завершена. Получено сообщений: {success}/{total}"
    BROADCAST_NO_USERS = "❌ Нет пользователей для рассылки"
    
    # Запросы на пополнение
    BALANCE_REQUEST = (
        "🆕 Запрос на пополнение баланса #{id}\n"
        "👤 Пользователь: @{username} (ID: {user_id})\n"
        "💰 Сумма: {amount} руб.\n"
        "🕒 Дата: {date}"
    )
    BALANCE_APPROVED = "✅ Ваш запрос на пополнение {amount} руб. одобрен. Текущий баланс: {balance} руб."
    BALANCE_REJECTED = "❌ Ваш запрос на пополнение {amount} руб. отклонен."
    
    # Ошибки и валидация
    ERROR = "⚠️ Произошла ошибка. Пожалуйста, попробуйте позже."
    INVALID_FILE = "❌ Неверный формат файла. Поддерживаются только PDF, JPG, PNG и текстовые сообщения."
    INVALID_PRICE = "❌ Неверная цена. Введите число больше или равное 0."
    INVALID_USER_ID_FORMAT = "Неверный формат ID. Введите число:"
    INVALID_AMOUNT_FORMAT = "Неверный формат суммы. Введите число:"
    AMOUNT_MUST_BE_POSITIVE = "Сумма должна быть больше 0"
    INVALID_PROOF_FORMAT = "Неверный формат подтверждения"
    INVALID_AMOUNT = "Ошибка: неверная сумма"
    ACTION_CANCELLED = "Действие отменено"
    UNEXPECTED_ERROR = "Произошла непредвиденная ошибка. Пожалуйста, попробуйте снова."


def format_cheatsheet_for_admin(cheatsheet: dict) -> str:
    """Форматирует информацию о шпаргалке для админа"""
    return (
        f"📝 Редактирование шпаргалки:\n\n"
        f"🏷 Название: {cheatsheet['name']}\n"
        f"📚 Предмет: {cheatsheet['subject']}\n"
        f"🔢 Семестр: {cheatsheet['semester']}\n"
        f"📝 Тип: {cheatsheet['type']}\n"
        f"💰 Цена: {cheatsheet['price']} руб.\n"  # Добавляем отображение цены
        f"👤 Автор: {cheatsheet['author']}"
    )


texts = Texts()
