import os
import asyncio
import logging
import sys
import random
import time
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message

API_TOKEN = os.environ.get("BOT_TOKEN", "8723084939:AAEO8Jd5oLYsAN-JMht4CBh2MUy_XWxH94M")

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ========== ДАННЫЕ В ПАМЯТИ ==========
user_balances = {}
game_history = []
user_stats = {}
user_levels = {}
daily_streak = {}

ADMIN_ID = 6003768110
GAME_COOLDOWN = 15
DAILY_BONUS_BASE = 500
DAILY_BONUS_STREAK_MULTIPLIER = 200

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

def get_level(exp: int) -> int:
    if exp < 10: return 1
    elif exp < 30: return 2
    elif exp < 60: return 3
    elif exp < 100: return 4
    else: return 5

def format_balance(user_name: str, balance: int) -> str:
    return f"{user_name}\nБаланс: {balance:,} GRAM".replace(",", " ")

def format_log():
    if not game_history:
        return "📋 История пуста."
    row1 = " ".join(game_history[-10:][:5])
    row2 = " ".join(game_history[-10:][5:]) if len(game_history[-10:]) > 5 else ""
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
    user_balances[ADMIN_ID] = user_balances.get(ADMIN_ID, 0) + amount
    await message.reply(f"✅ +{amount} GRAM\n💰 Баланс: {user_balances[ADMIN_ID]} GRAM")

