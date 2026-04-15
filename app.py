import os
import asyncio
import logging
import random
import time
import json
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

API_TOKEN = os.environ.get("BOT_TOKEN", "8723084939:AAEO8Jd5oLYsAN-JMht4CBh2MUy_XWxH94M")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Файлы для сохранения данных
DATA_FILE = "bot_data.json"

# Загружаем данные из файла
def load_data():
    global user_balances, user_stats, user_levels, daily_streak, game_history
    global daily_quests, last_quest_reset
    
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            user_balances = data.get("user_balances", {})
            user_stats = data.get("user_stats", {})
            user_levels = data.get("user_levels", {})
            daily_streak = data.get("daily_streak", {})
            game_history = data.get("game_history", [])
            daily_quests = data.get("daily_quests", {})
            last_quest_reset = data.get("last_quest_reset", int(time.time()))
    except:
        user_balances = {}
        user_stats = {}
        user_levels = {}
        daily_streak = {}
        game_history = []
        daily_quests = {}
        last_quest_reset = int(time.time())

# Сохраняем данные в файл
def save_data():
    data = {
        "user_balances": user_balances,
        "user_stats": user_stats,
        "user_levels": user_levels,
        "daily_streak": daily_streak,
        "game_history": game_history[-50:],
        "daily_quests": daily_quests,
        "last_quest_reset": last_quest_reset
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

user_balances = {}
user_stats = {}
user_levels = {}
daily_streak = {}
game_history = []
mines_games = {}
blackjack_games = {}

# ==================== ЕЖЕДНЕВНЫЕ ЗАДАНИЯ ====================
def init_quests():
    global daily_quests
    if not daily_quests:
        daily_quests = {
            "play_3_games": {
                "name": "🎲 Сыграть 3 игры",
                "target": 3,
                "reward": 30000,
                "progress": {},
                "completed": {},
                "last_notify": {}
            },
            "win_3_streak": {
                "name": "🏆 Выиграть 3 раза подряд",
                "target": 3,
                "reward": 25000,
                "progress": {},
                "completed": {},
                "last_notify": {},
                "current_streak": {}
            },
            "make_bet": {
                "name": "💰 Сделать любую ставку",
                "target": 1,
                "reward": 10000,
                "progress": {},
                "completed": {},
                "last_notify": {}
            }
        }

# Время последнего сброса заданий
last_quest_reset = int(time.time())

def reset_daily_quests():
    """Сбрасывает прогресс всех заданий для всех пользователей"""
    global last_quest_reset, daily_quests
    for quest_id in daily_quests:
        daily_quests[quest_id]["progress"] = {}
        daily_quests[quest_id]["completed"] = {}
        daily_quests[quest_id]["last_notify"] = {}
        if quest_id == "win_3_streak":
            daily_quests[quest_id]["current_streak"] = {}
    last_quest_reset = int(time.time())
    save_data()

def check_quests_reset():
    """Проверяет, нужно ли сбросить задания (каждые 24 часа)"""
    global last_quest_reset
    if int(time.time()) - last_quest_reset >= 86400:
        reset_daily_quests()
        return True
    return False

def update_quest_progress(uid: int, quest_id: str, increment: int = 1):
    """Обновляет прогресс задания и автоматически выдаёт награду при выполнении"""
    global user_balances
    check_quests_reset()
    
    # Если уже получил награду, не обновляем
    if uid in daily_quests[quest_id].get("completed", {}):
        return 0
    
    current = daily_quests[quest_id]["progress"].get(uid, 0)
    new_progress = current + increment
    daily_quests[quest_id]["progress"][uid] = min(new_progress, daily_quests[quest_id]["target"])
    
    # Проверяем, выполнено ли задание
    if new_progress >= daily_quests[quest_id]["target"] and uid not in daily_quests[quest_id].get("completed", {}):
        reward = daily_quests[quest_id]["reward"]
        
        # Начисляем награду
        user_balances[uid] = user_balances.get(uid, 0) + reward
        daily_quests[quest_id]["completed"][uid] = True
        daily_quests[quest_id]["last_notify"][uid] = True
        
        save_data()
        return reward
    
    return 0

def get_quests_status(uid: int) -> str:
    """Возвращает строку со статусом всех заданий"""
    check_quests_reset()
    lines = []
    for quest_id, quest in daily_quests.items():
        progress = quest["progress"].get(uid, 0)
        target = quest["target"]
        completed = uid in quest.get("completed", {})
        
        if completed:
            status = "✅ ВЫПОЛНЕНО (+{} GRAM)".format(format_amount(quest["reward"]))
            lines.append(f"  {quest['name']}: {status}")
        else:
            status = f"📊 {progress}/{target}"
            lines.append(f"  {quest['name']}: {status}")
    
    return "\n".join(lines)

ADMIN_ID = 6003768110
GAME_COOLDOWN = 15
DAILY_BONUS_BASE = 500
DAILY_BONUS_STREAK_MULTIPLIER = 200
MAX_BETS_PER_MESSAGE = 500

ROULETTE_GIF = "https://i.gifer.com/3P1d3.gif"

pending_bets = []
game_in_progress = False
last_game_time = 0

SUITS = ["♠", "♥", "♦", "♣"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]

def format_amount(amount: int) -> str:
    return f"{amount:,}".replace(",", " ")

def spin_roulette():
    number = random.randint(0, 36)
    if number == 0:
        color_emoji = "🟢"
        color_name = "ЗЕЛЁНОЕ"
    elif number in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]:
        color_emoji = "🔴"
        color_name = "КРАСНОЕ"
    else:
        color_emoji = "⚫"
        color_name = "ЧЁРНОЕ"
    return number, color_emoji, color_name

def normalize_bet(bet: str) -> str:
    bet = bet.lower().strip()
    if bet in ["к", "красное", "красный", "red", "🔴"]: return "красное"
    if bet in ["ч", "чёрное", "черное", "чёрный", "черный", "black", "⚫"]: return "чёрное"
    if bet in ["чёт", "чет", "чётное", "четное", "even"]: return "чётное"
    if bet in ["неч", "нечётное", "нечетное", "odd"]: return "нечётное"
    if bet in ["0", "зеро", "zero", "🟢"]: return "0"
    if bet in ["1-я", "1я", "первая", "первый"]: return "1-я"
    if bet in ["2-я", "2я", "вторая", "второй"]: return "2-я"
    if bet in ["3-я", "3я", "третья", "третий"]: return "3-я"
    return bet

