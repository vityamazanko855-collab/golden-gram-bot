import os
import asyncio
import logging
import random
import time
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

API_TOKEN = os.environ.get("BOT_TOKEN", "8723084939:AAEO8Jd5oLYsAN-JMht4CBh2MUy_XWxH94M")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

user_balances = {}
user_stats = {}
user_levels = {}
daily_streak = {}
game_history = []
mines_games = {}
blackjack_games = {}  # Для блэкджека

ADMIN_ID = 6003768110
GAME_COOLDOWN = 15
DAILY_BONUS_BASE = 500
DAILY_BONUS_STREAK_MULTIPLIER = 200
MAX_BETS_PER_MESSAGE = 500

ROULETTE_GIF = "https://i.gifer.com/3P1d3.gif"

pending_bets = []
game_in_progress = False
last_game_time = 0

# Карты для блэкджека
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

# ========== ФУНКЦИИ ДЛЯ БЛЭКДЖЕКА ==========
def generate_deck():
    deck = [(rank, suit) for suit in SUITS for rank in RANKS]
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
    card_symbols = {
        "♠": "🂡", "♥": "🂱", "♦": "🃁", "♣": "🃑",
    }
    result = []
    for rank, suit in hand:
        if rank == "A":
            base = {"♠": "🂡", "♥": "🂱", "♦": "🃁", "♣": "🃑"}[suit]
        elif rank == "J":
            base = {"♠": "🂫", "♥": "🂻", "♦": "🃋", "♣": "🃛"}[suit]
        elif rank == "Q":
            base = {"♠": "🂭", "♥": "🂽", "♦": "🃍", "♣": "🃝"}[suit]
        elif rank == "K":
            base = {"♠": "🂮", "♥": "🂾", "♦": "🃎", "♣": "🃞"}[suit]
        else:
            offset = int(rank) - 1
            if suit == "♠":
                base = chr(0x1F0A1 + offset)
            elif suit == "♥":
                base = chr(0x1F0B1 + offset)
            elif suit == "♦":
                base = chr(0x1F0C1 + offset)
            else:  # ♣
                base = chr(0x1F0D1 + offset)
        result.append(f"{rank}{suit}")
    return " ".join(result)

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ КОМАНД ==========
async def help_cmd(message: Message):
    await message.reply(
        "<code>🎰 GOLDEN GRAM ROULETTE\n\n"
        "🎲 СТАВКИ:\n100 чёрное / 250 красное / 500 чётное\n1000 14 / 2000 0 / 5000 1-12\n"
        "Много: 1000 14 23-34 к 0\n\n"
        "💣 МИНЫ: мины 100\n"
        "🃏 БЛЭКДЖЕК: bj 100\n\n"
        "🕹️ КОМАНДЫ:\nб, лог, топ, профиль, бонус, го, отмена\n"
        "дать @user 1000 / дать всё (ответом)</code>",
        parse_mode="HTML"
    )

async def top_cmd(message: Message):
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
        f"📊 Профит: {format_amount(profit)} GRAM</code>", parse_mode="HTML"
    )

