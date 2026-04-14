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
MAX_BETS_PER_MESSAGE = 200

pending_bets = []
game_in_progress = False
last_game_time = 0

# ========== ФОРМАТИРОВАНИЕ ==========
def format_amount(amount: int) -> str:
    return f"{amount:,}".replace(",", " ")

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
    return number, color_emoji, color_name

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

def check_win(bet_type: str, number: int) -> bool:
    bet = normalize_bet_type(bet_type)
    if bet.isdigit():
        return int(bet) == number
    if "-" in bet:
        parts = bet.split("-")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            start, end = int(parts[0]), int(parts[1])
            return start <= number <= end
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
    return 2

def get_level(exp: int) -> int:
    if exp < 10: return 1
    elif exp < 30: return 2
    elif exp < 60: return 3
    elif exp < 100: return 4
    else: return 5

# ========== ГЛАВНЫЙ ОБРАБОТЧИК ==========
@dp.message()
async def handle_message(message: Message):
    global pending_bets, game_in_progress, last_game_time

    user_id = message.from_user.id
    user_name = message.from_user.full_name
    text = message.text.strip()
    parts = text.split()

    # ========== ОТМЕНА ==========
    if text.lower() in ["отмена", "отменить"]:
        if game_in_progress:
            await message.reply("⏳ Нельзя отменить ставки во время игры!")
            return

        user_bets = [bet for bet in pending_bets if bet["user_id"] == user_id]
        if not user_bets:
            await message.reply("❌ У вас нет активных ставок.")
            return

        total_refund = sum(bet["amount"] for bet in user_bets)
        new_pending = [bet for bet in pending_bets if bet["user_id"] != user_id]
        pending_bets.clear()
        pending_bets.extend(new_pending)
        
        user_balances[user_id] = user_balances.get(user_id, 0) + total_refund
        await message.reply(f"✅ Ставка отменена\n💰 Возвращено: {format_amount(total_refund)} GRAM")
        return

    # ========== ПРОФИЛЬ ==========
    if text.lower() in ["профиль", "profile"]:
        balance = user_balances.get(user_id, 0)
        stats = user_stats.get(user_id, {"played": 0, "won": 0, "total_bet": 0, "total_win": 0})
        exp = user_levels.get(user_id, 0)
        level = get_level(exp)
        winrate = (stats["won"] / stats["played"] * 100) if stats["played"] > 0 else 0
        profit = stats["total_win"] - stats["total_bet"]
        await message.reply(
            f"👤 {user_name}\n"
            f"🆔 {user_id}\n"
            f"📊 Уровень: {level}\n"
            f"💰 Баланс: {format_amount(balance)} GRAM\n\n"
            f"🎲 Игр: {stats['played']}\n"
            f"🏆 Побед: {stats['won']}\n"
            f"📈 Винрейт: {winrate:.1f}%\n"
            f"📊 Профит: {format_amount(profit)} GRAM"
        )
        return

    # ========== БОНУС ==========
    if text.lower() == "бонус":
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
            await message.reply(f"🎁 +{format_amount(bonus)} GRAM\n🔥 Стрик: {streak} дн.")
        else:
            remaining = 24 * 60 * 60 - (now - last_claim)
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            await message.reply(f"⏰ Следующий бонус через {hours} ч {minutes} мин")
        return

    # ========== БАЛАНС ==========
    if text.lower() in ["б", "баланс"]:
        balance = user_balances.get(user_id, 0)
        await message.reply(f"{user_name}\nБаланс: {format_amount(balance)} GRAM")
        return

    # ========== ТОП ==========
    if text.lower() == "топ":
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
            top_text += f"{i}. {name} — {format_amount(bal)} GRAM\n"
        await message.reply(top_text)
        return

    # ========== ПОМОЩЬ ==========
    if text.lower() in ["помощь", "команды", "старт", "/start"]:
        await message.reply("🎰 GOLDEN GRAM ROULETTE\n\nКоманды: б, топ, бонус, го, профиль, отмена")
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

        win_num, win_emoji, win_color = spin_roulette()

        # 1. Собираем список всех ставок
        all_bets_lines = []
        for bet in pending_bets:
            uname = bet["user_name"]
            amount = bet["amount"]
            raw_bet = bet["raw_bet"]
            all_bets_lines.append(f"{uname} {format_amount(amount)} GRAM на {raw_bet}")

        # 2. Собираем результаты выигрышей
        win_results = []
        for bet in pending_bets:
            uid = bet["user_id"]
            uname = bet["user_name"]
            amount = bet["amount"]
            raw_bet = bet["raw_bet"]

            if check_win(raw_bet, win_num):
                multiplier = get_multiplier(raw_bet)
                winnings = amount * multiplier
                user_balances[uid] = user_balances.get(uid, 0) + winnings
                
                # Обновляем статистику
                if uid not in user_stats:
                    user_stats[uid] = {"played": 0, "won": 0, "total_bet": 0, "total_win": 0}
                user_stats[uid]["played"] += 1
                user_stats[uid]["won"] += 1
                user_stats[uid]["total_bet"] += amount
                user_stats[uid]["total_win"] += winnings
                user_levels[uid] = user_levels.get(uid, 0) + 1
                
                win_results.append(f"{uname} ставка {format_amount(amount)} GRAM выиграл {format_amount(winnings)} на {raw_bet}")
            else:
                # Обновляем статистику проигрыша
                if uid not in user_stats:
                    user_stats[uid] = {"played": 0, "won": 0, "total_bet": 0, "total_win": 0}
                user_stats[uid]["played"] += 1
                user_stats[uid]["total_bet"] += amount
                user_levels[uid] = user_levels.get(uid, 0) + 1

        # Формируем итоговое сообщение
        final_message = f"Рулетка: {win_num} {win_emoji}\n\n"
        final_message += "\n".join(all_bets_lines)
        if win_results:
            final_message += "\n\n" + "\n".join(win_results)

        await message.answer(final_message)

        pending_bets.clear()
        game_in_progress = False
        last_game_time = int(time.time())
        return

    # ========== СТАВКА ==========
    if len(parts) >= 2:
        if game_in_progress:
            await message.reply("⏳ Дождитесь окончания!")
            return

        try:
            amount = int(parts[0])
        except:
            return

        if amount <= 0:
            await message.reply("❌ Ставка > 0")
            return

        bet_items = " ".join(parts[1:]).split()
        if len(bet_items) > MAX_BETS_PER_MESSAGE:
            await message.reply(f"❌ Максимум {MAX_BETS_PER_MESSAGE} ставок.")
            return

        total_needed = amount * len(bet_items)
        balance = user_balances.get(user_id, 0)

        if total_needed > balance:
            await message.reply(f"❌ Недостаточно GRAM (нужно {format_amount(total_needed)})")
            return

        user_balances[user_id] = balance - total_needed

        accepted_lines = []
        for bet in bet_items:
            pending_bets.append({
                "user_id": user_id,
                "user_name": user_name,
                "amount": amount,
                "raw_bet": bet
            })
            accepted_lines.append(f"Ставка принята: {user_name} {format_amount(amount)} GRAM на {bet}")

        await message.reply("\n".join(accepted_lines))

# ========== ЗАПУСК ==========
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