def check_win(bet: str, num: int, color: str) -> bool:
    bet = normalize_bet(bet)
    if bet == "красное" and color == "КРАСНОЕ": return True
    if bet == "чёрное" and color == "ЧЁРНОЕ": return True
    if bet == "чётное" and num != 0 and num % 2 == 0: return True
    if bet == "нечётное" and num % 2 == 1: return True
    if bet == "0" and num == 0: return True
    if bet == "1-12" and 1 <= num <= 12: return True
    if bet == "13-24" and 13 <= num <= 24: return True
    if bet == "25-36" and 25 <= num <= 36: return True
    if bet == "1-я" and num != 0 and num % 3 == 1: return True
    if bet == "2-я" and num != 0 and num % 3 == 2: return True
    if bet == "3-я" and num != 0 and num % 3 == 0: return True
    if bet.isdigit(): return int(bet) == num
    if "-" in bet:
        try:
            parts = bet.split("-")
            if len(parts) == 2:
                start = int(parts[0].strip())
                end = int(parts[1].strip())
                if start > end: start, end = end, start
                return start <= num <= end
        except:
            pass
    return False

def get_multiplier(bet: str) -> int:
    bet = normalize_bet(bet)
    if bet in ["красное", "чёрное", "чётное", "нечётное"]: return 2
    if bet == "0" or bet.isdigit(): return 36
    if bet in ["1-12", "13-24", "25-36", "1-я", "2-я", "3-я"]: return 3
    if "-" in bet:
        try:
            parts = bet.split("-")
            if len(parts) == 2:
                start = int(parts[0].strip())
                end = int(parts[1].strip())
                if start > end: start, end = end, start
                count = end - start + 1
                if count == 2: return 18
                elif count == 3: return 12
                elif count == 4: return 9
                elif count == 6: return 6
                elif count == 8: return 4
                elif count == 12: return 3
                elif count == 18: return 2
                else: return 36 // count if count > 0 else 2
        except:
            pass
    return 2

def get_level(exp: int) -> int:
    if exp < 10: return 1
    elif exp < 30: return 2
    elif exp < 60: return 3
    elif exp < 100: return 4
    else: return 5

def generate_mines_field():
    field = [["⭐" for _ in range(5)] for _ in range(5)]
    mines = random.sample(range(25), 3)
    for m in mines:
        row, col = m // 5, m % 5
        field[row][col] = "💣"
    return field

def format_mines_field(field, revealed):
    lines = []
    for i in range(5):
        row = " ".join(field[i][j] if (i, j) in revealed else "❓" for j in range(5))
        lines.append(row)
    return "\n".join(lines)

def generate_deck():
    deck = [(rank, suit) for rank in RANKS for suit in SUITS]
    random.shuffle(deck)
    return deck

def card_value(card):
    rank = card[0]
    if rank in ["J", "Q", "K"]:
        return 10
    elif rank == "A":
        return 11
    else:
        return int(rank)

def hand_value(hand):
    value = sum(card_value(c) for c in hand)
    aces = sum(1 for c in hand if c[0] == "A")
    while value > 21 and aces > 0:
        value -= 10
        aces -= 1
    return value

def format_cards(hand):
    if not hand:
        return "пусто"
    result = []
    for rank, suit in hand:
        result.append(f"{rank}{suit}")
    return " ".join(result)

def get_mines_keyboard(field, revealed):
    kb = InlineKeyboardMarkup(row_width=5)
    for i in range(5):
        row_buttons = []
        for j in range(5):
            if (i, j) in revealed:
                row_buttons.append(InlineKeyboardButton(field[i][j], callback_data="done"))
            else:
                row_buttons.append(InlineKeyboardButton("❓", callback_data=f"m_{i}_{j}"))
        kb.row(*row_buttons)
    if revealed:
        kb.add(InlineKeyboardButton("💰 Забрать выигрыш", callback_data="cash"))
    return kb

# ==================== ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ ОЧИСТКИ КОМАНД ОТ @ ====================
def clean_command(text: str) -> str:
    """Убирает @username из команды"""
    return text.lower().split('@')[0].strip()

# ==================== КЛАВИАТУРА С КОМАНДАМИ ====================
def get_main_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("💰 Баланс", callback_data="menu_balance"),
        InlineKeyboardButton("📊 Профиль", callback_data="menu_profile"),
        InlineKeyboardButton("🎲 Рулетка", callback_data="menu_roulette"),
        InlineKeyboardButton("💣 Мины", callback_data="menu_mines"),
        InlineKeyboardButton("🃏 Блэкджек", callback_data="menu_blackjack"),
        InlineKeyboardButton("🎁 Задания", callback_data="menu_quests"),
        InlineKeyboardButton("🏆 Топ", callback_data="menu_top"),
        InlineKeyboardButton("❓ Помощь", callback_data="menu_help")
    )
    return kb

# ==================== КОМАНДА ДАТЬ ВСЁ ====================
@dp.message_handler(lambda message: message.reply_to_message and message.text.lower().strip() == 'дать всё')
async def give_all_grams_reply(message: types.Message):
    uid = message.from_user.id
    
    target_id = message.reply_to_message.from_user.id
    target_name = message.reply_to_message.from_user.full_name or "Пользователь"
    
    if uid == target_id:
        await message.reply("❌ Нельзя перевести GRAM самому себе")
        return
    
    sender_balance = user_balances.get(uid, 0)
    
    if sender_balance <= 0:
        await message.reply(f"❌ У вас нет GRAM для перевода! Ваш баланс: {format_amount(sender_balance)} GRAM")
        return
    
    amount = sender_balance
    
    user_balances[uid] = 0
    user_balances[target_id] = user_balances.get(target_id, 0) + amount
    save_data()
    
    await message.reply(
        f"✅ Перевод ВСЕХ GRAM выполнен!\n"
        f"📤 Отправитель: {message.from_user.full_name}\n"
        f"📥 Получатель: {target_name}\n"
        f"💰 Сумма: {format_amount(amount)} GRAM"
    )
    
    try:
        await bot.send_message(
            target_id,
            f"✅ Вам переведены ВСЕ GRAM ({format_amount(amount)} GRAM) от {message.from_user.full_name}\n"
            f"💰 Ваш баланс: {format_amount(user_balances[target_id])} GRAM"
        )
    except:
        pass