# ========== ОБРАБОТЧИК КОМАНД С УПОМИНАНИЕМ БОТА ==========
@dp.message(F.text.endswith("@Golden_Gram_Roulette_Bot"))
async def handle_mentioned_commands(message: Message):
    text = message.text.replace("@Golden_Gram_Roulette_Bot", "").strip()
    if text == "/top":
        await top_cmd(message)
    elif text == "/profile":
        await profile_cmd(message)
    elif text in ["/help", "/start"]:
        await help_cmd(message)

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

    # ========== БЛЭКДЖЕК ==========
    if text.lower().startswith("bj ") or text.lower().startswith("блекджек "):
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
        
        # Списываем ставку
        user_balances[uid] = bal - bet
        
        # Создаём колоду и раздаём карты
        deck = generate_deck()
        player_hand = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop(), deck.pop()]
        
        blackjack_games[uid] = {
            "bet": bet,
            "deck": deck,
            "player_hand": player_hand,
            "dealer_hand": dealer_hand,
            "active": True,
            "doubled": False
        }
        
        player_val = hand_value(player_hand)
        dealer_up = dealer_hand[0]
        
        # Проверка на мгновенный блэкджек
        if player_val == 21:
            # Игрок сразу выигрывает с x2.5
            win = int(bet * 2.5)
            user_balances[uid] = user_balances.get(uid, 0) + win
            
            if uid not in user_stats:
                user_stats[uid] = {"played": 0, "won": 0, "total_bet": 0, "total_win": 0}
            user_stats[uid]["played"] += 1
            user_stats[uid]["won"] += 1
            user_stats[uid]["total_bet"] += bet
            user_stats[uid]["total_win"] += win
            user_levels[uid] = user_levels.get(uid, 0) + 2
            
            del blackjack_games[uid]
            
            await message.reply(
                f"<code>🃏 БЛЭКДЖЕК!\n\n"
                f"Ваши карты: {format_cards(player_hand)} ({player_val})\n"
                f"Карты дилера: {format_cards(dealer_hand)} ({hand_value(dealer_hand)})\n\n"
                f"🎉 ВЫ ВЫИГРАЛИ x2.5!\n"
                f"💰 +{format_amount(win)} GRAM</code>",
                parse_mode="HTML"
            )
            return
        
        kb = InlineKeyboardBuilder()
        kb.button(text="🃏 Взять", callback_data="bj_hit")
        kb.button(text="✋ Хватит", callback_data="bj_stand")
        kb.button(text="🏳️ Сдаюсь", callback_data="bj_surrender")
        kb.adjust(3)
        
        await message.reply(
            f"<code>🃏 БЛЭКДЖЕК\n"
            f"💰 Ставка: {format_amount(bet)} GRAM\n\n"
            f"Ваши карты: {format_cards(player_hand)} ({player_val})\n"
            f"Карта дилера: {format_cards([dealer_up])}</code>",
            parse_mode="HTML",
            reply_markup=kb.as_markup()
        )
        return

    if text.lower().startswith("мины "):
        try:
            bet = int(parts[1])
        except:
            await message.reply("❌ Пример: мины 100")
            return
        if bet <= 0:
            await message.reply("❌ Ставка > 0")
            return
        bal = user_balances.get(uid, 0)
        if bet > bal:
            await message.reply("❌ Недостаточно GRAM")
            return
        user_balances[uid] = bal - bet
        field = generate_mines_field()
        mines_games[uid] = {"bet": bet, "field": field, "revealed": [], "multiplier": 1.0, "active": True}

        kb = InlineKeyboardBuilder()
        for i in range(5):
            for j in range(5):
                kb.button(text="❓", callback_data=f"m_{i}_{j}")
        kb.adjust(5)

        await message.answer(
            f"💎 {name}, вы начали игру минное поле!\n"
            f"📌 Ставка: {format_amount(bet)} GRAM\n"
            f"💲 Выигрыш: x1,0 | {format_amount(bet)} GRAM\n\n"
            f"{format_mines_field(field, [])}",
            reply_markup=kb.as_markup()
        )
        return

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

    if text.lower() in ["профиль", "profile"]:
        await profile_cmd(message)
        return

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

    if text.lower() in ["б", "баланс"]:
        bal = user_balances.get(uid, 0)
        await message.reply(f"<code>{name}\nБаланс: {format_amount(bal)} GRAM</code>", parse_mode="HTML")
        return

    if text.lower() in ["лог", "история"]:
        if not game_history:
            await message.reply("📋 Пусто")
            return
        log_lines = [entry for entry in game_history[-10:]]
        log_text = "\n".join(log_lines)
        await message.reply(f"<code>{log_text}</code>", parse_mode="HTML")
        return

    if text.lower() == "топ":
        await top_cmd(message)
        return

    if text.lower().startswith("дать "):
        p = text.split()
        if len(p) == 2 and p[1] == "всё" and message.reply_to_message:
            t = message.reply_to_message.from_user
            if t.id == uid:
                await message.reply("❌ Нельзя себе")
                return
            amt = user_balances.get(uid, 0)
            if amt <= 0:
                await message.reply("❌ 0 GRAM")
                return
            user_balances[uid] = 0
            user_balances[t.id] = user_balances.get(t.id, 0) + amt
            await message.reply(f"✅ Все {format_amount(amt)} GRAM → {t.full_name}")
            return
        elif len(p) == 3 and p[1].startswith("@"):
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

    if text.lower() in ["помощь", "команды", "help", "старт", "/start"]:
        await help_cmd(message)
        return

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
