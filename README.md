# cheat-sheet

main.py — точка входа, код запуска бота и инициализации всех остальных модулей

config.py — файл со всеми конфигурационными параметрами, такими как токен бота и данные подключения к БД.

db.py — функции подключения и работы с базой данных. Данный файл является абстракцией базы данных от основного кода

text.py — все тексты, используемые ботом. В этом файле лежат все приветствия, сообщения об ошибках и другие текстовые данные для бота.

kb.py — все клавиатуры, используемые ботом. В этом файле находятся абсолютно все клавиатуры, как статические, так и динамически генерируемые через функции

middlewares.py — название файла говорит само за себя. В этом файле лежат все используемые мидлвари (их всего две: UserMiddleware и DatabaseMiddleware)

states.py — хранит вспомогательные классы для FSM (машины состояний), а также фабрики Callback Data для кнопок Inline клавиатур

utils.py — различные функции. В этом файле лежат функции для рассылки, генерации текста и изображений через API и другие

handlers.py — основной файл, состоит из обработчиков с декораторами (фильтрами)
base_commands.py — сосотоит из общих (базовых) функций-обработчиков для всех пользователей
admin_commands.py — состоит из фунций-обработчиков для админов

admin.py — обработчики событий, клавиатуры, классы и весь остальной код админки бота. Наша админка будет иметь базовый функционал, поэтому реализуем всё в одном файле

cheatssheets.db - база данных, содержит: balance_requests, cheatsheets, purchases, sqlite_sequence, subjects, users
