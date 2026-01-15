from aiogram import Bot, Dispatcher, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, FSInputFile, InputMediaPhoto
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import sqlite3
import asyncio
import os

OWNER_ID = 7508122402
BOOSTERS_CHAT_ID = -1003679877605
ORDERS_CHANNEL_ID = -1003438779782  # Канал для заказов
ADMIN_IDS = [OWNER_ID, 1806616337]
BOOSTER_APPLICATIONS_CHAT_ID = ADMIN_IDS
BOOSTERS_CHAT_LINK = "https://t.me/+roK4alwk6JZiZDdk"


def init_db():
    conn = sqlite3.connect("databases.db")
    cursor = conn.cursor()
    cursor.execute("""PRAGMA foreign_keys = ON""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS users (tg_id INTEGER PRIMARY KEY, username TEXT, so2_id INTEGER)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, buyer_id INTEGER, game_mode TEXT, range_now TEXT, range_to_boost TEXT, boost_format TEXT, price TEXT, boost_status TEXT DEFAULT "waiting", booster_id INTEGER)""")  # Добавлено game_mode
    cursor.execute("""CREATE TABLE IF NOT EXISTS boosters (id INTEGER PRIMARY KEY, username TEXT, so2_id TEXT, status TEXT DEFAULT "active")""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS booster_applications (id INTEGER PRIMARY KEY AUTOINCREMENT, tg_id INTEGER, username TEXT, age INTEGER, main_mmr TEXT, main_id TEXT, twinks_count INTEGER, status TEXT DEFAULT "pending")""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)""")
    cursor.execute("""INSERT OR IGNORE INTO settings (key, value) VALUES ("orders_topic_id", "1")""")
    cursor.execute("""INSERT OR IGNORE INTO settings (key, value) VALUES ("applications_topic_id", "1")""")
    conn.commit()
    conn.close()
    