# ==================== КОМАНДА ДАТЬ ====================
@dp.message_handler(lambda message: message.reply_to_message and message.text.lower().startswith('дать') and not message.text.lower().startswith('дать всё'))
async def give_grams_reply(message: types.Message):
    uid = message.from_user.id
    text = message.text.strip()
    
    parts = text.split()
    if len(parts) != 2:
        await message.reply("❌ Неправильный формат!\nИспользуйте: `дать 1000` в ответ на сообщение пользователя\nИли: `дать всё` для перевода всех GRAM", parse_mode="HTML")
        return
    
    try:
        amount = int(parts[1])
    except ValueError:
        await message.reply("❌ Сумма должна быть числом\nПример: `дать 500`", parse_mode="HTML")
        return
    
    if amount <= 0:
        await message.reply("❌ Сумма должна быть больше 0")
        return
    
    target_id = message.reply_to_message.from_user.id
    target_name = message.reply_to_message.from_user.full_name or "Пользователь"
    
    if uid == target_id:
        await message.reply("❌ Нельзя перевести GRAM самому себе")
        return
    
    sender_balance = user_balances.get(uid, 0)
    if sender_balance < amount:
        await message.reply(f"❌ Недостаточно GRAM! Ваш баланс: {format_amount(sender_balance)} GRAM")
        return
    
    user_balances[uid] = sender_balance - amount
    user_balances[target_id] = user_balances.get(target_id, 0) + amount
    save_data()
    
    await message.reply(
        f"✅ Перевод выполнен!\n"
        f"📤 Отправитель: {message.from_user.full_name}\n"
        f"📥 Получатель: {target_name}\n"
        f"💰 Сумма: {format_amount(amount)} GRAM\n\n"
        f"💳 Ваш баланс: {format_amount(user_balances[uid])} GRAM"
    )
    
    try:
        await bot.send_message(
            target_id,
            f"✅ Вам переведено {format_amount(amount)} GRAM от {message.from_user.full_name}\n"
            f"💰 Ваш баланс: {format_amount(user_balances[target_id])} GRAM"
        )
    except:
        pass

# ==================== ОБРАБОТЧИКИ КОМАНД ====================
@dp.message_handler(commands=["start"])
async def start_cmd(message: Message):
    init_quests()
    await message.reply(
        "<code>🎰 GOLDEN GRAM ROULETTE\n\n"
        "🎲 СТАВКИ:\n100 чёрное / 250 красное / 500 чётное\n1000 14 / 2000 0 / 5000 1-12\n"
        "Много: 1000 14 23-34 к 0\n\n"
        "💣 МИНЫ: мины 100\n"
        "🃏 БЛЭКДЖЕК: bj 100\n\n"
        "🕹️ КОМАНДЫ:\nб, лог, топ, профиль, бонус, го, отмена, задания\n"
        "дать 500 (ответом на сообщение)\n"
        "дать всё (ответом на сообщение)</code>\n\n"
        "👇 Используйте кнопки меню для навигации",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )

