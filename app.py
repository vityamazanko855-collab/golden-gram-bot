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
user_stats = {}
user_levels = {}
daily_streak = {}
game_history = []

ADMIN_ID = 6003768110
GAME_COOLDOWN = 15
DAILY_BONUS_BASE = 500
DAILY_BONUS_STREAK_MULTIPLIER = 200
MAX_BETS_PER_MESSAGE = 500
MAX_LINES_PER_MESSAGE = 20
MAX_RESULT_LINES = 50

# Гифка для рулетки
ROULETTE_GIF = "https://media1.tenor.com/m/-_Wz-6rBqBUAAAAC/roulette-wheel.gif"

pending_bets = []
game_in_progress = False
last_game_time = 0
game_start_time = 0

# ========== ФОРМАТИРОВАНИЕ ==========
def format_amount(amount: int) -> str:
    return f"{amount:,}".replace(",", " ")

async def send_in_chunks(chat_id: int, lines: list, parse_mode: str = "HTML", chunk_size: int = 20):
    for i in range(0, len(lines), chunk_size):
        chunk = lines[i:i + chunk_size]
        text = "\n".join(chunk)
        if parse_mode == "HTML":
            text = f"<code>{text}</code>"
        await bot.send_message(chat_id, text, parse_mode=parse_mode if parse_mode == "HTML" else None)
        await asyncio.sleep(0.2)

# ========== РУЛЕТКА ==========
def spin_roulette():
    number = random.randint(0, 36)
    if number == 0:
        color_emoji = "🟢"
    elif number in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]:
        color_emoji = "🔴"
    else:
        color_emoji = "⚫"
    return number, color_emoji

def check_win(bet_type: str, number: int) -> bool:
    bet = bet_type.lower().strip()
    if not bet:
        return False
    if bet.isdigit():
        return int(bet) == number
    if "-" in bet:
        try:
            parts = bet.split("-")
            if len(parts) == 2:
                start = int(parts[0].strip())
                end = int(parts[1].strip())
                if start > end:
                    start, end = end, start
                return start <= number <= end
        except:
            return False
    return False

def get_multiplier(bet_type: str) -> int:
    bet = bet_type.lower().strip()
    if not bet:
        return 1
    if bet.isdigit() or bet == "0":
        return 36
    if "-" in bet:
        try:
            parts = bet.split("-")
            if len(parts) == 2:
                start = int(parts[0].strip())
                end = int(parts[1].strip())
                if start > end:
                    start, end = end, start
                count = end - start + 1
                if count <= 0:
                    return 1
                if count == 2: return 18
                elif count == 3: return 12
                elif count == 4: return 9
                elif count == 6: return 6
                elif count == 8: return 4
                elif count == 12: return 3
                elif count == 18: return 2
                else: return 36 // count
        except:
            return 2
    return 2

def get_level(exp: int) -> int:
    if exp < 10: return 1
    elif exp < 30: return 2
    elif exp < 60: return 3
    elif exp < 100: return 4
    else: return 5

def check_and_reset_stuck_game():
    global game_in_progress, pending_bets, last_game_time
    if game_in_progress:
        if time.time() - game_start_time > 60:
            game_in_progress = False
            pending_bets.clear()
            last_game_time = int(time.time())
            return True
    return False

# ========== АДМИН ==========
@dp.message(Command("add_grams"))
async def add_grams_slash(message: Message):
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
    await message.reply(f"✅ +{format_amount(amount)} GRAM\n💰 Баланс: {format_amount(user_balances[ADMIN_ID])} GRAM")

@dp.message(Command("reset_game"))
async def reset_game_slash(message: Message):
    global game_in_progress, pending_bets, last_game_time
    if message.from_user.id != ADMIN_ID:
        await message.reply("❌ У вас нет прав для этой команды.")
        return
    game_in_progress = False
    pending_bets.clear()
    last_game_time = int(time.time())
    await message.reply("✅ Состояние игры сброшено.")