# ========== ГЛАВНЫЙ ОБРАБОТЧИК ==========
@dp.message()
async def handle_message(message: Message):
    global pending_bets, game_in_progress, last_game_time, game_history

    user_id = message.from_user.id
    user_name = message.from_user.full_name
    text = message.text.strip()
    parts = text.split()

    # ========== ПРОФИЛЬ ==========
    if text.lower() in ["профиль", "profile", "/profile"]:
        balance = user_balances.get(user_id, 0)
        stats = user_stats.get(user_id, {"played": 0, "won": 0, "total_bet": 0, "total_win": 0})
        exp = user_levels.get(user_id, 0)
        level = get_level(exp)
        winrate = (stats["won"] / stats["played"] * 100) if stats["played"] > 0 else 0
        profit = stats["total_win"] - stats["total_bet"]
        await message.reply(
            f"👤 {user_name}\n"
            f"🆔 {user_id}\n"
            f"📊 Уровень: {level} (опыт: {exp})\n"
            f"💰 Баланс: {balance:,} GRAM\n\n"
            f"🎲 Игр сыграно: {stats['played']}\n"
            f"🏆 Побед: {stats['won']}\n"
            f"📈 Винрейт: {winrate:.1f}%\n"
            f"💸 Поставлено: {stats['total_bet']:,} GRAM\n"
            f"💵 Выиграно: {stats['total_win']:,} GRAM\n"
            f"📊 Профит: {profit:+,} GRAM".replace(",", " ")
        )
        return

    # ========== БОНУС ==========
    if text.lower() in ["бонус", "daily"]:
        now = int(time.time())
        ds = daily_streak.get(user_id, {"last_claim": 0, "streak": 0})
        last_claim = ds["last_claim"]
        streak = ds["streak"]

        if now - last_claim >= 24 * 60 * 60:
            if now - last_claim >= 48 * 60 * 60:
                streak = 0
            streak += 1
            bonus = DAILY_BONUS_BASE + (streak - 1) * DAILY_BONUS_STREAK_MULTIPLIER
            user_balances[user_id] = user_balances.get(user_id, 0) + bonus
            daily_streak[user_id] = {"last_claim": now, "streak": streak}
            await message.reply(
                f"🎁 Ежедневный бонус!\n\n"
                f"➕ {bonus} GRAM\n"
                f"🔥 Стрик: {streak} дн.\n"
                f"💰 Баланс: {user_balances[user_id]:,} GRAM".replace(",", " ")
            )
        else:
            remaining = 24 * 60 * 60 - (now - last_claim)
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            await message.reply(f"⏰ Следующий бонус через {hours} ч {minutes} мин")
        return

    # ========== БАЛАНС ==========
    if text.lower() in ["б", "баланс", "грамм"]:
        balance = user_balances.get(user_id, 0)
        await message.reply(format_balance(user_name, balance))
        return

    # ========== ЛОГ ==========
    if text.lower() in ["лог", "история"]:
        await message.reply(format_log())
        return

    # ========== ТОП ==========
    if text.lower() in ["топ", "/топ"]:
        if not user_balances:
            await message.reply("📊 Пока никто не играл.")
            return
        sorted_users = sorted(user_balances.items(), key=lambda x: x[1], reverse=True)
        top_text = "🏆 ТОП-10 БОГАЧЕЙ:\n\n"
        for i, (uid, bal) in enumerate(sorted_users[:10], 1):
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
                await message.reply("❌ Сумма числом.")
                return
            if amount <= 0:
                await message.reply("❌ Сумма > 0.")
                return
            sender_balance = user_balances.get(user_id, 0)
            if amount > sender_balance:
                await message.reply(f"❌ Недостаточно GRAM.")
                return
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
            user_balances[user_id] = sender_balance - amount
            user_balances[target_id] = user_balances.get(target_id, 0) + amount
            await message.reply(f"✅ {amount} GRAM → {target_name}")
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
            sender_balance = user_balances.get(user_id, 0)
            if amount > sender_balance:
                await message.reply(f"❌ Недостаточно GRAM.")
                return
            user_balances[user_id] = sender_balance - amount
            user_balances[target_id] = user_balances.get(target_id, 0) + amount
            await message.reply(f"✅ {amount} GRAM → {target_name}")
            return

    # ========== ПОМОЩЬ ==========
    if text.lower() in ["помощь", "команды", "help", "старт", "/start"]:
        await message.reply(
            f"🎰 GOLDEN GRAM ROULETTE\n\n"
            f"Ставки: 100 к, 200 ч, 500 чёт, 1000 23-34\n"
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

        # ========== ОБРАБОТКА СТАВОК (КАЖДАЯ СВОЙ РАНДОМ) ==========
        results = []
        for bet in pending_bets:
            uid = bet["user_id"]
            uname = bet["user_name"]
            amount = bet["amount"]
            raw_bet = bet["raw_bet"]

            # Для каждой ставки крутим свой рандом
            win_num, win_emoji, win_color, win_parity, win_dozen, win_column = spin_roulette()
            norm_bet = normalize_bet_type(raw_bet)
            win = check_win(norm_bet, win_num, win_color, win_parity, win_dozen, win_column)
            multiplier = get_multiplier(norm_bet)

            # Обновляем статистику
            if uid not in user_stats:
                user_stats[uid] = {"played": 0, "won": 0, "total_bet": 0, "total_win": 0}
            user_stats[uid]["played"] += 1
            user_stats[uid]["total_bet"] += amount
            user_levels[uid] = user_levels.get(uid, 0) + 1

            if win:
                winnings = amount * multiplier
                user_balances[uid] = user_balances.get(uid, 0) + winnings
                user_stats[uid]["won"] += 1
                user_stats[uid]["total_win"] += winnings
                results.append(f"✅ {uname} +{winnings} GRAM ({amount} на {raw_bet} → {win_emoji} {win_num})")
                game_history.append(f"{win_emoji} {win_num}")
            else:
                results.append(f"❌ {uname} -{amount} GRAM ({amount} на {raw_bet} → {win_emoji} {win_num})")
                game_history.append(f"{win_emoji} {win_num}")

        # Ограничиваем историю 10 элементами
        if len(game_history) > 10:
            game_history = game_history[-10:]

        result_text = "🎯 РЕЗУЛЬТАТЫ:\n\n" + "\n".join(results)
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
        balance = user_balances.get(user_id, 0)

        if total_needed > balance:
            await message.reply(f"❌ Недостаточно GRAM (нужно {total_needed})")
            return

        user_balances[user_id] = balance - total_needed

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
