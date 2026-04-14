import os
import asyncio
import logging
import sys
import random
import sqlite3
import time
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message

API_TOKEN = os.environ.get("BOT_TOKEN", "8723084939:AAEO8Jd5oLYsAN-JMht4CBh2MUy_XWxH94M")

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ========== БАЗА ДАННЫХ ==========
DB_FILE = "database.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS balances (user_id INTEGER PRIMARY KEY, balance INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, entry TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS bonus (user_id INTEGER PRIMARY KEY, last_time INTEGER, streak INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS stats 
                 (user_id INTEGER PRIMARY KEY, games_played INTEGER DEFAULT 0, games_won INTEGER DEFAULT 0, 
                  total_bet INTEGER DEFAULT 0, total_win INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS levels 
                 (user_id INTEGER PRIMARY KEY, level INTEGER DEFAULT 1, exp INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS daily_bonus 
                 (user_id INTEGER PRIMARY KEY, last_claim INTEGER, current_streak INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

init_db()

# ========== ФУНКЦИИ БД ==========
def get_balance(user_id: int) -> int:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT balance FROM balances WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def set_balance(user_id: int, balance: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO balances (user_id, balance) VALUES (?, ?)", (user_id, balance))
    conn.commit()
    conn.close()

def add_balance(user_id: int, amount: int):
    set_balance(user_id, get_balance(user_id) + amount)

def get_all_balances():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id, balance FROM balances ORDER BY balance DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def get_history():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT entry FROM history ORDER BY id DESC LIMIT 10")
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in reversed(rows)]

def add_history(entry: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO history (entry) VALUES (?)", (entry,))
    conn.commit()
    conn.close()

def get_bonus(user_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT last_time, streak FROM bonus WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row if row else (0, 0)

def set_bonus(user_id: int, last_time: int, streak: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO bonus (user_id, last_time, streak) VALUES (?, ?, ?)", (user_id, last_time, streak))
    conn.commit()
    conn.close()

def get_stats(user_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT games_played, games_won, total_bet, total_win FROM stats WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row if row else (0, 0, 0, 0)

def update_stats(user_id: int, won: bool, bet_amount: int, win_amount: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT games_played, games_won, total_bet, total_win FROM stats WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if row:
        played, won_cnt, total_bet, total_win = row
    else:
        played, won_cnt, total_bet, total_win = 0, 0, 0, 0
    played += 1
    if won:
        won_cnt += 1
    total_bet += bet_amount
    total_win += win_amount
    c.execute("INSERT OR REPLACE INTO stats VALUES (?, ?, ?, ?, ?)", (user_id, played, won_cnt, total_bet, total_win))
    # Опыт за игру
    c.execute("SELECT level, exp FROM levels WHERE user_id = ?", (user_id,))
    lvl_row = c.fetchone()
    if lvl_row:
        level, exp = lvl_row
    else:
        level, exp = 1, 0
    exp += 1
    # Повышение уровня каждые 10 опыта
    if exp >= level * 10:
        level += 1
        exp = 0
    c.execute("INSERT OR REPLACE INTO levels VALUES (?, ?, ?)", (user_id, level, exp))
    conn.commit()
    conn.close()

def get_level(user_id: int) -> int:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT level FROM levels WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 1

def get_daily_streak(user_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT last_claim, current_streak FROM daily_bonus WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row if row else (0, 0)

def set_daily_streak(user_id: int, last_claim: int, streak: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO daily_bonus VALUES (?, ?, ?)", (user_id, last_claim, streak))
    conn.commit()
    conn.close()

# ========== КОНСТАНТЫ ==========
ADMIN_ID = 6003768110
BONUS_COOLDOWN = 4 * 60 * 60  # 4 часа
GAME_COOLDOWN = 15
DAILY_BONUS_BASE = 500
DAILY_BONUS_STREAK_MULTIPLIER = 200

# Уровни и лимиты переводов
LEVEL_LIMITS = {1: 50000, 2: 100000, 3: 200000, 4: 500000, 5: 1000000}

pending_bets = []
game_in_progress = False
last_game_time = 0

# ========== РУЛЕТКА ==========
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

    if number == 0:
        parity = "ZERO"
    elif number % 2 == 0:
        parity = "ЧЁТНОЕ"
    else:
        parity = "НЕЧЁТНОЕ"

    if 1 <= number <= 12:
        dozen = 1
    elif 13 <= number <= 24:
        dozen = 2
    elif 25 <= number <= 36:
        dozen = 3
    else:
        dozen = 0

    if number == 0:
        column = 0
    elif number % 3 == 1:
        column = 1
    elif number % 3 == 2:
        column = 2
    else:
        column = 3

    return number, color_emoji, color_name, parity, dozen, column

def normalize_bet_type(bet: str) -> str:
    bet = bet.lower()
    if bet in ["к", "красное", "красный", "red"]: return "красное"
    if bet in ["ч", "чёрное", "черное", "чёрный", "черный", "black"]: return "чёрное"
    if bet in ["чёт", "чет", "чётное", "четное", "even"]: return "чётное"
    if bet in ["неч", "нечётное", "нечетное", "odd"]: return "нечётное"
    if bet in ["0", "зеро", "zero"]: return "0"
    if bet in ["1я", "1-я", "первая", "первый"]: return "1-я"
    if bet in ["2я", "2-я", "вторая", "второй"]: return "2-я"
    if bet in ["3я", "3-я", "третья", "третий"]: return "3-я"
    return bet

def check_win(bet_type: str, number: int, color_name: str, parity: str, dozen: int, column: int) -> bool:
    bet = normalize_bet_type(bet_type)
    if bet == "красное" and color_name == "КРАСНОЕ": return True
    if bet == "чёрное" and color_name == "ЧЁРНОЕ": return True
    if bet == "чётное" and parity == "ЧЁТНОЕ": return True
    if bet == "нечётное" and parity == "НЕЧЁТНОЕ": return True
    if bet == "0" and number == 0: return True
    if bet == "1-12" and dozen == 1: return True
    if bet == "13-24" and dozen == 2: return True
    if bet == "25-36" and dozen == 3: return True
    if bet == "1-я" and column == 1: return True
    if bet == "2-я" and column == 2: return True
    if bet == "3-я" and column == 3: return True
    if bet.isdigit():
        if int(bet) == number: return True
    if "-" in bet:
        parts = bet.split("-")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            start, end = int(parts[0]), int(parts[1])
            if start <= number <= end:
                return True
    return False

def get_multiplier(bet_type: str) -> int:
    bet = normalize_bet_type(bet_type)
    if bet.isdigit() or bet == "0":
        return 36
    if "-" in bet:
        parts = bet.split("-")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            start, end = int(parts[0]), int(parts[1])
            count = end - start + 1
            if count == 2: return 18
            elif count == 3: return 12
            elif count == 4: return 9
            elif count == 6: return 6
            elif count == 12: return 3
            else: return 36 // count if count > 0 else 2
        return 2
    if bet in ["1-12", "13-24", "25-36", "1-я", "2-я", "3-я"]:
        return 3
    return 2

def format_balance(user_name: str, balance: int) -> str:
    return f"{user_name}\nБаланс: {balance:,} GRAM".replace(",", " ")

def format_log():
    history = get_history()
    if not history:
        return "📋 История пуста."
    row1 = " ".join(history[:5])
    row2 = " ".join(history[5:]) if len(history) > 5 else ""
    if row2:
        return f"{row1}\n{row2}"
    else:
        return row1

# ========== АДМИН ==========
@dp.message(Command("add_grams"))
async def add_grams_slash(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.reply("❌ Нет прав.")
        return
    parts = message.text.split()
    if len(parts) != 2:
        await message.reply("❌ /add_grams 5000")
        return
    try:
        amount = int(parts[1])
    except:
        await message.reply("❌ Сумма числом.")
        return
    add_balance(ADMIN_ID, amount)
    await message.reply(f"✅ +{amount} GRAM\n💰 Баланс: {get_balance(ADMIN_ID)} GRAM")

# ========== ГЛАВНЫЙ ОБРАБОТЧИК ==========
@dp.message()
async def handle_message(message: Message):
    global pending_bets, game_in_progress, last_game_time

    user_id = message.from_user.id
    user_name = message.from_user.full_name
    text = message.text.strip()
    parts = text.split()

    # ========== ПРОФИЛЬ ==========
    if text.lower() in ["профиль", "profile", "/profile"]:
        balance = get_balance(user_id)
        level = get_level(user_id)
        played, won, total_bet, total_win = get_stats(user_id)
        winrate = (won / played * 100) if played > 0 else 0
        profit = total_win - total_bet
        limit = LEVEL_LIMITS.get(level, 50000)
        await message.reply(
            f"👤 {user_name}\n"
            f"🆔 {user_id}\n"
            f"📊 Уровень: {level}\n"
            f"💰 Баланс: {balance:,} GRAM\n\n".replace(",", " ") +
            f"🎲 Игр сыграно: {played}\n"
            f"🏆 Побед: {won}\n"
            f"📈 Винрейт: {winrate:.1f}%\n"
            f"💸 Всего поставлено: {total_bet:,} GRAM\n"
            f"💵 Всего выиграно: {total_win:,} GRAM\n"
            f"📊 Профит: {profit:+,} GRAM\n\n".replace(",", " ") +
            f"📤 Лимит передачи: {limit:,} GRAM/сутки".replace(",", " ")
        )
        return

    # ========== БОНУС (ЕЖЕДНЕВНЫЙ СТРИК) ==========
    if text.lower() in ["бонус", "daily"]:
        now = int(time.time())
        last_claim, streak = get_daily_streak(user_id)
        # Проверка 24 часа
        if now - last_claim >= 24 * 60 * 60:
            # Если прошло больше 48 часов - стрик сброшен
            if now - last_claim >= 48 * 60 * 60:
                streak = 0
            streak += 1
            bonus_amount = DAILY_BONUS_BASE + (streak - 1) * DAILY_BONUS_STREAK_MULTIPLIER
            add_balance(user_id, bonus_amount)
            set_daily_streak(user_id, now, streak)
            await message.reply(
                f"🎁 Ежедневный бонус получен!\n\n"
                f"➕ {bonus_amount} GRAM\n"
                f"🔥 Стрик: {streak} дн.\n"
                f"💰 Баланс: {get_balance(user_id):,} GRAM".replace(",", " ")
            )
        else:
            remaining = 24 * 60 * 60 - (now - last_claim)
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            await message.reply(f"⏰ Следующий бонус через {hours} ч {minutes} мин")
        return

    # ========== БАЛАНС ==========
    if text.lower() in ["б", "баланс", "грамм"]:
        balance = get_balance(user_id)
        await message.reply(format_balance(user_name, balance))
        return

    # ========== ЛОГ ==========
    if text.lower() in ["лог", "история"]:
        await message.reply(format_log())
        return

    # ========== ТОП ==========
    if text.lower() in ["топ", "/топ"]:
        rows = get_all_balances()
        if not rows:
            await message.reply("📊 Пока никто не играл.")
            return
        top_text = "🏆 ТОП-10 БОГАЧЕЙ:\n\n"
        for i, (uid, bal) in enumerate(rows[:10], 1):
            try:
                user_info = await bot.get_chat(uid)
                name = user_info.full_name
            except:
                name = f"ID: {uid}"
            top_text += f"{i}. {name} — {bal:,} GRAM\n".replace(",", " ")
        await message.reply(top_text)
        return

    # ========== ДАТЬ ==========
    if text.lower().startswith("дать ") or text.lower().startswith("/дать "):
        cmd_parts = text.split()
        if len(cmd_parts) == 3 and cmd_parts[1].startswith("@"):
            target_username = cmd_parts[1][1:]
            try:
                amount = int(cmd_parts[2])
            except:
                await message.reply("❌ Сумма должна быть числом.")
                return
            if amount <= 0:
                await message.reply("❌ Сумма > 0.")
                return
            sender_balance = get_balance(user_id)
            if amount > sender_balance:
                await message.reply(f"❌ Недостаточно GRAM. Ваш баланс: {sender_balance:,}".replace(",", " "))
                return
            # Проверка лимита
            level = get_level(user_id)
            limit = LEVEL_LIMITS.get(level, 50000)
            # Тут нужна проверка суточного лимита (можно добавить позже)
            try:
                target_user = await bot.get_chat(f"@{target_username}")
                target_id = target_user.id
                target_name = target_user.full_name
            except:
                await message.reply(f"❌ @{target_username} не найден.")
                return
            if target_id == user_id:
                await message.reply("❌ Нельзя самому себе.")
                return
            set_balance(user_id, sender_balance - amount)
            add_balance(target_id, amount)
            await message.reply(f"✅ {amount} GRAM → {target_name}\n💰 Ваш баланс: {get_balance(user_id):,}".replace(",", " "))
            return
        elif len(cmd_parts) == 2:
            try:
                amount = int(cmd_parts[1])
            except:
                await message.reply("❌ Сумма числом.")
                return
            if not message.reply_to_message:
                await message.reply("❌ Ответь на сообщение или `дать @user 1000`")
                return
            target_id = message.reply_to_message.from_user.id
            target_name = message.reply_to_message.from_user.full_name
            if target_id == user_id:
                await message.reply("❌ Нельзя самому себе.")
                return
            sender_balance = get_balance(user_id)
            if amount > sender_balance:
                await message.reply(f"❌ Недостаточно GRAM.")
                return
            set_balance(user_id, sender_balance - amount)
            add_balance(target_id, amount)
            await message.reply(f"✅ {amount} GRAM → {target_name}")
            return

    # ========== ПОМОЩЬ ==========
    if text.lower() in ["помощь", "команды", "help", "старт", "/start"]:
        await message.reply(
            f"🎰 GOLDEN GRAM ROULETTE\n\n"
            f"Ставки: 100 к, 200 ч, 500 чёт, 1000 23-34, 100 1-12\n"
            f"Команды: б, лог, топ, бонус, го, дать, профиль"
        )
        return

    # ========== ГО ==========
    if text.lower() == "го":
        now = int(time.time())
        if game_in_progress:
            await message.reply("⏳ Дождитесь окончания!")
            return
        if now - last_game_time < GAME_COOLDOWN:
            await message.reply(f"⏰ Подожди {GAME_COOLDOWN - (now - last_game_time)} сек.")
            return
        if not pending_bets:
            await message.reply("❌ Нет ставок.")
            return

        game_in_progress = True
        wait_msg = await message.answer("⏳ Подождите 10 секунд...")
        await asyncio.sleep(10)
        await bot.delete_message(chat_id=message.chat.id, message_id=wait_msg.message_id)

        win_num, win_emoji, win_color, win_parity, win_dozen, win_column = spin_roulette()
        add_history(f"{win_emoji} {win_num}")

        results = []
        for bet in pending_bets:
            uid = bet["user_id"]
            uname = bet["user_name"]
            amount = bet["amount"]
            raw_bet = bet["raw_bet"]
            norm_bet = normalize_bet_type(raw_bet)

            win = check_win(norm_bet, win_num, win_color, win_parity, win_dozen, win_column)
            multiplier = get_multiplier(norm_bet)

            if win:
                winnings = amount * multiplier
                add_balance(uid, winnings)
                results.append(f"✅ {uname} +{winnings} GRAM")
                update_stats(uid, True, amount, winnings)
            else:
                results.append(f"❌ {uname} -{amount} GRAM")
                update_stats(uid, False, amount, 0)

        result_text = f"🎯 ВЫПАЛО: {win_emoji} {win_num}\n\n" + "\n".join(results)
        await message.answer(result_text)

        pending_bets.clear()
        game_in_progress = False
        last_game_time = int(time.time())
        return

    # ========== СТАВКА ==========
    if len(parts) >= 2:
        if game_in_progress:
            await message.reply("⏳ Дождитесь окончания!")
            return
        now = int(time.time())
        if now - last_game_time < GAME_COOLDOWN:
            await message.reply(f"⏰ Подожди {GAME_COOLDOWN - (now - last_game_time)} сек.")
            return

        try:
            amount = int(parts[0])
        except:
            return

        if amount <= 0:
            await message.reply("❌ Ставка > 0")
            return

        bet_items = " ".join(parts[1:]).split()
        total_needed = amount * len(bet_items)
        balance = get_balance(user_id)

        if total_needed > balance:
            await message.reply(f"❌ Недостаточно GRAM (нужно {total_needed})")
            return

        set_balance(user_id, balance - total_needed)

        accepted = []
        for bet in bet_items:
            pending_bets.append({
                "user_id": user_id,
                "user_name": user_name,
                "amount": amount,
                "raw_bet": bet
            })
            accepted.append(f"✅ {amount} GRAM на {bet}")

        await message.reply("\n".join(accepted))

# ========== ЗАПУСК ==========
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