# ========== ГЛАВНЫЙ ОБРАБОТЧИК ==========
@dp.message()
async def handle_message(message: Message):
    global pending_bets, game_in_progress, last_game_time, game_start_time, game_history

    user_id = message.from_user.id
    user_name = message.from_user.full_name or "Игрок"
    text = message.text.strip()
    parts = text.split()

    if check_and_reset_stuck_game():
        await message.answer("⚠️ Предыдущая игра была сброшена. Можете делать ставки.")

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
            f"<code>👤 {user_name}\n"
            f"🆔 {user_id}\n"
            f"📊 Уровень: {level}\n"
            f"💰 Баланс: {format_amount(balance)} GRAM\n\n"
            f"🎲 Игр: {stats['played']}\n"
            f"🏆 Побед: {stats['won']}\n"
            f"📈 Винрейт: {winrate:.1f}%\n"
            f"📊 Профит: {format_amount(profit)} GRAM</code>",
            parse_mode="HTML"
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
            await message.reply(f"<code>🎁 +{format_amount(bonus)} GRAM\n🔥 Стрик: {streak} дн.</code>", parse_mode="HTML")
        else:
            remaining = 24 * 60 * 60 - (now - last_claim)
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            await message.reply(f"<code>⏰ Следующий бонус через {hours} ч {minutes} мин</code>", parse_mode="HTML")
        return

    # ========== БАЛАНС ==========
    if text.lower() in ["б", "баланс"]:
        balance = user_balances.get(user_id, 0)
        await message.reply(f"<code>{user_name}\nБаланс: {format_amount(balance)} GRAM</code>", parse_mode="HTML")
        return

    # ========== ЛОГ ==========
    if text.lower() in ["лог", "история"]:
        if not game_history:
            await message.reply("📋 История пуста.")
            return
        row1 = " ".join(game_history[-10:][:5])
        row2 = " ".join(game_history[-10:][5:]) if len(game_history[-10:]) > 5 else ""
        if row2:
            await message.reply(f"<code>{row1}\n{row2}</code>", parse_mode="HTML")
        else:
            await message.reply(f"<code>{row1}</code>", parse_mode="HTML")
        return

    # ========== ТОП ==========
    if text.lower() == "топ":
        if not user_balances:
            await message.reply("📊 Пока никто не играл.")
            return
        sorted_users = sorted(user_balances.items(), key=lambda x: x[1], reverse=True)
        top_lines = ["🏆 ТОП-10 БОГАЧЕЙ:", ""]
        for i, (uid, bal) in enumerate(sorted_users[:10], 1):
            try:
                user_info = await bot.get_chat(uid)
                name = user_info.full_name
            except:
                name = f"ID: {uid}"
            top_lines.append(f"{i}. {name} — {format_amount(bal)} GRAM")
        await send_in_chunks(message.chat.id, top_lines, chunk_size=15)
        return

    # ========== ДАТЬ ==========
    if text.lower().startswith("дать "):
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
            await message.reply(f"<code>✅ {format_amount(amount)} GRAM → {target_name}</code>", parse_mode="HTML")
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
            await message.reply(f"<code>✅ {format_amount(amount)} GRAM → {target_name}</code>", parse_mode="HTML")
            return

    # ========== ПОМОЩЬ ==========
    if text.lower() in ["помощь", "команды", "старт", "/start"]:
        await message.reply(
            "<code>🎰 GOLDEN GRAM ROULETTE\n\n"
            "Ставки: 100 15 17 0 22-24 30-33\n"
            "Команды: б, лог, топ, бонус, го, профиль, отмена, дать</code>",
            parse_mode="HTML"
        )
        return

    # ========== ГО ==========
    if text.lower() == "го":
        now = int(time.time())
        
        if game_in_progress and (time.time() - game_start_time > 60):
            game_in_progress = False
            pending_bets.clear()
            await message.answer("⚠️ Предыдущая игра зависла и была сброшена. Запускаем новую.")
        
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
        game_start_time = time.time()
        
        # Отправляем гифку с рулеткой
        gif_msg = await message.answer_animation(ROULETTE_GIF, caption="🎰 Крутим рулетку...")
        
        await asyncio.sleep(10)
        
        # Удаляем гифку
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=gif_msg.message_id)
        except Exception:
            pass

        try:
            win_num, win_emoji = spin_roulette()
            
            # Сохраняем в историю
            game_history.append(f"{win_emoji} {win_num}")
            if len(game_history) > 10:
                game_history.pop(0)

            # Список всех ставок
            all_bets_lines = []
            for bet in pending_bets:
                uname = bet["user_name"]
                amount = bet["amount"]
                raw_bet = bet["raw_bet"]
                all_bets_lines.append(f"{uname} {format_amount(amount)} GRAM на {raw_bet}")

            # Список выигрышей
            win_results = []
            for bet in pending_bets:
                uid = bet["user_id"]
                uname = bet["user_name"]
                amount = bet["amount"]
                raw_bet = bet["raw_bet"]

                if not raw_bet:
                    continue

                try:
                    if check_win(raw_bet, win_num):
                        multiplier = get_multiplier(raw_bet)
                        winnings = amount * multiplier
                        user_balances[uid] = user_balances.get(uid, 0) + winnings
                        
                        if uid not in user_stats:
                            user_stats[uid] = {"played": 0, "won": 0, "total_bet": 0, "total_win": 0}
                        user_stats[uid]["played"] += 1
                        user_stats[uid]["won"] += 1
                        user_stats[uid]["total_bet"] += amount
                        user_stats[uid]["total_win"] += winnings
                        user_levels[uid] = user_levels.get(uid, 0) + 1
                        
                        win_results.append(f"{uname} ставка {format_amount(amount)} GRAM выиграл {format_amount(winnings)} на {raw_bet}")
                    else:
                        if uid not in user_stats:
                            user_stats[uid] = {"played": 0, "won": 0, "total_bet": 0, "total_win": 0}
                        user_stats[uid]["played"] += 1
                        user_stats[uid]["total_bet"] += amount
                        user_levels[uid] = user_levels.get(uid, 0) + 1
                except Exception as e:
                    logging.error(f"Ошибка в ставке {raw_bet}: {e}")
                    user_balances[uid] = user_balances.get(uid, 0) + amount

            # Отправляем заголовок
            await message.answer(f"<code>Рулетка: {win_num} {win_emoji}</code>", parse_mode="HTML")
            
            # Отправляем все ставки порциями
            if all_bets_lines:
                await send_in_chunks(message.chat.id, all_bets_lines, chunk_size=MAX_RESULT_LINES)
            
            # Отправляем выигрыши порциями
            if win_results:
                await send_in_chunks(message.chat.id, win_results, chunk_size=MAX_RESULT_LINES)

        except Exception as e:
            logging.error(f"Критическая ошибка в игре: {e}")
            await message.answer("❌ Произошла критическая ошибка. Все ставки возвращены.")
            for bet in pending_bets:
                uid = bet["user_id"]
                amount = bet["amount"]
                user_balances[uid] = user_balances.get(uid, 0) + amount

        finally:
            pending_bets.clear()
            game_in_progress = False
            last_game_time = int(time.time())
        return

    # ========== СТАВКА ==========
    if len(parts) >= 2:
        if check_and_reset_stuck_game():
            await message.answer("⚠️ Предыдущая игра была сброшена. Можете делать ставки.")
        
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
            if not bet:
                continue
            pending_bets.append({
                "user_id": user_id,
                "user_name": user_name,
                "amount": amount,
                "raw_bet": bet
            })
            accepted_lines.append(f"Ставка принята: {user_name} {format_amount(amount)} GRAM на {bet}")

        if accepted_lines:
            await send_in_chunks(message.chat.id, accepted_lines, chunk_size=MAX_LINES_PER_MESSAGE)

# ========== ЗАПУСК ==========
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
