import os
import asyncio
import logging
import random
import time
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, BotCommand
from aiogram.utils.keyboard import InlineKeyboardBuilder

API_TOKEN = os.environ.get("BOT_TOKEN", "8723084939:AAEO8Jd5oLYsAN-JMht4CBh2MUy_XWxH94M")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

from aiogram.filters import Command

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.reply("рџЋ° Р‘РѕС‚ Р·Р°РїСѓС‰РµРЅ. РќР°РїРёС€Рё 'РїРѕРјРѕС‰СЊ'")

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await cmd_start(message)

@dp.message(Command("top"))
async def cmd_top(message: Message):
    if not user_balances:
        await message.reply("рџ“Љ РџСѓСЃС‚Рѕ")
        return
    sort = sorted(user_balances.items(), key=lambda x: x[1], reverse=True)[:10]
    txt = "рџЏ† РўРћРџ-10:\n\n"
    for i, (u, b) in enumerate(sort, 1):
        txt += f"{i}. {u} вЂ” {b}\n"
    await message.reply(txt)

@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    uid = message.from_user.id
    bal = user_balances.get(uid, 0)
    await message.reply(f"рџ‘¤ РџСЂРѕС„РёР»СЊ\nрџ’° Р‘Р°Р»Р°РЅСЃ: {bal}")


# вњ… Р”РћР‘РђР’Р›Р•РќРћ (РјРµРЅСЋ РєРѕРјР°РЅРґ)
async def set_commands():
    commands = [
        BotCommand(command="start", description="РіР»Р°РІРЅРѕРµ РјРµРЅСЋ"),
        BotCommand(command="help", description="РїРѕРјРѕС‰СЊ"),
        BotCommand(command="top", description="С‚РѕРї"),
        BotCommand(command="profile", description="РїСЂРѕС„РёР»СЊ"),
    ]
    await bot.set_my_commands(commands)

user_balances = {}
user_stats = {}
user_levels = {}
daily_streak = {}
game_history = []
mines_games = {}

ADMIN_ID = 6003768110
GAME_COOLDOWN = 15
DAILY_BONUS_BASE = 500
DAILY_BONUS_STREAK_MULTIPLIER = 200
MAX_BETS_PER_MESSAGE = 500

ROULETTE_GIF = "https://i.gifer.com/3P1d3.gif"

pending_bets = []
game_in_progress = False
last_game_time = 0

def format_amount(amount: int) -> str:
    return f"{amount:,}".replace(",", " ")

def spin_roulette():
    number = random.randint(0, 36)
    if number == 0:
        color_emoji = "рџџў"
        color_name = "Р—Р•Р›РЃРќРћР•"
    elif number in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]:
        color_emoji = "рџ”ґ"
        color_name = "РљР РђРЎРќРћР•"
    else:
        color_emoji = "вљ«"
        color_name = "Р§РЃР РќРћР•"
    return number, color_emoji, color_name

def normalize_bet(bet: str) -> str:
    bet = bet.lower().strip()
    if bet in ["Рє", "РєСЂР°СЃРЅРѕРµ", "РєСЂР°СЃРЅС‹Р№", "red", "рџ”ґ"]: return "РєСЂР°СЃРЅРѕРµ"
    if bet in ["С‡", "С‡С‘СЂРЅРѕРµ", "С‡РµСЂРЅРѕРµ", "С‡С‘СЂРЅС‹Р№", "С‡РµСЂРЅС‹Р№", "black", "вљ«"]: return "С‡С‘СЂРЅРѕРµ"
    if bet in ["С‡С‘С‚", "С‡РµС‚", "С‡С‘С‚РЅРѕРµ", "С‡РµС‚РЅРѕРµ", "even"]: return "С‡С‘С‚РЅРѕРµ"
    if bet in ["РЅРµС‡", "РЅРµС‡С‘С‚РЅРѕРµ", "РЅРµС‡РµС‚РЅРѕРµ", "odd"]: return "РЅРµС‡С‘С‚РЅРѕРµ"
    if bet in ["0", "Р·РµСЂРѕ", "zero", "рџџў"]: return "0"
    if bet in ["1-СЏ", "1СЏ", "РїРµСЂРІР°СЏ", "РїРµСЂРІС‹Р№"]: return "1-СЏ"
    if bet in ["2-СЏ", "2СЏ", "РІС‚РѕСЂР°СЏ", "РІС‚РѕСЂРѕР№"]: return "2-СЏ"
    if bet in ["3-СЏ", "3СЏ", "С‚СЂРµС‚СЊСЏ", "С‚СЂРµС‚РёР№"]: return "3-СЏ"
    return bet