def get_setting(key, default=None):
    conn = sqlite3.connect("databases.db")
    cursor = conn.cursor()
    cursor.execute("""SELECT value FROM settings WHERE key = ?""", (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else default

def set_setting(key, value):
    conn = sqlite3.connect("databases.db")
    cursor = conn.cursor()
    cursor.execute("""INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)""", (key, value))
    conn.commit()
    conn.close()

def add_user(tg_id, username, so2_id):
    try:
        so2_id_int = int(so2_id)
    except ValueError:
        return False
    
    conn = sqlite3.connect("databases.db")
    cursor = conn.cursor()
    cursor.execute("""INSERT OR IGNORE INTO users (tg_id, username, so2_id) VALUES (?, ?, ?)""", 
                   (tg_id, username, so2_id_int))
    conn.commit()
    conn.close()
    return True
    
def get_user(tg_id):
    conn = sqlite3.connect("databases.db")
    cursor = conn.cursor()
    cursor.execute("""SELECT * FROM users WHERE tg_id = ?""", (tg_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def create_order(buyer_id, game_mode, range_now, range_to_boost, boost_format):
    conn = sqlite3.connect("databases.db")
    cursor = conn.cursor()
    cursor.execute("""INSERT INTO orders (buyer_id, game_mode, range_now, range_to_boost, boost_format) VALUES (?, ?, ?, ?, ?)""", 
                   (buyer_id, game_mode, range_now, range_to_boost, boost_format))
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return order_id

def get_order(order_id):
    conn = sqlite3.connect("databases.db")
    cursor = conn.cursor()
    cursor.execute("""SELECT * FROM orders WHERE id = ?""", (order_id,))
    order = cursor.fetchone()
    conn.close()
    return order

def update_order_price(order_id, price):
    conn = sqlite3.connect("databases.db")
    cursor = conn.cursor()
    cursor.execute("""UPDATE orders SET price = ?, boost_status = "priced" WHERE id = ?""", 
                   (price, order_id))
    conn.commit()
    conn.close()

def assign_order_to_booster(order_id, booster_id):
    conn = sqlite3.connect("databases.db")
    cursor = conn.cursor()
    cursor.execute("""UPDATE orders SET booster_id = ?, boost_status = "assigned" WHERE id = ?""", 
                   (booster_id, order_id))
    conn.commit()
    conn.close()

def get_active_boosters():
    conn = sqlite3.connect("databases.db")
    cursor = conn.cursor()
    cursor.execute("""SELECT * FROM boosters WHERE status = "active" ORDER BY id""")
    boosters = cursor.fetchall()
    conn.close()
    return boosters

def get_booster(tg_id):
    conn = sqlite3.connect("databases.db")
    cursor = conn.cursor()
    cursor.execute("""SELECT * FROM boosters WHERE id = ?""", (tg_id,))
    booster = cursor.fetchone()
    conn.close()
    return booster

def create_booster_application(tg_id, username, age, main_mmr, main_id, twinks_count):
    conn = sqlite3.connect("databases.db")
    cursor = conn.cursor()
    cursor.execute("""INSERT INTO booster_applications (tg_id, username, age, main_mmr, main_id, twinks_count) VALUES (?, ?, ?, ?, ?, ?)""", 
                   (tg_id, username, age, main_mmr, main_id, twinks_count))
    app_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return app_id

def get_booster_application(app_id):
    conn = sqlite3.connect("databases.db")
    cursor = conn.cursor()
    cursor.execute("""SELECT * FROM booster_applications WHERE id = ?""", (app_id,))
    app = cursor.fetchone()
    conn.close()
    return app

def update_application_status(app_id, status, tg_id=None):
    conn = sqlite3.connect("databases.db")
    cursor = conn.cursor()
    cursor.execute("""UPDATE booster_applications SET status = ? WHERE id = ?""", (status, app_id))
    
    if status == "approved" and tg_id:
        app = get_booster_application(app_id)
        cursor.execute("""INSERT OR IGNORE INTO boosters (id, username, so2_id) VALUES (?, ?, ?)""", 
                       (tg_id, app[2], app[5]))
    
    conn.commit()
    conn.close()

def get_boosters():
    conn = sqlite3.connect("databases.db")
    cursor = conn.cursor()
    cursor.execute("""SELECT * FROM boosters WHERE status = "active" OR status = "pending" ORDER BY id""")
    boosters = cursor.fetchall()
    conn.close()
    return boosters

def update_booster_status(booster_id, status):
    conn = sqlite3.connect("databases.db")
    cursor = conn.cursor()
    cursor.execute("""UPDATE boosters SET status = ? WHERE id = ?""", (status, booster_id))
    conn.commit()
    conn.close()

init_db()

bot = Bot("8233932395:AAEsKNyZ7xAdz9rtd5oXeU50ny6Rq2-N2wA")
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class WaitingForID(StatesGroup):
    input = State()

class OrderStates(StatesGroup):
    game_mode = State()  # Новое состояние для выбора режима игры
    range_now = State()
    range_to_boost = State()
    boost_format = State()

class BoosterApplicationStates(StatesGroup):
    age = State()
    main_mmr = State()
    main_id = State()
    twinks_count = State()

class OwnerStates(StatesGroup):
    waiting_for_price = State()

def get_main_menu(tg_id: int = None, username: str = None, is_owner: bool = False) -> tuple[str, InlineKeyboardMarkup]:
    so2_id = "не указан"
    if tg_id:
        user = get_user(tg_id)
        if user:
            so2_id = user[2]
    
    text = (
        f"👋 Приветствуем вас в WONDER BOOST, <b>{username or 'друг'}</b>!\n\n"
        f"🆔️ Ваш SO2 ID: <b>{so2_id}</b>\n"
        "・<b>📌 Отзывы</b> — канал с отзывами о нашей работе\n"
        "・<b>💰 Прайс–лист</b> — цены на наши услуги\n"
        "・<b>📜 Правила</b> — правила предоставления наших услуг\n"
        "・<b>🚀 Заказать буст</b> — повысить звание в Standoff 2 по низкой цене\n"
        "・<b>👨‍💻 Подать заявку на бустера</b> — присоединиться к нашей команде"
    )
    
    if is_owner:
        text += "\n・<b>⚙️ Управление бустерами</b> — просмотр и управление командой\n・<b>⚙️ Настройки</b> — настройка бота"
    
    text += "\n\n👆 Выбери действие:"
    
    kb = [
        [InlineKeyboardButton(text="📌 Отзывы", url="https://t.me/otz_wondbs")],
        [InlineKeyboardButton(text="💰 Прайс–лист", callback_data="price")],
        [InlineKeyboardButton(text="📜 Правила", callback_data="rules")],
        [InlineKeyboardButton(text="🚀 Заказать буст", callback_data="order")],
        [InlineKeyboardButton(text="👨‍💻 Подать заявку на бустера", callback_data="booster_apply")]
    ]
    
    if is_owner:
        kb.append([InlineKeyboardButton(text="⚙️ Управление бустерами", callback_data="manage_boosters")])
        kb.append([InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")])
    
    markup = InlineKeyboardMarkup(inline_keyboard=kb)
    return text, markup

async def show_main_menu(target: Message | CallbackQuery, edit: bool = False):
    user_id = target.from_user.id
    username = target.from_user.first_name
    is_owner = (user_id == OWNER_ID)

    if is_owner:
        if not target.from_user.username:
            if isinstance(target, CallbackQuery):
                await target.message.answer(
                    "❌ <b>У вас не установлен username в Telegram!</b>\n\n"
                    "Для использования бота необходимо установить username:\n"
                    "1. Откройте настройки Telegram\n"
                    "2. Перейдите в раздел 'Имя пользователя'\n"
                    "3. Установите уникальный username\n"
                    "4. Перезапустите бота командой /start",
                    parse_mode="HTML"
                )
                await target.answer()
                return
            elif isinstance(target, Message):
                await target.answer(
                    "❌ <b>У вас не установлен username в Telegram!</b>\n\n"
                    "Для использования бота необходимо установить username:\n"
                    "1. Откройте настройки Telegram\n"
                    "2. Перейдите в раздел 'Имя пользователя'\n"
                    "3. Установите уникальный username\n"
                    "4. Перезапустите бота командой /start",
                    parse_mode="HTML"
                )
                return
    
    text, markup = get_main_menu(user_id, username, is_owner)
    
    if isinstance(target, CallbackQuery) and target.data == "main_menu":
        if os.path.exists("banner.jpg"):
            photo = FSInputFile("banner.jpg")
            
            try:
                if edit:
                    try:
                        await target.message.edit_media(
                            media=InputMediaPhoto(
                                media=photo,
                                caption=text,
                                parse_mode="HTML"
                            ),
                            reply_markup=markup
                        )
                    except Exception as e:
                        await target.message.delete()
                        await target.message.answer_photo(
                            photo=photo,
                            caption=text,
                            parse_mode="HTML",
                            reply_markup=markup
                        )
                else:
                    await target.message.answer_photo(
                        photo=photo,
                        caption=text,
                        parse_mode="HTML",
                        reply_markup=markup
                    )
                    
            except Exception as e:
                if edit:
                    await target.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
                else:
                    await target.message.answer(text, parse_mode="HTML", reply_markup=markup)
        else:
            if edit:
                await target.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
            else:
                await target.message.answer(text, parse_mode="HTML", reply_markup=markup)
    
    elif isinstance(target, Message) and target.text == "/start":
        if os.path.exists("banner.jpg"):
            photo = FSInputFile("banner.jpg")
            await target.answer_photo(
                photo=photo,
                caption=text,
                parse_mode="HTML",
                reply_markup=markup
            )
        else:
            await target.answer(text, parse_mode="HTML", reply_markup=markup)
    
    else:
        if isinstance(target, CallbackQuery):
            if edit:
                await target.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
            else:
                await target.message.answer(text, parse_mode="HTML", reply_markup=markup)
            await target.answer()
        elif isinstance(target, Message):
            await target.answer(text, parse_mode="HTML", reply_markup=markup)
    
    if isinstance(target, CallbackQuery):
        await target.answer()

@dp.message(Command("start"))
async def start(message: Message, state: FSMContext):
    user = get_user(message.from_user.id)
    
    if not message.from_user.username:
        await message.answer(
            "❌ <b>У вас не установлен username в Telegram!</b>\n\n"
            "Для использования бота необходимо установить username:\n"
            "1. Откройте настройки Telegram\n"
            "2. Перейдите в раздел 'Имя пользователя'\n"
            "3. Установите уникальный username\n"
            "4. Перезапустите бота командой /start",
            parse_mode="HTML"
        )
        return
    
    if not user:
        await message.answer("⚠️ Для продолжения работы с ботом, введите свой Standoff 2 ID:")
        await state.set_state(WaitingForID.input)
    else:
        await show_main_menu(message)

@dp.message(WaitingForID.input)
async def process_id_input(message: Message, state: FSMContext):
    so2_id = message.text.strip()
    
    if not message.from_user.username:
        await message.answer(
            "❌ У вас не установлен username в Telegram!\n\n"
            "Для продолжения работы необходимо установить username:\n"
            "1. Откройте настройки Telegram\n"
            "2. Перейдите в раздел 'Имя пользователя'\n"
            "3. Установите уникальный username\n"
            "4. Попробуйте снова ввести свой Standoff 2 ID"
        )
        await state.set_state(WaitingForID.input)
        return
    
    if add_user(message.from_user.id, message.from_user.username, so2_id):
        await message.answer("✅ Ваш ID успешно сохранен! Используйте /start для продолжения.")
    else:
        await message.answer("❌ Неверный формат ID. Введите целое число.")
        await state.set_state(WaitingForID.input)
    await state.clear()

@dp.callback_query(F.data == "price")
async def show_price(callback: CallbackQuery):
    mk = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 В меню", callback_data="main_menu")]])
    
    try:
        await callback.message.edit_text(
            "<b>❗️ ЦЕНЫ НА БУСТ ❗️</b>\n\n• Калибровка — 200₽ / 300G\n\n• Бронза 1 → Бронза 2 — 15₽ / 30G\n• Бронза 2 → Бронза 3 — 15₽ / 30G\n• Бронза 3 → Бронза 4 — 15₽ / 30G\n• Бронза 4 → Сильвер 1 — 20₽ / 40G\n\n• Сильвер 1 → Сильвер 2 — 20₽ / 40G\n• Сильвер 2 → Сильвер 3 — 20₽ / 40G\n• Сильвер 3 → Сильвер 4 — 20₽ / 40G\n• Сильвер 4 → Голд 1 — 30₽ / 50G\n\n• Голд 1 → Голд 2 — 30₽ / 55G\n• Голд 2 → Голд 3 — 40₽ / 55G\n• Голд 3 → Голд 4 — 40₽ / 55G\n• Голд 4 → Феникс — 50₽ / 90G\n\n• Феникс → Ренжер — 90₽ / 125G\n• Рейнджер → Чемпион — 100₽ / 150G\n• Чемпион → Мастер — 130₽ / 160G\n\n• Мастер → Элита — 200₽ / 300G\n• Элита → Легенда — 400₽ / 600G\n\n⸻\n\n⚠️ <b>Буст в лобби — цена x1,4</b>\n\n❕ Цены одинаковые для всех режимов\n🔹 Буст звания клана — цена в ЛС", 
            reply_markup=mk, 
            parse_mode="HTML"
        )
    except:
        await callback.message.answer(
            "<b>❗️ ЦЕНЫ НА БУСТ ❗️</b>\n\n• Калибровка — 200₽ / 300G\n\n• Бронза 1 → Бронза 2 — 15₽ / 30G\n• Бронза 2 → Бронза 3 — 15₽ / 30G\n• Бронза 3 → Бронза 4 — 15₽ / 30G\n• Бронза 4 → Сильвер 1 — 20₽ / 40G\n\n• Сильвер 1 → Сильвер 2 — 20₽ / 40G\n• Сильвер 2 → Сильвер 3 — 20₽ / 40G\n• Сильвер 3 → Сильвер 4 — 20₽ / 40G\n• Сильвер 4 → Голд 1 — 30₽ / 50G\n\n• Голд 1 → Голд 2 — 30₽ / 55G\n• Голд 2 → Голд 3 — 40₽ / 55G\n• Голд 3 → Голд 4 — 40₽ / 55G\n• Голд 4 → Феникс — 50₽ / 90G\n\n• Феникс → Ренжер — 90₽ / 125G\n• Рейнджер → Чемпион — 100₽ / 150G\n• Чемпион → Мастер — 130₽ / 160G\n\n• Мастер → Элита — 200₽ / 300G\n• Элита → Легенда — 400₽ / 600G\n\n⸻\n\n⚠️ <b>Буст в лобби — цена x1,4</b>\n\n❕ Цены одинаковые для всех режимов\n🔹 Буст звания клана — цена в ЛС", 
            reply_markup=mk, 
            parse_mode="HTML"
        )
    await callback.answer()

@dp.callback_query(F.data == "rules")
async def show_rules(callback: CallbackQuery):
    mk = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 В меню", callback_data="main_menu")]])
    
    try:
        await callback.message.edit_text(
            '''📜 <b>Правила буста</b>\n\n❕Оплата возврату не подлежит❕\n\n<b>Запрещено:</b>\n\nПиар другого бустера\n• Наказание: отмена буста\n\nИгра без бустера в период активного буста\n• Наказание: доплата или отмена буста\n\nУмышленный слив MMR\n• Наказание: доплата или отмена буста\n\nИгра с софтом в пати до начала буста, из-за чего была отменена (победная) игра\n• Наказание: доплата или отмена буста\n\nРуин буста\n• Наказание: предупреждение, при повторе — отмена буста\n\nИгнорирование сообщений более 24 часов\n• Наказание: доплата или отмена буста\n\nОскорбления в сторону бустера или проекта\n• Наказание: предупреждение, при повторе — отмена буста''',
            reply_markup=mk, 
            parse_mode="HTML"
        )
    except:
        await callback.message.answer(
            '''📜 <b>Правила буста</b>\n\n❕Оплата возврату не подлежит❕\n\n<b>Запрещено:</b>\n\nПиар другого бустера\n• Наказание: отмена буста\n\nИгра без бустера в период активного буста\n• Наказание: доплата или отмена буста\n\nУмышленный слив MMR\n• Наказание: доплата или отмена буста\n\nИгра с софтом в пати до начала буста, из-за чего была отменена (победная) игра\n• Наказание: доплата или отмена буста\n\nРуин буста\n• Наказание: предупреждение, при повторе — отмена буста\n\nИгнорирование сообщений более 24 часов\n• Наказание: доплата или отмена буста\n\nОскорбления в сторону бустера или проекта\n• Наказание: предупреждение, при повторе — отмена буста''',
            reply_markup=mk, 
            parse_mode="HTML"
        )
    await callback.answer()

@dp.callback_query(F.data == "main_menu")
async def back_to_menu(callback: CallbackQuery):
    await show_main_menu(callback, edit=True)

@dp.callback_query(F.data == "order")
async def start_order(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    
    if not callback.from_user.username:
        await callback.message.answer(
            "❌ <b>У вас не установлен username в Telegram!</b>\n\n"
            "Для создания заказа необходимо установить username:\n"
            "1. Откройте настройки Telegram\n"
            "2. Перейдите в раздел 'Имя пользователя'\n"
            "3. Установите уникальный username\n"
            "4. Перезапустите бота командой /start"
        )
        return
    
    # Кнопки для выбора режима игры
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="ММ"), KeyboardButton(text="Союзники")],
            [KeyboardButton(text="Битва кланов"), KeyboardButton(text="↩️ Отменить заказ")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await callback.message.answer(
        "🎮 <b>Выберите режим игры:</b>\n\n"
        "• <b>ММ</b> — Competitive Matchmaking\n"
        "• <b>Союзники</b> — Allies\n"
        "• <b>Битва кланов</b> — Clan Wars\n\n"
        "Нажмите на кнопку ниже:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await state.set_state(OrderStates.game_mode)

@dp.message(OrderStates.game_mode)
async def process_game_mode(message: Message, state: FSMContext):
    if message.text == "↩️ Отменить заказ":
        await message.answer("❌ Создание заказа отменено.", reply_markup=ReplyKeyboardRemove())
        await show_main_menu(message)
        await state.clear()
        return
    
    game_modes = ["ММ", "Союзники", "Битва кланов"]
    if message.text not in game_modes:
        await message.answer("❌ Пожалуйста, выберите режим игры из предложенных кнопок:")
        return
    
    await state.update_data(game_mode=message.text)
    await message.answer("📝 Введите ваш текущий ранг (например: Silver 3, Gold 1, Phoenix):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(OrderStates.range_now)

@dp.message(OrderStates.range_now)
async def process_range_now(message: Message, state: FSMContext):
    await state.update_data(range_now=message.text)
    await message.answer("🎯 Введите ранг, до которого хотите выполнить буст:")
    await state.set_state(OrderStates.range_to_boost)

@dp.message(OrderStates.range_to_boost)
async def process_range_to_boost(message: Message, state: FSMContext):
    await state.update_data(range_to_boost=message.text)
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Передача аккаунта"), KeyboardButton(text="Через лобби")],
            [KeyboardButton(text="↩️ Отменить заказ")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer(
        "📋 <b>Выберите тип буста:</b>\n\n"
        "• <b>Передача аккаунта</b> — бустер заходит на ваш аккаунт\n"
        "• <b>Через лобби</b> — бустер играет с вами в пати\n\n"
        "Нажмите на кнопку ниже или напишите нужный вариант:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await state.set_state(OrderStates.boost_format)

@dp.message(OrderStates.boost_format)
async def process_boost_format(message: Message, state: FSMContext):
    if message.text == "↩️ Отменить заказ":
        await message.answer("❌ Создание заказа отменено.", reply_markup=ReplyKeyboardRemove())
        await show_main_menu(message)
        await state.clear()
        return
    
    boost_format = None
    if message.text in ["Передача аккаунта", "Через лобби"]:
        boost_format = message.text
    else:
        text_lower = message.text.lower()
        if any(word in text_lower for word in ["передач", "аккаунт", "заход"]):
            boost_format = "Передача аккаунта"
        elif any(word in text_lower for word in ["лобби", "пати", "вместе"]):
            boost_format = "Через лобби"
        else:
            await message.answer(
                "❌ Пожалуйста, выберите правильный тип буста:\n"
                "• Передача аккаунта\n"
                "• Через лобби"
            )
            return
    
    data = await state.get_data()
    
    # Создаем заказ с новым полем game_mode
    order_id = create_order(
        message.from_user.id, 
        data['game_mode'],  # Добавлено game_mode
        data['range_now'], 
        data['range_to_boost'], 
        boost_format
    )
    
    user = get_user(message.from_user.id)
    so2_id = user[2] if user else "не указан"
    
    # 1. Отправляем заказ в канал (только уведомление, без кнопки принятия)
    try:
        await bot.send_message(
            ORDERS_CHANNEL_ID,
            f"📦 <b>НОВЫЙ ЗАКАЗ #{order_id}</b>\n\n"
            f"👤 Клиент: {message.from_user.first_name}\n"
            f"📝 Юзернейм: @{message.from_user.username}\n"
            f"🆔 ID: {message.from_user.id}\n"
            f"🎮 SO2 ID: {so2_id}\n\n"
            f"📊 <b>Детали заказа:</b>\n"
            f"• Режим: {data['game_mode']}\n"  # Добавлено
            f"• Текущий ранг: {data['range_now']}\n"
            f"• Желаемый ранг: {data['range_to_boost']}\n"
            f"• Формат: {boost_format}\n\n"
            f"⏳ <i>Ожидает перенаправления бустерам</i>",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Ошибка отправки заказа в канал: {e}")
    
    # 2. Отправляем админу сообщение с кнопкой для пересылки в чат бустеров
    forward_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Переслать бустерам", callback_data=f"forward_to_boosters_{order_id}")]
    ])
    
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"📦 <b>НОВЫЙ ЗАКАЗ #{order_id}</b>\n\n"
                f"👤 Клиент: {message.from_user.first_name}\n"
                f"📝 Юзернейм: @{message.from_user.username}\n"
                f"🆔 ID: {message.from_user.id}\n"
                f"🎮 SO2 ID: {so2_id}\n\n"
                f"📊 <b>Детали заказа:</b>\n"
                f"• Режим: {data['game_mode']}\n"  # Добавлено
                f"• Текущий ранг: {data['range_now']}\n"
                f"• Желаемый ранг: {data['range_to_boost']}\n"
                f"• Формат: {boost_format}\n\n"
                f"<b>Нажмите кнопку ниже, чтобы переслать заказ бустерам:</b>",
                parse_mode="HTML",
                reply_markup=forward_keyboard
            )
        except Exception as e:
            print(f"Ошибка отправки админу: {e}")
    
    await message.answer(
        f"✅ <b>Ваш заказ №{order_id} успешно принят!</b>\n\n"
        f"📋 <b>Детали заказа:</b>\n"
        f"• Режим: {data['game_mode']}\n"  # Добавлено
        f"• Текущий ранг: {data['range_now']}\n"
        f"• Желаемый ранг: {data['range_to_boost']}\n"
        f"• Формат: {boost_format}\n\n"
        "⏳ <i>Ожидайте, скоро администратор обработает ваш заказ.</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )
    
    await state.clear()

@dp.callback_query(F.data.startswith("forward_to_boosters_"))
async def forward_to_boosters(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔️ У вас нет доступа!")
        return
    
    order_id = int(callback.data.split("_")[3])
    order = get_order(order_id)
    
    if not order:
        await callback.answer("Заказ не найден!")
        return
    
    # Получаем информацию о пользователе
    user = get_user(order[1])
    so2_id = user[2] if user else "не указан"
    
    # Получаем username пользователя
    from sqlite3 import connect
    conn = connect("databases.db")
    cursor = conn.cursor()
    cursor.execute("""SELECT username FROM users WHERE tg_id = ?""", (order[1],))
    user_data = cursor.fetchone()
    conn.close()
    
    username = user_data[0] if user_data else "не указан"
    
    # Клавиатура для бустеров с кнопкой принятия заказа
    order_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Беру заказ", callback_data=f"take_order_{order_id}")]
    ])
    
    # Отправляем заказ в чат бустеров
    try:
        orders_topic_id = get_setting("orders_topic_id", "1")
        
        # Упоминаем активных бустеров
        boosters = get_active_boosters()
        mention_tags = ""
        for booster in boosters:
            mention_tags += f"@{booster[1]} "
        
        if mention_tags:
            mention_message = await bot.send_message(
                BOOSTERS_CHAT_ID,
                f"👥 <b>Новый заказ!</b> {mention_tags}",
                parse_mode="HTML",
                message_thread_id=int(orders_topic_id) if orders_topic_id != "1" else None
            )
        
        order_message = await bot.send_message(
            BOOSTERS_CHAT_ID,
            f"📦 <b>НОВЫЙ ЗАКАЗ #{order_id}</b>\n\n"
            f"👤 Клиент: {username}\n"
            f"📝 Юзернейм: @{username}\n"
            f"🆔 ID: {order[1]}\n"
            f"🎮 SO2 ID: {so2_id}\n\n"
            f"📊 <b>Детали заказа:</b>\n"
            f"• Режим: {order[2]}\n"  # game_mode
            f"• Текущий ранг: {order[3]}\n"  # range_now
            f"• Желаемый ранг: {order[4]}\n"  # range_to_boost
            f"• Формат: {order[5]}\n\n"  # boost_format
            f"💰 <b>Цена:</b> <i>не установлена</i>\n\n"
            f"<b>Для установки цены нажмите на кнопку ниже:</b>",
            parse_mode="HTML",
            reply_markup=order_keyboard,
            message_thread_id=int(orders_topic_id) if orders_topic_id != "1" else None
        )
        
        # Обновляем сообщение админу
        await callback.message.edit_text(
            f"{callback.message.text}\n\n"
            f"✅ <b>Заказ #{order_id} переслан бустерам!</b>\n"
            f"Бустеры могут взять заказ в чате.",
            parse_mode="HTML"
        )
        
        # Отправляем клиенту уведомление
        await bot.send_message(
            order[1],
            f"📢 <b>Ваш заказ #{order_id} отправлен бустерам!</b>\n\n"
            f"Скоро с вами свяжется бустер для выполнения заказа.",
            parse_mode="HTML"
        )
        
        await callback.answer(f"Заказ #{order_id} переслан бустерам!")
        
    except Exception as e:
        print(f"Ошибка отправки заказа в группу: {e}")
        await callback.answer(f"Ошибка: {e}")

@dp.callback_query(F.data.startswith("take_order_"))
async def take_order(callback: CallbackQuery, state: FSMContext):
    if not get_booster(callback.from_user.id):
        await callback.answer("⛔️ Вы не бустер!")
        return
    
    order_id = int(callback.data.split("_")[2])
    order = get_order(order_id)
    
    if not order:
        await callback.answer("Заказ не найден!")
        return
    
    if order[8] == "assigned":  # boost_status
        await callback.answer("❌ Этот заказ уже взят!")
        return
    
    booster_id = callback.from_user.id
    assign_order_to_booster(order_id, booster_id)
    
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.edit_text(
        f"{callback.message.text}\n\n"
        f"✅ <b>Заказ #{order_id} взят бустером:</b>\n"
        f"👤 @{callback.from_user.username}",
        parse_mode="HTML"
    )
    
    await bot.send_message(
        order[1],
        f"👤 <b>Ваш заказ #{order_id} взят бустером!</b>\n\n"
        f"Бустер: @{callback.from_user.username}\n"
        f"Скоро он свяжется с вами для выполнения заказа.",
        parse_mode="HTML"
    )
    
    await callback.answer(f"Вы взяли заказ #{order_id}")

# Остальной код остается без изменений...

@dp.callback_query(F.data == "booster_apply")
async def start_booster_application(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    
    if not callback.from_user.username:
        await callback.message.answer(
            "❌ <b>У вас не установлен username в Telegram!</b>\n\n"
            "Для подачи заявки необходимо установить username:\n"
            "1. Откройте настройки Telegram\n"
            "2. Перейдите в раздел 'Имя пользователя'\n"
            "3. Установите уникальный username\n"
            "4. Перезапустите бота командой /start"
        )
        return
    
    await callback.message.answer(
        "📝 <b>Анкета для бустера</b>\n\n"
        "1. Сколько вам лет?\n\n"
        "Введите ваш возраст (только число):",
        parse_mode="HTML"
    )
    await state.set_state(BoosterApplicationStates.age)

@dp.message(BoosterApplicationStates.age)
async def process_booster_age(message: Message, state: FSMContext):
    try:
        age = int(message.text)
        if age < 14 or age > 60:
            await message.answer("❌ Возраст должен быть от 14 до 60 лет. Введите корректный возраст:")
            return
        await state.update_data(age=age)
        await message.answer(
            "2. Какой MMR на основном аккаунте?\n\n"
            "Введите MMR в формате:\n"
            "• <b>MM</b> (например: 1500)\n"
            "• <b>Напы</b> (например: Напы 5)\n"
            "• <b>Дуэли</b> (например: Дуэли 10)\n\n"
            "Примеры: 1800, Напы 7, Дуэли 15",
            parse_mode="HTML"
        )
        await state.set_state(BoosterApplicationStates.main_mmr)
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число (например: 18):")

@dp.message(BoosterApplicationStates.main_mmr)
async def process_main_mmr(message: Message, state: FSMContext):
    await state.update_data(main_mmr=message.text)
    await message.answer(
        "3. Введите ID вашего основного аккаунта Standoff 2:"
    )
    await state.set_state(BoosterApplicationStates.main_id)

@dp.message(BoosterApplicationStates.main_id)
async def process_main_id(message: Message, state: FSMContext):
    await state.update_data(main_id=message.text)
    await message.answer(
        "4. Сколько у вас твинков (вторых аккаунтов)?\n\n"
        "Введите количество (число):"
    )
    await state.set_state(BoosterApplicationStates.twinks_count)

@dp.message(BoosterApplicationStates.twinks_count)
async def process_twinks_count(message: Message, state: FSMContext):
    try:
        twinks_count = int(message.text)
        await state.update_data(twinks_count=twinks_count)
        
        data = await state.get_data()
        app_id = create_booster_application(
                tg_id=message.from_user.id,
             username=message.from_user.username,
            age=data['age'],
            main_mmr=data['main_mmr'],
            main_id=data['main_id'],
            twinks_count=data['twinks_count']
        )
        
        try:
            applications_topic_id = get_setting("applications_topic_id", "1")
            kb = [[InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_app_{app_id}")], [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_app_{app_id}")]]
            mk = InlineKeyboardMarkup(inline_keyboard=kb)
            for admin_id in ADMIN_IDS:
                await bot.send_message(
                admin_id,
                f"📝 <b>НОВАЯ ЗАЯВКА НА БУСТЕРА #{app_id}</b>\n\n"
                f"👤 Кандидат: {message.from_user.first_name}\n"
                f"📝 Юзернейм: @{message.from_user.username}\n"
                f"🆔 ID: {message.from_user.id}\n\n"
                f"📋 <b>Анкета:</b>\n"
                f"• Возраст: {data['age']}\n"
                f"• MMR основного акка: {data['main_mmr']}\n"
                f"• ID основного акка: {data['main_id']}\n"
                f"• Количество твинков: {data['twinks_count']}",
                parse_mode="HTML", reply_markup=mk
            )
        except Exception as e:
            print(f"Ошибка отправки заявки в группу: {e}")
        
        await message.answer(
            f"✅ <b>Ваша заявка №{app_id} отправлена!</b>\n\n"
            "⏳ Ожидайте решения владельца. Мы свяжемся с вами в течение 24 часов.",
            parse_mode="HTML"
        )
        
        await state.clear()
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число:")

@dp.callback_query(F.data == "manage_boosters")
async def manage_boosters(callback: CallbackQuery):
    if callback.from_user.id != OWNER_ID:
        await callback.answer("⛔️ У вас нет доступа!")
        return
    
    await callback.answer()
    
    boosters = get_boosters()
    
    if not boosters:
        await callback.message.answer("📭 Список бустеров пуст.")
        return
    
    text = "👥 <b>Список бустеров:</b>\n\n"
    for i, booster in enumerate(boosters, 1):
        status_emoji = "✅" if booster[3] == "active" else "⏳" if booster[3] == "pending" else "❌"
        text += f"{i}. ID: {booster[0]} | @{booster[1]} | SO2 ID: {booster[2] or 'нет'} | {status_emoji}\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Заявки на бустера", callback_data="view_applications")],
        [InlineKeyboardButton(text="🔙 В меню", callback_data="main_menu")]
    ])
    
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    except:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)

@dp.callback_query(F.data == "settings")
async def settings_menu(callback: CallbackQuery):
    if callback.from_user.id != OWNER_ID:
        await callback.answer("⛔️ У вас нет доступа!")
        return
    
    await callback.answer()
    
    orders_topic = get_setting("orders_topic_id", "1")
    applications_topic = get_setting("applications_topic_id", "1")
    
    text = (
        "⚙️ <b>Настройки бота</b>\n\n"
        f"<b>Группа бустеров:</b> {BOOSTERS_CHAT_ID}\n"
        f"• ID темы для заказов: <b>{orders_topic}</b>\n\n"
        f"<b>Группа для заявок:</b> {BOOSTER_APPLICATIONS_CHAT_ID}\n"
        f"• ID темы для заявок: <b>{applications_topic}</b>\n\n"
        "Используйте команду /setup в нужной теме группы для автоматической настройки."
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 В меню", callback_data="main_menu")]
    ])
    
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    except:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)

@dp.message(Command("setup"))
async def setup_command(message: Message):
    if message.from_user.id != OWNER_ID:
        await message.answer("⛔️ У вас нет доступа к этой команде!")
        return
    
    if not message.message_thread_id:
        await message.answer(
            "❌ <b>Команда /setup работает только в теме группы!</b>\n\n"
            "1. Перейдите в тему группы где должны приходить сообщения\n"
            "2. Отправьте команду /setup в этой теме\n"
            "3. Бот автоматически определит ID темы",
            parse_mode="HTML"
        )
        return
    
    topic_id = message.message_thread_id
    
    if message.chat.id == BOOSTERS_CHAT_ID:
        set_setting("orders_topic_id", str(topic_id))
        await message.answer(
            f"✅ <b>Настройка успешна!</b>\n\n"
            f"ID темы для заказов установлен: <b>{topic_id}</b>\n\n"
            f"Теперь все заказы будут приходить в эту тему.\n"
            f"Ссылка на группу бустеров: {BOOSTERS_CHAT_LINK}",
            parse_mode="HTML"
        )
    elif message.chat.id == BOOSTER_APPLICATIONS_CHAT_ID:
        set_setting("applications_topic_id", str(topic_id))
        await message.answer(
            f"✅ <b>Настройка успешна!</b>\n\n"
            f"ID темы для заявок установлен: <b>{topic_id}</b>\n\n"
            f"Теперь все заявки на бустера будут приходить в эту тему.",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ <b>Неизвестная группа!</b>\n\n"
            "Используйте команду /setup в:\n"
            f"• Группе бустеров: {BOOSTERS_CHAT_ID}\n"
            f"• Группе для заявок: {BOOSTER_APPLICATIONS_CHAT_ID}",
            parse_mode="HTML"
        )

@dp.callback_query(F.data == "view_applications")
async def view_applications(callback: CallbackQuery):
    if callback.from_user.id != OWNER_ID:
        await callback.answer("⛔️ У вас нет доступа!")
        return
    
    await callback.answer()
    
    conn = sqlite3.connect("databases.db")
    cursor = conn.cursor()
    cursor.execute("""SELECT * FROM booster_applications WHERE status = "pending" ORDER BY id DESC""")
    applications = cursor.fetchall()
    conn.close()
    
    if not applications:
        await callback.message.answer("📭 Нет ожидающих заявок.")
        return
    
    text = "📝 <b>Ожидающие заявки:</b>\n\n"
    for app in applications:
        text += f"<b>Заявка #{app[0]}</b>\n"
        text += f"👤 @{app[2]} (ID: {app[1]})\n"
        text += f"• Возраст: {app[3]}\n"
        text += f"• MMR: {app[4]}\n"
        text += f"• ID акка: {app[5]}\n"
        text += f"• Твинков: {app[6]}\n\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="manage_boosters")]
    ])
    
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    except:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("approve_app_"))
async def approve_application(callback: CallbackQuery):
    if callback.from_user.id != OWNER_ID:
        await callback.answer("⛔️ У вас нет доступа!")
        return
    
    app_id = int(callback.data.split("_")[2])
    app = get_booster_application(app_id)
    
    if not app:
        await callback.answer("Заявка не найдена!")
        return
    
    update_application_status(app_id, "approved", app[1])
    
    await bot.send_message(
        app[1],
        f"🎉 <b>Ваша заявка на бустера одобрена!</b>\n\n"
        f"Теперь вы официальный бустер команды WONDER BOOST!\n\n"
        f"📢 <b>Ссылка на чат бустеров:</b>\n"
        f"{BOOSTERS_CHAT_LINK}\n\n"
        "Заходите в чат и ознакомьтесь с правилами!",
        parse_mode="HTML"
    )
    
    await callback.message.edit_text(
        f"{callback.message.text}\n\n"
        f"✅ <b>Заявка #{app_id} одобрена!</b>\n"
        f"Пользователь @{app[2]} уведомлен.\n"
        f"Ссылка на чат отправлена.",
        parse_mode="HTML"
    )
    
    await callback.answer(f"Заявка #{app_id} одобрена!")