@dp.message_handler(commands=["add_grams"])
async def add_grams(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.reply("❌ Нет прав")
        return
    parts = message.text.split()
    if len(parts) != 2:
        await message.reply("❌ /add_grams 5000")
        return
    try:
        amount = int(parts[1])
    except:
        await message.reply("❌ Сумма числом")
        return
    user_balances[ADMIN_ID] = user_balances.get(ADMIN_ID, 0) + amount
    save_data()
    await message.reply(f"✅ +{format_amount(amount)} GRAM")

@dp.message_handler(lambda message: clean_command(message.text) in ['/profile', '/профиль'])
async def profile_cmd(message: Message):
    uid = message.from_user.id
    name = message.from_user.full_name or "Игрок"
    bal = user_balances.get(uid, 0)
    stats = user_stats.get(uid, {"played": 0, "won": 0, "total_bet": 0, "total_win": 0})
    exp = user_levels.get(uid, 0)
    lvl = get_level(exp)
    winrate = (stats["won"] / stats["played"] * 100) if stats["played"] > 0 else 0
    profit = stats["total_win"] - stats["total_bet"]
    await message.reply(
        f"<code>👤 {name}\n🆔 {uid}\n📊 Уровень: {lvl}\n💰 {format_amount(bal)} GRAM\n\n"
        f"🎲 Игр: {stats['played']}\n🏆 Побед: {stats['won']}\n📈 Винрейт: {winrate:.1f}%\n"
        f"📊 Профит: {format_amount(profit)} GRAM</code>", 
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )

@dp.message_handler(lambda message: clean_command(message.text) == '/top')
async def top_cmd(message: Message):
    if not user_balances:
        await message.reply("📊 Пусто")
        return
    sort_items = sorted(user_balances.items(), key=lambda x: x[1], reverse=True)[:10]
    txt = "🏆 ТОП-10:\n\n"
    for i, (u, b) in enumerate(sort_items, 1):
        try:
            chat = await bot.get_chat(u)
            n = chat.full_name
        except:
            n = str(u)
        txt += f"{i}. {n} — {format_amount(b)} GRAM\n"
    await message.reply(f"<code>{txt}</code>", parse_mode="HTML")

@dp.message_handler(lambda message: clean_command(message.text) in ['/quests', '/задания'])
async def quests_cmd(message: Message):
    uid = message.from_user.id
    status = get_quests_status(uid)
    await message.reply(
        f"<code>🎯 ЕЖЕДНЕВНЫЕ ЗАДАНИЯ\n\n{status}\n\n⏰ Задания обновляются каждые 24 часа\n\n"
        f"✨ Награда выдаётся АВТОМАТИЧЕСКИ при выполнении!</code>",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )

@dp.message_handler(lambda message: clean_command(message.text) in ['/help', '/помощь'])
async def help_cmd(message: Message):
    await message.reply(
        "<code>🎰 GOLDEN GRAM ROULETTE\n\n"
        "🎲 СТАВКИ:\n100 чёрное / 250 красное / 500 чётное\n1000 14 / 2000 0 / 5000 1-12\n"
        "Много: 1000 14 23-34 к 0\n\n"
        "💣 МИНЫ: мины 100\n"
        "🃏 БЛЭКДЖЕК: bj 100\n\n"
        "🕹️ КОМАНДЫ:\nб, лог, топ, профиль, бонус, го, отмена, задания\n"
        "дать 500 (ответом на сообщение)\n"
        "дать всё (ответом на сообщение)</code>",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )

@dp.message_handler(lambda message: clean_command(message.text) == '/bonus')
async def bonus_cmd(message: Message):
    uid = message.from_user.id
    now = int(time.time())
    ds = daily_streak.get(uid, {"last": 0, "streak": 0})
    if now - ds["last"] >= 86400:
        if now - ds["last"] >= 172800:
            ds["streak"] = 0
        ds["streak"] += 1
        bonus = DAILY_BONUS_BASE + (ds["streak"] - 1) * DAILY_BONUS_STREAK_MULTIPLIER
        user_balances[uid] = user_balances.get(uid, 0) + bonus
        ds["last"] = now
        daily_streak[uid] = ds
        save_data()
        await message.reply(f"<code>🎁 +{format_amount(bonus)} GRAM\n🔥 Стрик: {ds['streak']} дн.</code>", parse_mode="HTML")
    else:
        rem = 86400 - (now - ds["last"])
        h, m = rem // 3600, (rem % 3600) // 60
        await message.reply(f"<code>⏰ Через {h} ч {m} мин</code>", parse_mode="HTML")

# ==================== ОБРАБОТЧИКИ МЕНЮ ====================
@dp.callback_query_handler(lambda c: c.data.startswith("menu_"))
async def menu_callback(call: CallbackQuery):
    await call.answer()
    uid = call.from_user.id
    action = call.data[5:]
    
    if action == "balance":
        bal = user_balances.get(uid, 0)
        await call.message.edit_text(
            f"<code>💰 Ваш баланс: {format_amount(bal)} GRAM</code>",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
    
    elif action == "profile":
        name = call.from_user.full_name or "Игрок"
        bal = user_balances.get(uid, 0)
        stats = user_stats.get(uid, {"played": 0, "won": 0, "total_bet": 0, "total_win": 0})
        exp = user_levels.get(uid, 0)
        lvl = get_level(exp)
        winrate = (stats["won"] / stats["played"] * 100) if stats["played"] > 0 else 0
        profit = stats["total_win"] - stats["total_bet"]
        await call.message.edit_text(
            f"<code>👤 {name}\n🆔 {uid}\n📊 Уровень: {lvl}\n💰 {format_amount(bal)} GRAM\n\n"
            f"🎲 Игр: {stats['played']}\n🏆 Побед: {stats['won']}\n📈 Винрейт: {winrate:.1f}%\n"
            f"📊 Профит: {format_amount(profit)} GRAM</code>",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
    
    elif action == "roulette":
        await call.message.edit_text(
            "<code>🎲 СТАВКИ НА РУЛЕТКУ:\n\n"
            "100 чёрное\n250 красное\n500 чётное\n"
            "1000 14\n2000 0\n5000 1-12\n\n"
            "Можно ставить на несколько исходов:\n"
            "1000 14 23-34 к 0</code>",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
    
    elif action == "mines":
        await call.message.edit_text(
            "<code>💣 ИГРА МИНЫ:\n\n"
            "Команда: мины 100\n"
            "Поле 5x5, 3 мины\n"
            "Каждая безопасная клетка +0.14x к множителю\n"
            "Максимальный множитель ~ x4.0</code>",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
    
    elif action == "blackjack":
        await call.message.edit_text(
            "<code>🃏 БЛЭКДЖЕК:\n\n"
            "Команда: bj 100\n"
            "Минимальная ставка: 100 GRAM\n"
            "Блэкджек (21) выплачивает x2.5\n"
            "Обычная победа: x2\n"
            "Сдача: возврат 50%</code>",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
    
    elif action == "quests":
        status = get_quests_status(uid)
        await call.message.edit_text(
            f"<code>🎯 ЕЖЕДНЕВНЫЕ ЗАДАНИЯ\n\n{status}\n\n⏰ Задания обновляются каждые 24 часа\n\n"
            f"✨ Награда выдаётся АВТОМАТИЧЕСКИ при выполнении!</code>",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
    
    elif action == "top":
        if not user_balances:
            await call.message.edit_text("📊 Пусто", reply_markup=get_main_keyboard())
            return
        sort_items = sorted(user_balances.items(), key=lambda x: x[1], reverse=True)[:10]
        txt = "🏆 ТОП-10:\n\n"
        for i, (u, b) in enumerate(sort_items, 1):
            try:
                chat = await bot.get_chat(u)
                n = chat.full_name
            except:
                n = str(u)
            txt += f"{i}. {n} — {format_amount(b)} GRAM\n"
        await call.message.edit_text(f"<code>{txt}</code>", parse_mode="HTML", reply_markup=get_main_keyboard())
    
    elif action == "help":
        await call.message.edit_text(
            "<code>🎰 GOLDEN GRAM ROULETTE\n\n"
            "🎲 СТАВКИ:\n100 чёрное / 250 красное / 500 чётное\n1000 14 / 2000 0 / 5000 1-12\n"
            "Много: 1000 14 23-34 к 0\n\n"
            "💣 МИНЫ: мины 100\n"
            "🃏 БЛЭКДЖЕК: bj 100\n\n"
            "🕹️ КОМАНДЫ:\nб, лог, топ, профиль, бонус, го, отмена, задания\n"
            "дать 500 (ответом на сообщение)\n"
            "дать всё (ответом на сообщение)</code>",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )

# ==================== ФУНКЦИЯ ДЛЯ ОТПРАВКИ УВЕДОМЛЕНИЯ ====================
async def send_quest_complete_notification(uid: int, quest_id: str, reward: int, message_obj=None):
    quest_name = daily_quests[quest_id]["name"]
    new_balance = user_balances.get(uid, 0)
    text = (
        f"🎉 <b>ЗАДАНИЕ ВЫПОЛНЕНО!</b> 🎉\n\n"
        f"📋 {quest_name}\n"
        f"💰 Награда: +{format_amount(reward)} GRAM\n\n"
        f"✨ Награда автоматически зачислена на баланс!\n"
        f"💳 Ваш баланс: {format_amount(new_balance)} GRAM"
    )
    
    try:
        if message_obj:
            await message_obj.reply(text, parse_mode="HTML")
        else:
            await bot.send_message(uid, text, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Ошибка отправки уведомления: {e}")

# ==================== ОСНОВНОЙ ОБРАБОТЧИК ====================
@dp.message_handler()
async def handle(message: Message):
    global pending_bets, game_in_progress, last_game_time, game_history

    uid = message.from_user.id
    name = message.from_user.full_name or "Игрок"
    text = message.text.strip()
    
    # Пропускаем команды
    if text.lower().startswith('/'):
        return
    
    parts = text.split()

    # ==================== БЛЭКДЖЕК ====================
    if text.lower().startswith("bj ") or text.lower().startswith("блекджек "):
        if len(parts) < 2:
            await message.reply("❌ Пример: bj 100")
            return
        try:
            bet = int(parts[1])
        except:
            await message.reply("❌ Пример: bj 100")
            return
        
        if bet < 100:
            await message.reply("❌ Минимальная ставка 100 GRAM")
            return
        
        bal = user_balances.get(uid, 0)
        if bet > bal:
            await message.reply("❌ Недостаточно GRAM")
            return
        
        # Снимаем ставку
        user_balances[uid] = bal - bet
        
        # Обновляем задание "сделать ставку" ТОЛЬКО если ставка >= 100
        if bet >= 100:
            reward = update_quest_progress(uid, "make_bet")
            if reward > 0:
                await send_quest_complete_notification(uid, "make_bet", reward, message)
        
        # Создаём игру
        deck = generate_deck()
        player_hand = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop(), deck.pop()]
        
        blackjack_games[uid] = {
            "bet": bet,
            "deck": deck,
            "player_hand": player_hand,
            "dealer_hand": dealer_hand,
            "active": True,
        }
        
        player_val = hand_value(player_hand)
        dealer_up = dealer_hand[0]
        
        # Проверка на блэкджек
        if player_val == 21:
            win = int(bet * 2.5)
            user_balances[uid] = user_balances.get(uid, 0) + win
            
            if uid not in user_stats:
                user_stats[uid] = {"played": 0, "won": 0, "total_bet": 0, "total_win": 0}
            user_stats[uid]["played"] += 1
            user_stats[uid]["won"] += 1
            user_stats[uid]["total_bet"] += bet
            user_stats[uid]["total_win"] += win
            user_levels[uid] = user_levels.get(uid, 0) + 2
            
            # Обновляем задание "сыграть 3 игры"
            reward_play = update_quest_progress(uid, "play_3_games")
            if reward_play > 0:
                await send_quest_complete_notification(uid, "play_3_games", reward_play, message)
            
            # Обновляем streak побед
            if uid not in daily_quests["win_3_streak"]["current_streak"]:
                daily_quests["win_3_streak"]["current_streak"][uid] = 0
            daily_quests["win_3_streak"]["current_streak"][uid] += 1
            reward_streak = update_quest_progress(uid, "win_3_streak", daily_quests["win_3_streak"]["current_streak"][uid])
            if reward_streak > 0:
                await send_quest_complete_notification(uid, "win_3_streak", reward_streak, message)
            
            del blackjack_games[uid]
            save_data()
            
            await message.reply(
                f"<code>🃏 БЛЭКДЖЕК!\n\n"
                f"Ваши карты: {format_cards(player_hand)} ({player_val})\n"
                f"Карты дилера: {format_cards(dealer_hand)} ({hand_value(dealer_hand)})\n\n"
                f"🎉 ВЫ ВЫИГРАЛИ x2.5!\n"
                f"💰 +{format_amount(win)} GRAM</code>",
                parse_mode="HTML"
            )
            return
        
        # Обычная игра
        kb = InlineKeyboardMarkup(row_width=3)
        kb.add(
            InlineKeyboardButton("🃏 Взять", callback_data="bj_hit"),
            InlineKeyboardButton("✋ Хватит", callback_data="bj_stand"),
            InlineKeyboardButton("🏳️ Сдаюсь", callback_data="bj_surrender")
        )
        
        await message.reply(
            f"<code>🃏 БЛЭКДЖЕК\n"
            f"💰 Ставка: {format_amount(bet)} GRAM\n\n"
            f"Ваши карты: {format_cards(player_hand)} ({player_val})\n"
            f"Карта дилера: {format_cards([dealer_up])}</code>",
            parse_mode="HTML",
            reply_markup=kb
        )
        return

    # ==================== МИНЫ ====================
    if text.lower().startswith("мины "):
        if len(parts) < 2:
            await message.reply("❌ Пример: мины 100")
            return
        try:
            bet = int(parts[1])
        except:
            await message.reply("❌ Пример: мины 100")
            return
        
        if bet < 100:
            await message.reply("❌ Минимальная ставка 100 GRAM")
            return
        
        bal = user_balances.get(uid, 0)
        if bet > bal:
            await message.reply("❌ Недостаточно GRAM")
            return
        
        # Снимаем ставку
        user_balances[uid] = bal - bet
        
        # Обновляем задание "сделать ставку" ТОЛЬКО если ставка >= 100
        if bet >= 100:
            reward = update_quest_progress(uid, "make_bet")
            if reward > 0:
                await send_quest_complete_notification(uid, "make_bet", reward, message)
        
        # Создаём поле мин
        field = generate_mines_field()
        mines_games[uid] = {"bet": bet, "field": field, "revealed": [], "multiplier": 1.0, "active": True}
        save_data()

        kb = get_mines_keyboard(field, [])

        await message.answer(
            f"💎 {name}, вы начали игру минное поле!\n"
            f"📌 Ставка: {format_amount(bet)} GRAM\n"
            f"💲 Выигрыш: x1,0 | {format_amount(bet)} GRAM\n\n"
            f"{format_mines_field(field, [])}",
            reply_markup=kb
        )
        return

    # ==================== ОТМЕНА СТАВОК ====================
    if text.lower() in ["отмена", "отменить"]:
        if game_in_progress:
            await message.reply("⏳ Идёт игра")
            return
        user_bets = [b for b in pending_bets if b["user_id"] == uid]
        if not user_bets:
            await message.reply("❌ Нет ставок")
            return
        refund = sum(b["amount"] for b in user_bets)
        pending_bets = [b for b in pending_bets if b["user_id"] != uid]
        user_balances[uid] = user_balances.get(uid, 0) + refund
        save_data()
        await message.reply(f"✅ Возвращено {format_amount(refund)} GRAM")
        return

    # ==================== ПРОФИЛЬ ====================
    if text.lower() in ["профиль", "profile"]:
        bal = user_balances.get(uid, 0)
        stats = user_stats.get(uid, {"played": 0, "won": 0, "total_bet": 0, "total_win": 0})
        exp = user_levels.get(uid, 0)
        lvl = get_level(exp)
        winrate = (stats["won"] / stats["played"] * 100) if stats["played"] > 0 else 0
        profit = stats["total_win"] - stats["total_bet"]
        await message.reply(
            f"<code>👤 {name}\n🆔 {uid}\n📊 Уровень: {lvl}\n💰 {format_amount(bal)} GRAM\n\n"
            f"🎲 Игр: {stats['played']}\n🏆 Побед: {stats['won']}\n📈 Винрейт: {winrate:.1f}%\n"
            f"📊 Профит: {format_amount(profit)} GRAM</code>", 
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
        return

    # ==================== БОНУС ====================
    if text.lower() == "бонус":
        now = int(time.time())
        ds = daily_streak.get(uid, {"last": 0, "streak": 0})
        if now - ds["last"] >= 86400:
            if now - ds["last"] >= 172800:
                ds["streak"] = 0
            ds["streak"] += 1
            bonus = DAILY_BONUS_BASE + (ds["streak"] - 1) * DAILY_BONUS_STREAK_MULTIPLIER
            user_balances[uid] = user_balances.get(uid, 0) + bonus
            ds["last"] = now
            daily_streak[uid] = ds
            save_data()
            await message.reply(f"<code>🎁 +{format_amount(bonus)} GRAM\n🔥 Стрик: {ds['streak']} дн.</code>", parse_mode="HTML")
        else:
            rem = 86400 - (now - ds["last"])
            h, m = rem // 3600, (rem % 3600) // 60
            await message.reply(f"<code>⏰ Через {h} ч {m} мин</code>", parse_mode="HTML")
        return

    # ==================== БАЛАНС ====================
    if text.lower() in ["б", "баланс"]:
        bal = user_balances.get(uid, 0)
        await message.reply(f"<code>{name}\nБаланс: {format_amount(bal)} GRAM</code>", parse_mode="HTML")
        return

    # ==================== ИСТОРИЯ ====================
    if text.lower() in ["лог", "история"]:
        if not game_history:
            await message.reply("📋 Пусто")
            return
        log_lines = [entry for entry in game_history[-10:]]
        log_text = "\n".join(log_lines)
        await message.reply(f"<code>{log_text}</code>", parse_mode="HTML")
        return

    # ==================== ТОП ====================
    if text.lower() == "топ":
        if not user_balances:
            await message.reply("📊 Пусто")
            return
        sort_items = sorted(user_balances.items(), key=lambda x: x[1], reverse=True)[:10]
        txt = "🏆 ТОП-10:\n\n"
        for i, (u, b) in enumerate(sort_items, 1):
            try:
                chat = await bot.get_chat(u)
                n = chat.full_name
            except:
                n = str(u)
            txt += f"{i}. {n} — {format_amount(b)} GRAM\n"
        await message.reply(f"<code>{txt}</code>", parse_mode="HTML")
        return

    # ==================== ЗАДАНИЯ ====================
    if text.lower() in ["задания", "quests"]:
        status = get_quests_status(uid)
        await message.reply(
            f"<code>🎯 ЕЖЕДНЕВНЫЕ ЗАДАНИЯ\n\n{status}\n\n⏰ Задания обновляются каждые 24 часа\n\n"
            f"✨ Награда выдаётся АВТОМАТИЧЕСКИ при выполнении!</code>",
            parse_mode="HTML"
        )
        return

    # ==================== ПОМОЩЬ ====================
    if text.lower() in ["помощь", "команды", "help"]:
        await message.reply(
            "<code>🎰 GOLDEN GRAM ROULETTE\n\n"
            "🎲 СТАВКИ:\n100 чёрное / 250 красное / 500 чётное\n1000 14 / 2000 0 / 5000 1-12\n"
            "Много: 1000 14 23-34 к 0\n\n"
            "💣 МИНЫ: мины 100\n"
            "🃏 БЛЭКДЖЕК: bj 100\n\n"
            "🕹️ КОМАНДЫ:\nб, лог, топ, профиль, бонус, го, отмена, задания\n"
            "дать 500 (ответом на сообщение)\n"
            "дать всё (ответом на сообщение)</code>",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
        return

    # ==================== ЗАПУСК РУЛЕТКИ ====================
    if text.lower() == "го":
        now = int(time.time())
        if game_in_progress:
            await message.reply("⏳ Идёт игра")
            return
        if now - last_game_time < GAME_COOLDOWN:
            await message.reply(f"⏰ Подожди {GAME_COOLDOWN - (now - last_game_time)} сек")
            return
        if not pending_bets:
            await message.reply("❌ Нет ставок")
            return

        game_in_progress = True
        try:
            gif_msg = await message.answer_animation(ROULETTE_GIF, caption="🎰 Крутим...")
        except:
            gif_msg = None

        await asyncio.sleep(10)

        if gif_msg:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=gif_msg.message_id)
            except:
                pass

        try:
            win_num, win_emoji, win_color = spin_roulette()
            game_history.append(f"{win_emoji} {win_num}")
            if len(game_history) > 10:
                game_history.pop(0)

            all_bets, win_res = [], []
            for b in pending_bets:
                uname, amt, raw = b["user_name"], b["amount"], b["raw_bet"]
                all_bets.append(f"{uname} {format_amount(amt)} GRAM на {raw}")

                if check_win(raw, win_num, win_color):
                    mult = get_multiplier(raw)
                    win_amt = amt * mult
                    user_balances[b["user_id"]] = user_balances.get(b["user_id"], 0) + win_amt

                    if b["user_id"] not in user_stats:
                        user_stats[b["user_id"]] = {"played": 0, "won": 0, "total_bet": 0, "total_win": 0}
                    user_stats[b["user_id"]]["played"] += 1
                    user_stats[b["user_id"]]["won"] += 1
                    user_stats[b["user_id"]]["total_bet"] += amt
                    user_stats[b["user_id"]]["total_win"] += win_amt
                    user_levels[b["user_id"]] = user_levels.get(b["user_id"], 0) + 1
                    
                    # Обновляем streak побед
                    uid_bet = b["user_id"]
                    if uid_bet not in daily_quests["win_3_streak"]["current_streak"]:
                        daily_quests["win_3_streak"]["current_streak"][uid_bet] = 0
                    daily_quests["win_3_streak"]["current_streak"][uid_bet] += 1
                    reward_streak = update_quest_progress(uid_bet, "win_3_streak", daily_quests["win_3_streak"]["current_streak"][uid_bet])
                    if reward_streak > 0:
                        await send_quest_complete_notification(uid_bet, "win_3_streak", reward_streak, message)

                    win_res.append(f"{uname} ставка {format_amount(amt)} GRAM выиграл {format_amount(win_amt)} на {raw}")
                else:
                    if b["user_id"] not in user_stats:
                        user_stats[b["user_id"]] = {"played": 0, "won": 0, "total_bet": 0, "total_win": 0}
                    user_stats[b["user_id"]]["played"] += 1
                    user_stats[b["user_id"]]["total_bet"] += amt
                    user_levels[b["user_id"]] = user_levels.get(b["user_id"], 0) + 1
                    
                    # Сбрасываем streak при проигрыше
                    daily_quests["win_3_streak"]["current_streak"][b["user_id"]] = 0
                
                # Обновляем задание "сыграть 3 игры"
                reward_play = update_quest_progress(b["user_id"], "play_3_games")
                if reward_play > 0:
                    await send_quest_complete_notification(b["user_id"], "play_3_games", reward_play, message)

            save_data()

            await message.answer(f"<code>Рулетка: {win_num} {win_emoji}</code>", parse_mode="HTML")
            for i in range(0, len(all_bets), 50):
                await message.answer("<code>" + "\n".join(all_bets[i:i+50]) + "</code>", parse_mode="HTML")
            for i in range(0, len(win_res), 50):
                await message.answer("<code>" + "\n".join(win_res[i:i+50]) + "</code>", parse_mode="HTML")

        except Exception as e:
            logging.error(f"Ошибка: {e}")
            await message.answer("❌ Ошибка. Ставки возвращены")
            for b in pending_bets:
                user_balances[b["user_id"]] = user_balances.get(b["user_id"], 0) + b["amount"]
            save_data()

        finally:
            pending_bets.clear()
            game_in_progress = False
            last_game_time = int(time.time())
        return

    # ==================== СТАВКИ НА РУЛЕТКУ ====================
    if len(parts) >= 2:
        if game_in_progress:
            await message.reply("⏳ Идёт игра")
            return
        try:
            amt = int(parts[0])
        except:
            return
        
        if amt < 100:
            await message.reply("❌ Минимальная ставка 100 GRAM")
            return

        bets = " ".join(parts[1:]).split()
        if len(bets) > MAX_BETS_PER_MESSAGE:
            await message.reply(f"❌ Максимум {MAX_BETS_PER_MESSAGE} ставок")
            return

        total = amt * len(bets)
        bal = user_balances.get(uid, 0)
        if total > bal:
            await message.reply(f"❌ Нужно {format_amount(total)} GRAM")
            return

        # Обновляем задание "сделать ставку" ТОЛЬКО если ставка >= 100
        if amt >= 100:
            reward = update_quest_progress(uid, "make_bet")
            if reward > 0:
                await send_quest_complete_notification(uid, "make_bet", reward, message)

        user_balances[uid] = bal - total
        save_data()

        acc = []
        for b in bets:
            if not b: continue
            pending_bets.append({"user_id": uid, "user_name": name, "amount": amt, "raw_bet": b})
            acc.append(f"Ставка принята: {name} {format_amount(amt)} GRAM на {b}")

        for i in range(0, len(acc), 20):
            await message.reply("<code>" + "\n".join(acc[i:i+20]) + "</code>", parse_mode="HTML")

# ==================== КОЛБЭКИ БЛЭКДЖЕКА ====================
@dp.callback_query_handler(lambda c: c.data.startswith("bj_"))
async def blackjack_callback(call: CallbackQuery):
    await call.answer()
    uid = call.from_user.id
    
    if uid not in blackjack_games:
        await call.message.edit_text("❌ Игра не найдена")
        return
    
    g = blackjack_games[uid]
    if not g["active"]:
        return
    
    action = call.data[3:]
    
    if action == "hit":
        g["player_hand"].append(g["deck"].pop())
        player_val = hand_value(g["player_hand"])
        
        if player_val > 21:
            g["active"] = False
            del blackjack_games[uid]
            
            if uid not in user_stats:
                user_stats[uid] = {"played": 0, "won": 0, "total_bet": 0, "total_win": 0}
            user_stats[uid]["played"] += 1
            user_stats[uid]["total_bet"] += g["bet"]
            user_levels[uid] = user_levels.get(uid, 0) + 1
            
            # Обновляем задание "сыграть 3 игры"
            reward_play = update_quest_progress(uid, "play_3_games")
            if reward_play > 0:
                await send_quest_complete_notification(uid, "play_3_games", reward_play, call.message)
            
            # Сбрасываем streak
            daily_quests["win_3_streak"]["current_streak"][uid] = 0
            save_data()
            
            await call.message.edit_text(
                f"<code>🃏 ПЕРЕБОР! ({player_val})\n\n"
                f"Ваши карты: {format_cards(g['player_hand'])}\n"
                f"Карты дилера: {format_cards(g['dealer_hand'])} ({hand_value(g['dealer_hand'])})\n\n"
                f"❌ Вы проиграли {format_amount(g['bet'])} GRAM</code>",
                parse_mode="HTML"
            )
            return
        
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton("🃏 Взять", callback_data="bj_hit"),
            InlineKeyboardButton("✋ Хватит", callback_data="bj_stand")
        )
        
        dealer_up = g["dealer_hand"][0]
        await call.message.edit_text(
            f"<code>🃏 БЛЭКДЖЕК\n"
            f"💰 Ставка: {format_amount(g['bet'])} GRAM\n\n"
            f"Ваши карты: {format_cards(g['player_hand'])} ({player_val})\n"
            f"Карта дилера: {format_cards([dealer_up])}</code>",
            parse_mode="HTML",
            reply_markup=kb
        )
    
    elif action == "stand":
        g["active"] = False
        
        while hand_value(g["dealer_hand"]) < 17:
            g["dealer_hand"].append(g["deck"].pop())
        
        player_val = hand_value(g["player_hand"])
        dealer_val = hand_value(g["dealer_hand"])
        
        win = 0
        result_text = ""
        won = False
        
        if dealer_val > 21:
            win = g["bet"] * 2
            result_text = "🎉 ДИЛЕР ПЕРЕБРАЛ! ВЫ ВЫИГРАЛИ!"
            won = True
        elif player_val > dealer_val:
            win = g["bet"] * 2
            result_text = "🎉 ВЫ ВЫИГРАЛИ!"
            won = True
        elif player_val == dealer_val:
            win = g["bet"]
            result_text = "🤝 НИЧЬЯ! СТАВКА ВОЗВРАЩЕНА"
            won = False
        else:
            result_text = "😞 ДИЛЕР ВЫИГРАЛ"
            won = False
        
        if win > 0:
            user_balances[uid] = user_balances.get(uid, 0) + win
        
        if uid not in user_stats:
            user_stats[uid] = {"played": 0, "won": 0, "total_bet": 0, "total_win": 0}
        user_stats[uid]["played"] += 1
        if won:
            user_stats[uid]["won"] += 1
            # Обновляем streak побед
            if uid not in daily_quests["win_3_streak"]["current_streak"]:
                daily_quests["win_3_streak"]["current_streak"][uid] = 0
            daily_quests["win_3_streak"]["current_streak"][uid] += 1
            reward_streak = update_quest_progress(uid, "win_3_streak", daily_quests["win_3_streak"]["current_streak"][uid])
            if reward_streak > 0:
                await send_quest_complete_notification(uid, "win_3_streak", reward_streak, call.message)
        else:
            daily_quests["win_3_streak"]["current_streak"][uid] = 0
            
        # Обновляем задание "сыграть 3 игры"
        reward_play = update_quest_progress(uid, "play_3_games")
        if reward_play > 0:
            await send_quest_complete_notification(uid, "play_3_games", reward_play, call.message)
            
        user_stats[uid]["total_bet"] += g["bet"]
        user_stats[uid]["total_win"] += win
        user_levels[uid] = user_levels.get(uid, 0) + 1
        
        del blackjack_games[uid]
        save_data()
        
        await call.message.edit_text(
            f"<code>🃏 ИГРА ОКОНЧЕНА\n\n"
            f"Ваши карты: {format_cards(g['player_hand'])} ({player_val})\n"
            f"Карты дилера: {format_cards(g['dealer_hand'])} ({dealer_val})\n\n"
            f"{result_text}\n"
            f"💰 {'+' if win > 0 else ''}{format_amount(win) if win > 0 else '0'} GRAM</code>",
            parse_mode="HTML"
        )
    
    elif action == "surrender":
        g["active"] = False
        
        refund = g["bet"] // 2
        user_balances[uid] = user_balances.get(uid, 0) + refund
        
        if uid not in user_stats:
            user_stats[uid] = {"played": 0, "won": 0, "total_bet": 0, "total_win": 0}
        user_stats[uid]["played"] += 1
        user_stats[uid]["total_bet"] += g["bet"]
        user_levels[uid] = user_levels.get(uid, 0) + 1
        
        # Обновляем задание "сыграть 3 игры"
        reward_play = update_quest_progress(uid, "play_3_games")
        if reward_play > 0:
            await send_quest_complete_notification(uid, "play_3_games", reward_play, call.message)
        
        del blackjack_games[uid]
        save_data()
        
        await call.message.edit_text(
            f"<code>🏳️ ВЫ СДАЛИСЬ\n\n"
            f"Ваши карты: {format_cards(g['player_hand'])} ({hand_value(g['player_hand'])})\n"
            f"Карты дилера: {format_cards(g['dealer_hand'])} ({hand_value(g['dealer_hand'])})\n\n"
            f"💰 Возвращено {format_amount(refund)} GRAM</code>",
            parse_mode="HTML"
        )

# ==================== КОЛБЭКИ МИН ====================
@dp.callback_query_handler(lambda c: c.data.startswith("m_"))
async def mine_click(call: CallbackQuery):
    await call.answer()
    uid = call.from_user.id

    if uid not in mines_games:
        await call.message.edit_text("❌ Игра не найдена")
        return

    g = mines_games[uid]
    if not g["active"]:
        return

    parts = call.data.split("_")
    row, col = int(parts[1]), int(parts[2])

    if (row, col) in g["revealed"]:
        return

    g["revealed"].append((row, col))
    cell = g["field"][row][col]

    if cell == "💣":
        g["active"] = False
        del mines_games[uid]
        
        # Обновляем задание "сыграть 3 игры" (проигрыш тоже считается игрой)
        reward_play = update_quest_progress(uid, "play_3_games")
        if reward_play > 0:
            await send_quest_complete_notification(uid, "play_3_games", reward_play, call.message)
        
        # Сбрасываем streak побед
        daily_quests["win_3_streak"]["current_streak"][uid] = 0
        save_data()
        
        await call.message.edit_text(
            f"💥 {call.from_user.full_name}, мина!\n❌ -{format_amount(g['bet'])} GRAM\n\n"
            f"{format_mines_field(g['field'], g['revealed'])}"
        )
        return

    g["multiplier"] += 0.14
    pot = int(g["bet"] * g["multiplier"])

    kb = get_mines_keyboard(g["field"], g["revealed"])

    await call.message.edit_text(
        f"💎 {call.from_user.full_name}, вы начали игру минное поле!\n"
        f"📌 Ставка: {format_amount(g['bet'])} GRAM\n"
        f"💲 Выигрыш: x{g['multiplier']:.2f} | {format_amount(pot)} GRAM\n\n"
        f"{format_mines_field(g['field'], g['revealed'])}",
        reply_markup=kb
    )

@dp.callback_query_handler(lambda c: c.data == "cash")
async def mine_cash(call: CallbackQuery):
    await call.answer()
    uid = call.from_user.id

    if uid not in mines_games:
        await call.message.edit_text("❌ Игра не найдена")
        return

    g = mines_games[uid]
    if not g["active"]:
        return

    g["active"] = False
    win = int(g["bet"] * g["multiplier"])
    user_balances[uid] = user_balances.get(uid, 0) + win

    if uid not in user_stats:
        user_stats[uid] = {"played": 0, "won": 0, "total_bet": 0, "total_win": 0}
    user_stats[uid]["played"] += 1
    user_stats[uid]["won"] += 1
    user_stats[uid]["total_bet"] += g["bet"]
    user_stats[uid]["total_win"] += win
    user_levels[uid] = user_levels.get(uid, 0) + 1
    
    # Обновляем задание "сыграть 3 игры"
    reward_play = update_quest_progress(uid, "play_3_games")
    if reward_play > 0:
        await send_quest_complete_notification(uid, "play_3_games", reward_play, call.message)
    
    # Обновляем streak побед
    if uid not in daily_quests["win_3_streak"]["current_streak"]:
        daily_quests["win_3_streak"]["current_streak"][uid] = 0
    daily_quests["win_3_streak"]["current_streak"][uid] += 1
    reward_streak = update_quest_progress(uid, "win_3_streak", daily_quests["win_3_streak"]["current_streak"][uid])
    if reward_streak > 0:
        await send_quest_complete_notification(uid, "win_3_streak", reward_streak, call.message)

    del mines_games[uid]
    save_data()

    await call.message.edit_text(
        f"💰 {call.from_user.full_name} забрал выигрыш!\n"
        f"✅ +{format_amount(win)} GRAM\n"
        f"💲 Итоговый множитель: x{g['multiplier']:.2f}\n\n"
        f"{format_mines_field(g['field'], g['revealed'])}"
    )

if __name__ == "__main__":
    load_data()
    init_quests()
    executor.start_polling(dp, skip_updates=True)