def check_win(bet: str, num: int, color: str) -> bool:
    bet = normalize_bet(bet)
    if bet == "РєСЂР°СЃРЅРѕРµ" and color == "РљР РђРЎРќРћР•": return True
    if bet == "С‡С‘СЂРЅРѕРµ" and color == "Р§РЃР РќРћР•": return True
    if bet == "С‡С‘С‚РЅРѕРµ" and num != 0 and num % 2 == 0: return True
    if bet == "РЅРµС‡С‘С‚РЅРѕРµ" and num % 2 == 1: return True
    if bet == "0" and num == 0: return True
    if bet == "1-12" and 1 <= num <= 12: return True
    if bet == "13-24" and 13 <= num <= 24: return True
    if bet == "25-36" and 25 <= num <= 36: return True
    if bet == "1-СЏ" and num != 0 and num % 3 == 1: return True
    if bet == "2-СЏ" and num != 0 and num % 3 == 2: return True
    if bet == "3-СЏ" and num != 0 and num % 3 == 0: return True
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
    if bet in ["РєСЂР°СЃРЅРѕРµ", "С‡С‘СЂРЅРѕРµ", "С‡С‘С‚РЅРѕРµ", "РЅРµС‡С‘С‚РЅРѕРµ"]: return 2
    if bet == "0" or bet.isdigit(): return 36
    if bet in ["1-12", "13-24", "25-36", "1-СЏ", "2-СЏ", "3-СЏ"]: return 3
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
    field = [["в­ђ" for _ in range(5)] for _ in range(5)]
    mines = random.sample(range(25), 3)
    for m in mines:
        row, col = m // 5, m % 5
        field[row][col] = "рџ’Ј"
    return field

def format_mines_field(field, revealed):
    lines = []
    for i in range(5):
        row = " ".join(field[i][j] if (i, j) in revealed else "вќ“" for j in range(5))
        lines.append(row)
    return "\n".join(lines)

