import os
import asyncio
import logging
import random
import time
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message

API_TOKEN = os.environ.get("BOT_TOKEN", "8723084939:AAEO8Jd5oLYsAN-JMht4CBh2MUy_XWxH94M")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Данные в памяти
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

# ГИФКА
ROULETTE_GIF = "https://drive.google.com/uc?export=download&id=1S9DrcnA36xJ_nfPqDgH9h1ye7DYW-QBI"

pending_bets = []
game_in_progress = False
last_game_time = 0

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
    return bet

def check_win(bet: str, num: int, color: str) -> bool:
    bet = normalize_bet(bet)
    if bet == "красное" and color == "КРАСНОЕ": return True
    if bet == "чёрное" and color == "ЧЁРНОЕ": return True
    if bet == "чётное" and num != 0 and num % 2 == 0: return True
    if bet == "нечётное" and num % 2 == 1: return True
    if bet == "0" and num == 0: return True
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

@dp.message(Command("add_grams"))
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
    await message.reply(f"✅ +{format_amount(amount)} GRAM")

@dp.message()
async def handle(message: Message):
    global pending_bets, game_in_progress, last_game_time, game_history

    uid = message.from_user.id
    name = message.from_user.full_name or "Игрок"
    text = message.text.strip()
    parts = text.split()

    # Отмена
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
        await message.reply(f"✅ Возвращено {format_amount(refund)} GRAM")
        return

    # Профиль
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
            f"📊 Профит: {format_amount(profit)} GRAM</code>", parse_mode="HTML"
        )
        return

    # Бонус
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
            await message.reply(f"<code>🎁 +{format_amount(bonus)} GRAM\n🔥 Стрик: {ds['streak']} дн.</code>", parse_mode="HTML")
        else:
            rem = 86400 - (now - ds["last"])
            h, m = rem // 3600, (rem % 3600) // 60
            await message.reply(f"<code>⏰ Через {h} ч {m} мин</code>", parse_mode="HTML")
        return

    # Баланс
    if text.lower() in ["б", "баланс"]:
        bal = user_balances.get(uid, 0)
        await message.reply(f"<code>{name}\nБаланс: {format_amount(bal)} GRAM</code>", parse_mode="HTML")
        return

    # Лог
    if text.lower() in ["лог", "история"]:
        if not game_history:
            await message.reply("📋 Пусто")
            return
        row1 = " ".join(game_history[-10:][:5])
        row2 = " ".join(game_history[-10:][5:]) if len(game_history[-10:]) > 5 else ""
        txt = f"{row1}\n{row2}" if row2 else row1
        await message.reply(f"<code>{txt}</code>", parse_mode="HTML")
        return

    # Топ
    if text.lower() == "топ":
        if not user_balances:
            await message.reply("📊 Пусто")
            return
        sort = sorted(user_balances.items(), key=lambda x: x[1], reverse=True)[:10]
        txt = "🏆 ТОП-10:\n\n"
        for i, (u, b) in enumerate(sort, 1):
            try:
                u = await bot.get_chat(u)
                n = u.full_name
            except:
                n = str(u)
            txt += f"{i}. {n} — {format_amount(b)} GRAM\n"
        await message.reply(f"<code>{txt}</code>", parse_mode="HTML")
        return

    # Дать
    if text.lower().startswith("дать "):
        p = text.split()
        if len(p) == 3 and p[1].startswith("@"):
            try:
                amt = int(p[2])
            except:
                return
            if amt <= 0: return
            if user_balances.get(uid, 0) < amt:
                await message.reply("❌ Недостаточно")
                return
            try:
                t = await bot.get_chat(p[1])
                user_balances[uid] -= amt
                user_balances[t.id] = user_balances.get(t.id, 0) + amt
                await message.reply(f"✅ {format_amount(amt)} GRAM → {t.full_name}")
            except:
                await message.reply("❌ Не найден")
        elif len(p) == 2 and message.reply_to_message:
            try:
                amt = int(p[1])
            except:
                return
            if amt <= 0: return
            if user_balances.get(uid, 0) < amt:
                await message.reply("❌ Недостаточно")
                return
            t = message.reply_to_message.from_user
            if t.id == uid:
                await message.reply("❌ Нельзя себе")
                return
            user_balances[uid] -= amt
            user_balances[t.id] = user_balances.get(t.id, 0) + amt
            await message.reply(f"✅ {format_amount(amt)} GRAM → {t.full_name}")
        return

    # Помощь
    if text.lower() in ["помощь", "команды", "help", "старт", "/start"]:
        await message.reply(
            "<code>🎰 GOLDEN GRAM ROULETTE\n\n"
            "🎲 СТАВКИ:\n100 чёрное\n250 красное\n500 чётное\n1000 14\n2000 0\n5000 1-12\n10000 23-34\n"
            "Можно много: 1000 14 23-34 к 0\n\n"
            "🕹️ КОМАНДЫ:\nб — баланс\nлог — история\nтоп — рейтинг\nпрофиль — статистика\n"
            "бонус — ежед. награда\nго — запуск\nотмена — отмена ставок\nдать @user 1000\n\n"
            "📊 МНОЖИТЕЛИ:\nЧисло: x36\nКрасное/Чёрное: x2\nЧётное/Нечётное: x2\n"
            "Дюжина: x3\nДиапазон: по расчёту</code>", parse_mode="HTML"
        )
        return

    # ГО
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

        # ГИФКА
        gif_msg = None
        try:
            gif_msg = await message.answer_animation(ROULETTE_GIF, caption="🎰 Крутим...")
        except:
            await message.answer("<code>⏳ 10 секунд...</code>", parse_mode="HTML")

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

            all_bets = []
            win_res = []
            for b in pending_bets:
                uname = b["user_name"]
                amt = b["amount"]
                raw = b["raw_bet"]
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

                    win_res.append(f"{uname} ставка {format_amount(amt)} GRAM выиграл {format_amount(win_amt)} на {raw}")
                else:
                    if b["user_id"] not in user_stats:
                        user_stats[b["user_id"]] = {"played": 0, "won": 0, "total_bet": 0, "total_win": 0}
                    user_stats[b["user_id"]]["played"] += 1
                    user_stats[b["user_id"]]["total_bet"] += amt
                    user_levels[b["user_id"]] = user_levels.get(b["user_id"], 0) + 1

            await message.answer(f"<code>Рулетка: {win_num} {win_emoji}</code>", parse_mode="HTML")

            for i in range(0, len(all_bets), 50):
                await message.answer("<code>" + "\n".join(all_bets[i:i+50]) + "</code>", parse_mode="HTML")
            for i in range(0, len(win_res), 50):
                await message.answer("<code>" + "\n".join(win_res[i:i+50]) + "</code>", parse_mode="HTML")

        except Exception as e:
            logging.error(f"Ошибка игры: {e}")
            await message.answer("❌ Ошибка. Ставки возвращены")
            for b in pending_bets:
                user_balances[b["user_id"]] = user_balances.get(b["user_id"], 0) + b["amount"]

        finally:
            pending_bets.clear()
            game_in_progress = False
            last_game_time = int(time.time())
        return

    # Ставка
    if len(parts) >= 2:
        if game_in_progress:
            await message.reply("⏳ Идёт игра")
            return
        try:
            amt = int(parts[0])
        except:
            return
        if amt <= 0:
            await message.reply("❌ Ставка > 0")
            return

        bets = " ".join(parts[1:]).split()
        if len(bets) > MAX_BETS_PER_MESSAGE:
            await message.reply(f"❌ Максимум {MAX_BETS_PER_MESSAGE}")
            return

        total = amt * len(bets)
        bal = user_balances.get(uid, 0)
        if total > bal:
            await message.reply(f"❌ Нужно {format_amount(total)} GRAM")
            return

        user_balances[uid] = bal - total

        acc = []
        for b in bets:
            if not b: continue
            pending_bets.append({"user_id": uid, "user_name": name, "amount": amt, "raw_bet": b})
            acc.append(f"Ставка принята: {name} {format_amount(amt)} GRAM на {b}")

        for i in range(0, len(acc), 20):
            await message.reply("<code>" + "\n".join(acc[i:i+20]) + "</code>", parse_mode="HTML")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