@dp.callback_query(F.data.startswith("reject_app_"))
async def reject_application(callback: CallbackQuery):
    if callback.from_user.id != OWNER_ID:
        await callback.answer("⛔️ У вас нет доступа!")
        return
    
    app_id = int(callback.data.split("_")[2])
    app = get_booster_application(app_id)
    
    if not app:
        await callback.answer("Заявка не найдена!")
        return
    
    update_application_status(app_id, "rejected")
    
    await bot.send_message(
        app[1],
        f"❌ <b>Ваша заявка на бустера отклонена.</b>\n\n"
        f"К сожалению, мы не можем принять вас в нашу команду в данный момент.\n"
        f"Вы можете попробовать снова через 30 дней.",
        parse_mode="HTML"
    )
    
    await callback.message.edit_text(
        f"{callback.message.text}\n\n"
        f"❌ <b>Заявка #{app_id} отклонена.</b>\n"
        f"Пользователь @{app[2]} уведомлен.",
        parse_mode="HTML"
    )
    
    await callback.answer(f"Заявка #{app_id} отклонена!")

@dp.callback_query(F.data.startswith("set_price_"))
async def set_price_handler(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != OWNER_ID:
        await callback.answer("⛔️ У вас нет доступа!")
        return
    
    order_id = int(callback.data.split("_")[2])
    order = get_order(order_id)
    
    if not order:
        await callback.answer("Заказ не найден!")
        return
    
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await state.update_data(order_id=order_id)
    await state.set_state(OwnerStates.waiting_for_price)
    
    await callback.message.answer(
        f"💰 <b>Установите цену для заказа #{order_id}</b>\n\n"
        f"Детали заказа:\n"
        f"• Клиент: ID {order[1]}\n"
        f"• Режим: {order[2]}\n"  # game_mode
        f"• Текущий ранг: {order[3]}\n"
        f"• Желаемый ранг: {order[4]}\n"
        f"• Формат: {order[5]}\n\n"
        "Введите цену в формате: <b>500₽</b> или <b>750G</b>",
        parse_mode="HTML"
    )

@dp.message(OwnerStates.waiting_for_price)
async def process_owner_price(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        await message.answer("⛔️ У вас нет доступа!")
        return
    
    data = await state.get_data()
    order_id = data.get('order_id')
    
    if not order_id:
        await message.answer("❌ Ошибка: заказ не найден")
        await state.clear()
        return
    
    price = message.text.strip()
    update_order_price(order_id, price)
    order = get_order(order_id)
    
    if order:
        await bot.send_message(
            order[1],
            f"💰 <b>Цена заказа установлена!</b>\n\n"
            f"📋 <b>Детали заказа #{order_id}:</b>\n"
            f"• Режим: {order[2]}\n"  # game_mode
            f"• Текущий ранг: {order[3]}\n"
            f"• Желаемый ранг: {order[4]}\n"
            f"• Формат: {order[5]}\n"
            f"• Цена: <b>{price}</b>\n\n"
            "Скоро с вами свяжется бустер для выполнения заказа!",
            parse_mode="HTML"
        )
        
        await message.answer(
            f"✅ <b>Цена {price} установлена для заказа #{order_id}</b>\n\n"
            f"Пользователь уведомлен о цене.\n"
            f"Теперь можно передать заказ бустеру.",
            parse_mode="HTML"
        )
    
    await state.clear()

async def main():
    print("Бот запущен...")
    if not os.path.exists("banner.jpg"):
        print("⚠️ Внимание: файл banner.jpg не найден! Будет использоваться текстовое меню.")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
    
if __name__ == "__main__":
    asyncio.run(main())
