import os
import asyncio
import logging
import sys
import random
import json
import time
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message

API_TOKEN = os.environ.get("BOT_TOKEN", "8723084939:AAEO8Jd5oLYsAN-JMht4CBh2MUy_XWxH94M")

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ========== ФАЙЛЫ ==========
BALANCES_FILE = "balances.json"
HISTORY_FILE = "history.json"
BONUS_FILE = "bonus.json"

def load_balances():
    try:
        with open(BALANCES_FILE, "r", encoding="utf-8") as f:
            return {int(k): v for k, v in json.load(f).items()}
    except:
        return {}

def save_balances(data):
    with open(BALANCES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_history():
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_history(data):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_bonus():
    try:
        with open(BONUS_FILE, "r", encoding="utf-8") as f:
            return {int(k): v for k, v in json.load(f).items()}
    except:
        return {}

def save_bonus(data):
    with open(BONUS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Глобальные переменные
user_balances = load_balances()
game_history = load_history()
last_bonus = load_bonus()

ADMIN_ID = 6003768110
BONUS_AMOUNT = 10000
BONUS_COOLDOWN = 24 * 60 * 60
GAME_COOLDOWN = 15

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
    return f"{user_name}\nБаланс: {balance} GRAM"

def format_log():
    if not game_history:
        return "📋 История пуста."
    last_10 = game_history[-10:]
    row1 = " ".join(last_10[:5])
    row2 = " ".join(last_10[5:]) if len(last_10) > 5 else ""
    if row2:
        return f"{row1}\n{row2}"
    else:
        return row1

# ========== АДМИН ==========
@dp.message(Command("add_grams"))
async def add_grams_slash(message: Message):
    global user_balances
    if message.from_user.id != ADMIN_ID:
        await message.reply("❌ У вас нет прав для этой команды.")
        return
    parts = message.text.split()
    if len(parts) != 2:
        await message.reply("❌ Укажите сумму. Пример: /add_grams 5000")
        return
    try:
        amount = int(parts[1])
    except:
        await message.reply("❌ Сумма должна быть числом.")
        return
    user_balances[ADMIN_ID] = user_balances.get(ADMIN_ID, 0) + amount
    save_balances(user_balances)
    await message.reply(f"✅ Баланс пополнен на {amount} GRAM.\n💰 Текущий баланс: {user_balances[ADMIN_ID]} GRAM")

# ========== ГЛАВНЫЙ ОБРАБОТЧИК ==========
@dp.message()
async def handle_message(message: Message):
    global user_balances, game_history, last_bonus
    global pending_bets, game_in_progress, last_game_time

    user_id = message.from_user.id
    user_name = message.from_user.full_name
    text = message.text.strip()
    parts = text.split()

    # ========== БОНУС ==========
    if text.lower() == "бонус":
        now = int(time.time())
        last = last_bonus.get(user_id, 0)
        if now - last >= BONUS_COOLDOWN:
            user_balances[user_id] = user_balances.get(user_id, 0) + BONUS_AMOUNT
            last_bonus[user_id] = now
            save_balances(user_balances)
            save_bonus(last_bonus)
            await message.reply(f"🎁 +{BONUS_AMOUNT} GRAM\n💰 Баланс: {user_balances[user_id]} GRAM")
        else:
            remaining = BONUS_COOLDOWN - (now - last)
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            await message.reply(f"⏰ Бонус через {hours} ч. {minutes} мин.")
        return

    # ========== БАЛАНС ==========
    if text.lower() in ["б", "баланс"]:
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
            top_text += f"{i}. {name} — {bal} GRAM\n"
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
                await message.reply("❌ Сумма должна быть больше нуля.")
                return
            sender_balance = user_balances.get(user_id, 0)
            if amount > sender_balance:
                await message.reply(f"❌ Недостаточно GRAM. Ваш баланс: {sender_balance}")
                return
            try:
                target_user = await bot.get_chat(f"@{target_username}")
                target_id = target_user.id
                target_name = target_user.full_name
            except:
                await message.reply(f"❌ Пользователь @{target_username} не найден.")
                return
            if target_id == user_id:
                await message.reply("❌ Нельзя передать GRAM самому себе.")
                return
            if target_id == bot.id:
                await message.reply("🤖 Бот не принимает GRAM.")
                return
            user_balances[user_id] = sender_balance - amount
            user_balances[target_id] = user_balances.get(target_id, 0) + amount
            save_balances(user_balances)
            await message.reply(f"✅ Перевод {amount} GRAM для {target_name}\n💰 Ваш баланс: {user_balances[user_id]} GRAM")
            return
        elif len(cmd_parts) == 2:
            try:
                amount = int(cmd_parts[1])
            except:
                await message.reply("❌ Сумма должна быть числом.")
                return
            if amount <= 0:
                await message.reply("❌ Сумма должна быть больше нуля.")
                return
            if not message.reply_to_message:
                await message.reply("❌ Ответь на сообщение или используй `дать @username 1000`")
                return
            target_id = message.reply_to_message.from_user.id
            target_name = message.reply_to_message.from_user.full_name
            if target_id == bot.id:
                await message.reply("🤖 Бот не принимает GRAM.")
                return
            if target_id == user_id:
                await message.reply("❌ Нельзя передать GRAM самому себе.")
                return
            sender_balance = user_balances.get(user_id, 0)
            if amount > sender_balance:
                await message.reply(f"❌ Недостаточно GRAM. Ваш баланс: {sender_balance}")
                return
            user_balances[user_id] = sender_balance - amount
            user_balances[target_id] = user_balances.get(target_id, 0) + amount
            save_balances(user_balances)
            await message.reply(f"✅ Перевод {amount} GRAM для {target_name}\n💰 Ваш баланс: {user_balances[user_id]} GRAM")
            return
        else:
            await message.reply("❌ Формат: `дать @username 1000` или ответь на сообщение и напиши `дать 1000`")
            return

    # ========== ПОМОЩЬ ==========
    if text.lower() in ["помощь", "команды", "help", "старт", "/start"]:
        balance = user_balances.get(user_id, 0)
        await message.reply(
            f"{user_name}\n\n"
            f"🎰 GOLDEN GRAM ROULETTE\n\n"
            f"Ставки: 100 к, 200 ч, 500 чёт, 1000 23-34\n"
            f"Команды: б, лог, топ, бонус, го, дать\n\n"
            f"💰 Баланс: {balance} GRAM"
        )
        return

    # ========== ГО ==========
    if text.lower() == "го":
        now = int(time.time())
        if game_in_progress:
            await message.reply("⏳ Дождитесь окончания игры!")
            return
        if now - last_game_time < GAME_COOLDOWN:
            remaining = GAME_COOLDOWN - (now - last_game_time)
            await message.reply(f"⏰ Подожди {remaining} сек.")
            return
        if not pending_bets:
            await message.reply("❌ Нет активных ставок.")
            return

        game_in_progress = True

        # Сообщение о ожидании
        wait_msg = await message.answer("⏳ Подождите 10 секунд... Результаты скоро будут!")
        await asyncio.sleep(10)
        await bot.delete_message(chat_id=message.chat.id, message_id=wait_msg.message_id)

        # Крутим рулетку
        win_num, win_emoji, win_color, win_parity, win_dozen, win_column = spin_roulette()

        # Сохраняем в историю
        game_history.append(f"{win_emoji} {win_num}")
        if len(game_history) > 10:
            game_history.pop(0)
        save_history(game_history)

        # Обрабатываем ставки
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
                user_balances[uid] = user_balances.get(uid, 0) + winnings
                results.append(f"✅ {uname} +{winnings} GRAM ({amount} на {raw_bet})")
            else:
                results.append(f"❌ {uname} -{amount} GRAM ({raw_bet})")

        save_balances(user_balances)

        # Итоговое сообщение
        result_text = f"🎯 ВЫПАЛО: {win_emoji} {win_num}\n\n" + "\n".join(results)
        await message.answer(result_text)

        # Очистка
        pending_bets.clear()
        game_in_progress = False
        last_game_time = int(time.time())
        return

    # ========== СТАВКА ==========
    if len(parts) >= 2:
        if game_in_progress:
            await message.reply("⏳ Дождитесь окончания игры!")
            return
        now = int(time.time())
        if now - last_game_time < GAME_COOLDOWN:
            remaining = GAME_COOLDOWN - (now - last_game_time)
            await message.reply(f"⏰ Подожди {remaining} сек.")
            return
        try:
            amount = int(parts[0])
        except:
            return
        if amount <= 0:
            await message.reply("❌ Ставка > 0")
            return
        bet_type = " ".join(parts[1:])
        balance = user_balances.get(user_id, 0)
        if amount > balance:
            await message.reply(format_balance(user_name, balance) + "\n\n❌ Недостаточно GRAM.")
            return

        # Списываем сразу
        user_balances[user_id] = balance - amount
        save_balances(user_balances)

        pending_bets.append({
            "user_id": user_id,
            "user_name": user_name,
            "amount": amount,
            "raw_bet": bet_type
        })
        await message.reply(f"✅ Ставка принята: {user_name} {amount} GRAM на {bet_type}")

# ========== ЗАПУСК ==========
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