@dp.message(Command("add_grams"))
async def add_grams(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.reply("вќЊ РќРµС‚ РїСЂР°РІ")
        return
    parts = message.text.split()
    if len(parts) != 2:
        await message.reply("вќЊ /add_grams 5000")
        return
    try:
        amount = int(parts[1])
    except:
        await message.reply("вќЊ РЎСѓРјРјР° С‡РёСЃР»РѕРј")
        return
    user_balances[ADMIN_ID] = user_balances.get(ADMIN_ID, 0) + amount
    await message.reply(f"вњ… +{format_amount(amount)} GRAM")

@dp.message()
async def handle(message: Message):
    global pending_bets, game_in_progress, last_game_time, game_history

    uid = message.from_user.id
    name = message.from_user.full_name or "РРіСЂРѕРє"
    text = message.text.strip()
    parts = text.split()

    if text.lower().startswith("РјРёРЅС‹ "):
        try:
            bet = int(parts[1])
        except:
            await message.reply("вќЊ РџСЂРёРјРµСЂ: РјРёРЅС‹ 100")
            return
        if bet <= 0:
            await message.reply("вќЊ РЎС‚Р°РІРєР° > 0")
            return
        bal = user_balances.get(uid, 0)
        if bet > bal:
            await message.reply("вќЊ РќРµРґРѕСЃС‚Р°С‚РѕС‡РЅРѕ GRAM")
            return
        user_balances[uid] = bal - bet
        field = generate_mines_field()
        mines_games[uid] = {"bet": bet, "field": field, "revealed": [], "multiplier": 1.0, "active": True}

        kb = InlineKeyboardBuilder()
        for i in range(5):
            for j in range(5):
                kb.button(text="вќ“", callback_data=f"m_{i}_{j}")
        kb.adjust(5)

        await message.answer(
            f"рџ’Ћ {name}, РІС‹ РЅР°С‡Р°Р»Рё РёРіСЂСѓ РјРёРЅРЅРѕРµ РїРѕР»Рµ!\n"
            f"рџ“Њ РЎС‚Р°РІРєР°: {format_amount(bet)} GRAM\n"
            f"рџ’І Р’С‹РёРіСЂС‹С€: x1,0 | {format_amount(bet)} GRAM\n\n"
            f"{format_mines_field(field, [])}",
            reply_markup=kb.as_markup()
        )
        return

    if text.lower() in ["РѕС‚РјРµРЅР°", "РѕС‚РјРµРЅРёС‚СЊ"]:
        if game_in_progress:
            await message.reply("вЏі РРґС‘С‚ РёРіСЂР°")
            return
        user_bets = [b for b in pending_bets if b["user_id"] == uid]
        if not user_bets:
            await message.reply("вќЊ РќРµС‚ СЃС‚Р°РІРѕРє")
            return
        refund = sum(b["amount"] for b in user_bets)
        pending_bets = [b for b in pending_bets if b["user_id"] != uid]
        user_balances[uid] = user_balances.get(uid, 0) + refund
        await message.reply(f"вњ… Р’РѕР·РІСЂР°С‰РµРЅРѕ {format_amount(refund)} GRAM")
        return

    if text.lower() in ["РїСЂРѕС„РёР»СЊ", "profile"]:
        bal = user_balances.get(uid, 0)
        stats = user_stats.get(uid, {"played": 0, "won": 0, "total_bet": 0, "total_win": 0})
        exp = user_levels.get(uid, 0)
        lvl = get_level(exp)
        winrate = (stats["won"] / stats["played"] * 100) if stats["played"] > 0 else 0
        profit = stats["total_win"] - stats["total_bet"]
        await message.reply(
            f"<code>рџ‘¤ {name}\nрџ†” {uid}\nрџ“Љ РЈСЂРѕРІРµРЅСЊ: {lvl}\nрџ’° {format_amount(bal)} GRAM\n\n"
            f"рџЋІ РРіСЂ: {stats['played']}\nрџЏ† РџРѕР±РµРґ: {stats['won']}\nрџ“€ Р’РёРЅСЂРµР№С‚: {winrate:.1f}%\n"
            f"рџ“Љ РџСЂРѕС„РёС‚: {format_amount(profit)} GRAM</code>", parse_mode="HTML"
        )
        return

    if text.lower() == "Р±РѕРЅСѓСЃ":
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
            await message.reply(f"<code>рџЋЃ +{format_amount(bonus)} GRAM\nрџ”Ґ РЎС‚СЂРёРє: {ds['streak']} РґРЅ.</code>", parse_mode="HTML")
        else:
            rem = 86400 - (now - ds["last"])
            h, m = rem // 3600, (rem % 3600) // 60
            await message.reply(f"<code>вЏ° Р§РµСЂРµР· {h} С‡ {m} РјРёРЅ</code>", parse_mode="HTML")
        return

    if text.lower() in ["Р±", "Р±Р°Р»Р°РЅСЃ"]:
        bal = user_balances.get(uid, 0)
        await message.reply(f"<code>{name}\nР‘Р°Р»Р°РЅСЃ: {format_amount(bal)} GRAM</code>", parse_mode="HTML")
        return

    if text.lower() in ["Р»РѕРі", "РёСЃС‚РѕСЂРёСЏ"]:
        if not game_history:
            await message.reply("рџ“‹ РџСѓСЃС‚Рѕ")
            return
        log_lines = [entry for entry in game_history[-10:]]
        log_text = "\n".join(log_lines)
        await message.reply(f"<code>{log_text}</code>", parse_mode="HTML")
        return

    if text.lower() == "С‚РѕРї":
        if not user_balances:
            await message.reply("рџ“Љ РџСѓСЃС‚Рѕ")
            return
        sort = sorted(user_balances.items(), key=lambda x: x[1], reverse=True)[:10]
        txt = "рџЏ† РўРћРџ-10:\n\n"
        for i, (u, b) in enumerate(sort, 1):
            try:
                u = await bot.get_chat(u)
                n = u.full_name
            except:
                n = str(u)
            txt += f"{i}. {n} вЂ” {format_amount(b)} GRAM\n"
        await message.reply(f"<code>{txt}</code>", parse_mode="HTML")
        return

    if text.lower().startswith("РґР°С‚СЊ "):
        p = text.split()
        if len(p) == 2 and p[1] == "РІСЃС‘" and message.reply_to_message:
            t = message.reply_to_message.from_user
            if t.id == uid:
                await message.reply("вќЊ РќРµР»СЊР·СЏ СЃРµР±Рµ")
                return
            amt = user_balances.get(uid, 0)
            if amt <= 0:
                await message.reply("вќЊ 0 GRAM")
                return
            user_balances[uid] = 0
            user_balances[t.id] = user_balances.get(t.id, 0) + amt
            await message.reply(f"вњ… Р’СЃРµ {format_amount(amt)} GRAM в†’ {t.full_name}")
            return
        elif len(p) == 3 and p[1].startswith("@"):
            try:
                amt = int(p[2])
            except:
                return
            if amt <= 0: return
            if user_balances.get(uid, 0) < amt:
                await message.reply("вќЊ РќРµРґРѕСЃС‚Р°С‚РѕС‡РЅРѕ")
                return
            try:
                t = await bot.get_chat(p[1])
                user_balances[uid] -= amt
                user_balances[t.id] = user_balances.get(t.id, 0) + amt
                await message.reply(f"вњ… {format_amount(amt)} GRAM в†’ {t.full_name}")
            except:
                await message.reply("вќЊ РќРµ РЅР°Р№РґРµРЅ")
        elif len(p) == 2 and message.reply_to_message:
            try:
                amt = int(p[1])
            except:
                return
            if amt <= 0: return
            if user_balances.get(uid, 0) < amt:
                await message.reply("вќЊ РќРµРґРѕСЃС‚Р°С‚РѕС‡РЅРѕ")
                return
            t = message.reply_to_message.from_user
            if t.id == uid:
                await message.reply("вќЊ РќРµР»СЊР·СЏ СЃРµР±Рµ")
                return
            user_balances[uid] -= amt
            user_balances[t.id] = user_balances.get(t.id, 0) + amt
            await message.reply(f"вњ… {format_amount(amt)} GRAM в†’ {t.full_name}")
        return

    if text.lower() in ["РїРѕРјРѕС‰СЊ", "РєРѕРјР°РЅРґС‹", "help", "СЃС‚Р°СЂС‚"]:
        await message.reply(
            "<code>рџЋ° GOLDEN GRAM ROULETTE\n\n"
            "рџЋІ РЎРўРђР’РљР:\n100 С‡С‘СЂРЅРѕРµ / 250 РєСЂР°СЃРЅРѕРµ / 500 С‡С‘С‚РЅРѕРµ\n1000 14 / 2000 0 / 5000 1-12\n"
            "РњРЅРѕРіРѕ: 1000 14 23-34 Рє 0\n\n"
            "рџ’Ј РњРРќР«: РјРёРЅС‹ 100\n\n"
            "рџ•№пёЏ РљРћРњРђРќР”Р«:\nР±, Р»РѕРі, С‚РѕРї, РїСЂРѕС„РёР»СЊ, Р±РѕРЅСѓСЃ, РіРѕ, РѕС‚РјРµРЅР°\n"
            "РґР°С‚СЊ @user 1000 / РґР°С‚СЊ РІСЃС‘ (РѕС‚РІРµС‚РѕРј)</code>",
            parse_mode="HTML"
        )
        return

    if text.lower() == "РіРѕ":
        now = int(time.time())
        if game_in_progress:
            await message.reply("вЏі РРґС‘С‚ РёРіСЂР°")
            return
        if now - last_game_time < GAME_COOLDOWN:
            await message.reply(f"вЏ° РџРѕРґРѕР¶РґРё {GAME_COOLDOWN - (now - last_game_time)} СЃРµРє")
            return
        if not pending_bets:
            await message.reply("вќЊ РќРµС‚ СЃС‚Р°РІРѕРє")
            return

        game_in_progress = True
        try:
            gif_msg = await message.answer_animation(ROULETTE_GIF, caption="рџЋ° РљСЂСѓС‚РёРј...")
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
                all_bets.append(f"{uname} {format_amount(amt)} GRAM РЅР° {raw}")

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

                    win_res.append(f"{uname} СЃС‚Р°РІРєР° {format_amount(amt)} GRAM РІС‹РёРіСЂР°Р» {format_amount(win_amt)} РЅР° {raw}")
                else:
                    if b["user_id"] not in user_stats:
                        user_stats[b["user_id"]] = {"played": 0, "won": 0, "total_bet": 0, "total_win": 0}
                    user_stats[b["user_id"]]["played"] += 1
                    user_stats[b["user_id"]]["total_bet"] += amt
                    user_levels[b["user_id"]] = user_levels.get(b["user_id"], 0) + 1

            await message.answer(f"<code>Р СѓР»РµС‚РєР°: {win_num} {win_emoji}</code>", parse_mode="HTML")
            for i in range(0, len(all_bets), 50):
                await message.answer("<code>" + "\n".join(all_bets[i:i+50]) + "</code>", parse_mode="HTML")
            for i in range(0, len(win_res), 50):
                await message.answer("<code>" + "\n".join(win_res[i:i+50]) + "</code>", parse_mode="HTML")

        except Exception as e:
            logging.error(f"РћС€РёР±РєР°: {e}")
            await message.answer("вќЊ РћС€РёР±РєР°. РЎС‚Р°РІРєРё РІРѕР·РІСЂР°С‰РµРЅС‹")
            for b in pending_bets:
                user_balances[b["user_id"]] = user_balances.get(b["user_id"], 0) + b["amount"]

        finally:
            pending_bets.clear()
            game_in_progress = False
            last_game_time = int(time.time())
        return

    if len(parts) >= 2:
        if game_in_progress:
            await message.reply("вЏі РРґС‘С‚ РёРіСЂР°")
            return
        try:
            amt = int(parts[0])
        except:
            return
        if amt <= 0:
            await message.reply("вќЊ РЎС‚Р°РІРєР° > 0")
            return

        bets = " ".join(parts[1:]).split()
        if len(bets) > MAX_BETS_PER_MESSAGE:
            await message.reply(f"вќЊ РњР°РєСЃРёРјСѓРј {MAX_BETS_PER_MESSAGE} СЃС‚Р°РІРѕРє")
            return

        total = amt * len(bets)
        bal = user_balances.get(uid, 0)
        if total > bal:
            await message.reply(f"вќЊ РќСѓР¶РЅРѕ {format_amount(total)} GRAM")
            return

        user_balances[uid] = bal - total

        acc = []
        for b in bets:
            if not b: continue
            pending_bets.append({"user_id": uid, "user_name": name, "amount": amt, "raw_bet": b})
            acc.append(f"РЎС‚Р°РІРєР° РїСЂРёРЅСЏС‚Р°: {name} {format_amount(amt)} GRAM РЅР° {b}")

        for i in range(0, len(acc), 20):
            await message.reply("<code>" + "\n".join(acc[i:i+20]) + "</code>", parse_mode="HTML")

@dp.callback_query(F.data.startswith("m_"))
async def mine_click(call: CallbackQuery):
    await call.answer()
    uid = call.from_user.id

    if uid not in mines_games:
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

    if cell == "рџ’Ј":
        g["active"] = False
        del mines_games[uid]
        await call.message.edit_text(
            f"рџ’Ґ {call.from_user.full_name}, РјРёРЅР°!\nвќЊ -{format_amount(g['bet'])} GRAM\n\n"
            f"{format_mines_field(g['field'], g['revealed'])}"
        )
        return

    g["multiplier"] += 0.14
    pot = int(g["bet"] * g["multiplier"])

    kb = InlineKeyboardBuilder()
    for i in range(5):
        for j in range(5):
            if (i, j) in g["revealed"]:
                kb.button(text=g["field"][i][j], callback_data="done")
            else:
                kb.button(text="вќ“", callback_data=f"m_{i}_{j}")

    if g["revealed"]:
        kb.button(text="рџ’° Р—Р°Р±СЂР°С‚СЊ РІС‹РёРіСЂС‹С€", callback_data="cash")

    kb.adjust(5, 5, 5, 5, 5, 1) if g["revealed"] else kb.adjust(5, 5, 5, 5, 5)

    await call.message.edit_te
