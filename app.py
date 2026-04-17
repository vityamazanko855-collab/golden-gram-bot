import os,asyncio,logging,random,time,json
from aiogram import Bot,Dispatcher,types
from aiogram.types import Message,CallbackQuery,InlineKeyboardMarkup,InlineKeyboardButton
from aiogram.utils import executor

API_TOKEN=os.environ.get("BOT_TOKEN","8723084939:AAEO8Jd5oLYsAN-JMht4CBh2MUy_XWxH94M")
logging.basicConfig(level=logging.INFO)
bot=Bot(token=API_TOKEN)
dp=Dispatcher(bot)

user_balances={}
user_stats={}
user_levels={}
daily_streak={}
game_history=[]
mines_games={}
blackjack_games={}
pending_bets=[]
game_in_progress=False
last_game_time=0
user_achievements={}
user_prestige={}
user_titles={}
user_active_title={}
user_badges={}
user_lottery_tickets={}
user_referrals={}
user_referrer={}
used_promocodes={}

ADMIN_ID=6003768110
GAME_COOLDOWN=15
DAILY_BONUS_BASE=500
DAILY_BONUS_STREAK_MULTIPLIER=200
MAX_BETS_PER_MESSAGE=500
ROULETTE_GIF="https://i.gifer.com/3P1d3.gif"
DATA_FILE="bot_data.json"

daily_quests={}
last_quest_reset=int(time.time())
last_lottery_time=0
lottery_pool=0

# ========== ЗНАЧКИ ==========
BADGES = {
    "beginner": {"name": "🟢 НОВИЧОК", "desc": "Сыграть первую игру", "icon": "🟢"},
    "winner": {"name": "🏆 ПОБЕДИТЕЛЬ", "desc": "Выиграть 10 раз", "icon": "🏆"},
    "expert": {"name": "🔴 ЭКСПЕРТ", "desc": "Выиграть 100 раз", "icon": "🔴"},
    "millionaire": {"name": "💰 МИЛЛИОНЕР", "desc": "Накопить 1 000 000 GOLD", "icon": "💰"},
    "billionaire": {"name": "💎 МИЛЛИАРДЕР", "desc": "Накопить 1 000 000 000 GOLD", "icon": "💎"},
    "lucky": {"name": "🍀 ВЕЗУНЧИК", "desc": "Выиграть 3 раза подряд", "icon": "🍀"},
    "gambler": {"name": "🎲 АЗАРТНЫЙ", "desc": "Сыграть 500 игр", "icon": "🎲"},
    "slot_king": {"name": "👑 КОРОЛЬ СЛОТОВ", "desc": "Выиграть джекпот в слотах", "icon": "👑"},
    "card_master": {"name": "🃏 КАРТЁЖНИК", "desc": "Выиграть в блэкджек 50 раз", "icon": "🃏"},
    "sapper": {"name": "💣 САПЁР", "desc": "Выиграть в минах 25 раз", "icon": "💣"},
    "fortune": {"name": "🎡 ФОРТУНА", "desc": "Выиграть x100 на колесе", "icon": "🎡"},
    "lottery": {"name": "🍀 ЛОТЕРЕЙЩИК", "desc": "Выиграть в лотерее", "icon": "🍀"},
    "sport": {"name": "⚽ СПОРТСМЕН", "desc": "Выиграть спортивную ставку", "icon": "⚽"},
    "rps": {"name": "✊ КНБ МАСТЕР", "desc": "Выиграть в КНБ 10 раз", "icon": "✊"},
    "streak10": {"name": "🔥 СТРИКЕР X10", "desc": "Выиграть 10 раз подряд", "icon": "🔥"},
    "bowler": {"name": "🎳 БОУЛЕР", "desc": "Выбить страйк в боулинге", "icon": "🎳"},
    "dart_master": {"name": "🎯 МАСТЕР ДАРТСА", "desc": "Попасть в яблочко", "icon": "🎯"},
    "basketball_star": {"name": "🏀 ЗВЕЗДА", "desc": "Забить трёхочковый", "icon": "🏀"},
    "referrer": {"name": "👥 ЛИДЕР", "desc": "Привести 10 друзей", "icon": "👥"}
}

# ========== ЗВАНИЯ ==========
RANKS = [
    {"name": "🎖️ РЯДОВОЙ", "need": 0, "reward": 0},
    {"name": "🎖️ ЕФРЕЙТОР", "need": 50000, "reward": 5000},
    {"name": "🎖️ СЕРЖАНТ", "need": 250000, "reward": 20000},
    {"name": "🎖️ СТАРШИНА", "need": 1000000, "reward": 50000},
    {"name": "🎖️ ПРАПОРЩИК", "need": 5000000, "reward": 100000},
    {"name": "🎖️ ЛЕЙТЕНАНТ", "need": 20000000, "reward": 200000},
    {"name": "🎖️ КАПИТАН", "need": 50000000, "reward": 400000},
    {"name": "🎖️ МАЙОР", "need": 100000000, "reward": 750000},
    {"name": "🎖️ ПОЛКОВНИК", "need": 250000000, "reward": 1500000},
    {"name": "🎖️ ГЕНЕРАЛ", "need": 500000000, "reward": 3000000},
    {"name": "🎖️ МАРШАЛ", "need": 1000000000, "reward": 10000000}
]

# ========== ПРЕСТИЖ ==========
PRESTIGE_LEVELS = [
    {"name": "🌟 1 ПРЕСТИЖ", "need_level": 50, "reward": 500000},
    {"name": "🌟🌟 2 ПРЕСТИЖ", "need_level": 100, "reward": 1000000},
    {"name": "🌟🌟🌟 3 ПРЕСТИЖ", "need_level": 200, "reward": 2500000},
    {"name": "🌟🌟🌟🌟 4 ПРЕСТИЖ", "need_level": 300, "reward": 5000000},
    {"name": "🌟🌟🌟🌟🌟 5 ПРЕСТИЖ", "need_level": 500, "reward": 10000000}
]

# ========== ТИТУЛЫ ==========
TITLES = {
    "lucky": {"name": "🍀 ВЕЗУНЧИК", "desc": "Выиграть 5 раз подряд", "need_streak": 5},
    "winner": {"name": "🏆 ПОБЕДИТЕЛЬ", "desc": "Выиграть 100 раз", "need_wins": 100},
    "millionaire": {"name": "💰 МИЛЛИОНЕР", "desc": "Накопить 1 000 000 GOLD", "need_balance": 1000000},
    "gambler": {"name": "🎲 АЗАРТНЫЙ", "desc": "Сыграть 500 игр", "need_games": 500},
    "sapper": {"name": "💣 САПЁР", "desc": "Выиграть в минах 25 раз", "need_mines_wins": 25},
    "carder": {"name": "🃏 КАРТЁЖНИК", "desc": "Выиграть в блэкджек 50 раз", "need_bj_wins": 50},
    "slot_master": {"name": "🎰 СЛОТ-МАСТЕР", "desc": "Выиграть джекпот 3 раза", "need_jackpot": 3},
    "fortune": {"name": "🎡 ФОРТУНА", "desc": "Выиграть x100 на колесе", "need_fortune": 100}
}

# ========== ДОСТИЖЕНИЯ ==========
achievements_data = {
    "first_game": {"name": "🎮 ПЕРВАЯ ИГРА", "desc": "Сыграть первую игру", "reward": 5000, "need_games": 1},
    "winner_10": {"name": "🏆 ПОБЕДИТЕЛЬ", "desc": "Выиграть 10 раз", "reward": 10000, "need_wins": 10},
    "winner_100": {"name": "🏆 ЛЕГЕНДА", "desc": "Выиграть 100 раз", "reward": 50000, "need_wins": 100},
    "millionaire": {"name": "💰 МИЛЛИОНЕР", "desc": "Накопить 1 000 000 GOLD", "reward": 100000, "need_balance": 1000000},
    "gambler": {"name": "🎲 АЗАРТНЫЙ", "desc": "Сыграть 100 игр", "reward": 50000, "need_games": 100},
    "gambler_500": {"name": "🎲 ПРОФЕССИОНАЛ", "desc": "Сыграть 500 игр", "reward": 150000, "need_games": 500},
    "streak_3": {"name": "🔥 СТРИКЕР", "desc": "Выиграть 3 раза подряд", "reward": 30000, "need_streak": 3},
    "streak_5": {"name": "🔥 МАСТЕР СТРИКА", "desc": "Выиграть 5 раз подряд", "reward": 75000, "need_streak": 5},
    "streak_10": {"name": "🔥 БОГ СТРИКА", "desc": "Выиграть 10 раз подряд", "reward": 200000, "need_streak": 10},
    "sapper": {"name": "💣 САПЁР", "desc": "Выиграть в минах 10 раз", "reward": 50000, "need_mines_wins": 10},
    "carder": {"name": "🃏 КАРТЁЖНИК", "desc": "Выиграть в блэкджек 25 раз", "reward": 50000, "need_bj_wins": 25},
    "slot_winner": {"name": "🎰 СЛОТ-МАСТЕР", "desc": "Выиграть джекпот в слотах", "reward": 50000, "need_jackpot": 1},
    "fortune": {"name": "🍀 ВЕЗУНЧИК", "desc": "Выиграть x50+ на колесе", "reward": 50000, "need_fortune": 50},
    "lottery": {"name": "🍀 ЛОТЕРЕЙЩИК", "desc": "Выиграть в лотерее", "reward": 50000, "need_lottery": 1},
    "sport": {"name": "⚽ СПОРТСМЕН", "desc": "Выиграть спортивную ставку", "reward": 25000, "need_sport": 1},
    "rps": {"name": "✊ КНБ МАСТЕР", "desc": "Выиграть в КНБ 10 раз", "reward": 50000, "need_rps": 10}
}

# ========== СПОРТИВНЫЕ СТАВКИ ==========
SPORTS_EVENTS = [
    {"name": "⚽ Реал Мадрид - Барселона", "coef1": 2.5, "coef2": 2.8, "coefX": 3.2},
    {"name": "🏀 Лейкерс - Голден Стэйт", "coef1": 2.2, "coef2": 2.5, "coefX": 3.0},
    {"name": "🎾 Джокович - Надаль", "coef1": 1.8, "coef2": 2.2, "coefX": 3.5},
    {"name": "🏒 ЦСКА - СКА", "coef1": 2.3, "coef2": 2.4, "coefX": 3.1},
    {"name": "🏈 Челси - Манчестер Сити", "coef1": 3.0, "coef2": 2.1, "coefX": 3.3}
]

# ========== КНБ ==========
RPS_CHOICES = {"камень": "✊", "ножницы": "✌️", "бумага": "✋"}
RPS_WIN = {"камень": "ножницы", "ножницы": "бумага", "бумага": "камень"}

# ========== НОВЫЕ ИГРЫ ==========
def play_bowling():
    return random.randint(0, 10)

BOX_REWARDS = {1: 5, 2: 2, 3: 0.5}
def choose_box(box_num):
    return BOX_REWARDS.get(box_num, 0)

def throw_dart():
    r = random.randint(1, 100)
    if r <= 5:
        return "bullseye"
    elif r <= 20:
        return "inner"
    elif r <= 50:
        return "outer"
    else:
        return "miss"

DART_MULT = {"bullseye": 10, "inner": 5, "outer": 2, "miss": 0}

def shoot_ball():
    r = random.randint(1, 100)
    if r <= 10:
        return "three_point"
    elif r <= 30:
        return "two_point"
    elif r <= 60:
        return "free_throw"
    else:
        return "miss"

BASKET_MULT = {"three_point": 3, "two_point": 2, "free_throw": 1, "miss": 0}

# ========== РЕФЕРАЛЬНАЯ СИСТЕМА ==========
REFERRAL_REWARD = 30000

def generate_referral_link(uid):
    return f"https://t.me/Golden_Gram_Roulette_Bot?start=ref{uid}"

def process_referral(new_uid, referrer_uid):
    if new_uid not in user_referrer and new_uid != referrer_uid:
        user_referrer[new_uid] = referrer_uid
        user_referrals[referrer_uid] = user_referrals.get(referrer_uid, 0) + 1
        user_balances[referrer_uid] = user_balances.get(referrer_uid, 0) + REFERRAL_REWARD
        return True
    return False

# ========== ПРОМОКОДЫ ==========
PROMOCODES = {
    "Gold2026": {"reward": 100000, "used": set()}
}

def use_promocode(uid, code):
    if code in PROMOCODES:
        if uid in PROMOCODES[code]["used"]:
            return None, "already_used"
        PROMOCODES[code]["used"].add(uid)
        return PROMOCODES[code]["reward"], "success"
    return None, "invalid"

# ========== ОСНОВНЫЕ ФУНКЦИИ ==========
def format_amount(a):
    return f"{a:,}".replace(",", " ")

def get_level(e):
    if e < 10: return 1
    elif e < 30: return 2
    elif e < 60: return 3
    elif e < 100: return 4
    else: return 5

def get_rank(balance):
    for i in range(len(RANKS)-1, -1, -1):
        if balance >= RANKS[i]["need"]:
            return RANKS[i]
    return RANKS[0]

def check_rank_up(uid, old_balance, new_balance):
    old_rank = get_rank(old_balance)
    new_rank = get_rank(new_balance)
    if old_rank["name"] != new_rank["name"]:
        user_balances[uid] = user_balances.get(uid, 0) + new_rank["reward"]
        return new_rank
    return None

def get_prestige_level(level):
    for i in range(len(PRESTIGE_LEVELS)-1, -1, -1):
        if level >= PRESTIGE_LEVELS[i]["need_level"]:
            return PRESTIGE_LEVELS[i]
    return PRESTIGE_LEVELS[0]

def can_prestige(uid):
    level = user_levels.get(uid, 0)
    current_prestige = user_prestige.get(uid, 0)
    if current_prestige >= len(PRESTIGE_LEVELS):
        return False, "❌ Ты достиг максимального престижа!"
    next_prestige = PRESTIGE_LEVELS[current_prestige]
    if level >= next_prestige["need_level"]:
        return True, next_prestige
    return False, f"📊 Нужно {next_prestige['need_level']} уровень"

def do_prestige(uid):
    if uid not in user_prestige:
        user_prestige[uid] = 0
    current = user_prestige[uid]
    if current >= len(PRESTIGE_LEVELS):
        return None
    next_p = PRESTIGE_LEVELS[current]
    if user_levels.get(uid, 0) >= next_p["need_level"]:
        user_prestige[uid] = current + 1
        reward = next_p["reward"]
        user_balances[uid] = user_balances.get(uid, 0) + reward
        user_levels[uid] = 0
        return next_p
    return None

def get_sport_event():
    return random.choice(SPORTS_EVENTS)

def rps_result(player, bot):
    if player == bot:
        return "draw"
    elif RPS_WIN[player] == bot:
        return "win"
    else:
        return "lose"

# ========== ЗАГРУЗКА/СОХРАНЕНИЕ ==========
def load_data():
    global user_balances,user_stats,user_levels,daily_streak,game_history,daily_quests,last_quest_reset,user_achievements,user_prestige,user_titles,user_active_title,user_badges,user_lottery_tickets,last_lottery_time,lottery_pool,user_referrals,user_referrer,used_promocodes
    try:
        with open(DATA_FILE,"r")as f:
            d=json.load(f)
            user_balances=d.get("user_balances",{})
            user_stats=d.get("user_stats",{})
            user_levels=d.get("user_levels",{})
            daily_streak=d.get("daily_streak",{})
            game_history=d.get("game_history",[])
            daily_quests=d.get("daily_quests",{})
            last_quest_reset=d.get("last_quest_reset",int(time.time()))
            user_achievements=d.get("user_achievements",{})
            user_prestige=d.get("user_prestige",{})
            user_titles=d.get("user_titles",{})
            user_active_title=d.get("user_active_title",{})
            user_badges=d.get("user_badges",{})
            user_lottery_tickets=d.get("user_lottery_tickets",{})
            last_lottery_time=d.get("last_lottery_time",int(time.time()))
            lottery_pool=d.get("lottery_pool",0)
            user_referrals=d.get("user_referrals",{})
            user_referrer=d.get("user_referrer",{})
            if "Gold2026" in PROMOCODES:
                used_set = d.get("used_promocodes", {})
                PROMOCODES["Gold2026"]["used"] = set(used_set) if isinstance(used_set, list) else set()
    except:
        pass

def save_data():
    with open(DATA_FILE,"w")as f:
        used_list = list(PROMOCODES["Gold2026"]["used"]) if "Gold2026" in PROMOCODES else []
        json.dump({
            "user_balances":user_balances,
            "user_stats":user_stats,
            "user_levels":user_levels,
            "daily_streak":daily_streak,
            "game_history":game_history[-50:],
            "daily_quests":daily_quests,
            "last_quest_reset":last_quest_reset,
            "user_achievements":user_achievements,
            "user_prestige":user_prestige,
            "user_titles":user_titles,
            "user_active_title":user_active_title,
            "user_badges":user_badges,
            "user_lottery_tickets":user_lottery_tickets,
            "last_lottery_time":last_lottery_time,
            "lottery_pool":lottery_pool,
            "user_referrals":user_referrals,
            "user_referrer":user_referrer,
            "used_promocodes":used_list
        },f,ensure_ascii=False,indent=2)

# ========== ПРОВЕРКИ АЧИВОК, ЗНАЧКОВ, ТИТУЛОВ ==========
def check_achievements(uid):
    if uid not in user_achievements:
        user_achievements[uid] = []
    stats = user_stats.get(uid, {"played":0,"won":0,"total_bet":0,"total_win":0,"mines_wins":0,"bj_wins":0,"slot_jackpot":0,"max_fortune":0,"lottery_win":0,"sport_wins":0,"rps_wins":0})
    current_streak = daily_quests["win_3_streak"]["current_streak"].get(uid, 0) if "win_3_streak" in daily_quests else 0
    balance = user_balances.get(uid, 0)
    new_achievements = []
    for aid, ach in achievements_data.items():
        if aid in user_achievements[uid]:
            continue
        earned = False
        if "need_balance" in ach and balance >= ach["need_balance"]:
            earned = True
        elif "need_games" in ach and stats.get("played",0) >= ach["need_games"]:
            earned = True
        elif "need_wins" in ach and stats.get("won",0) >= ach["need_wins"]:
            earned = True
        elif "need_mines_wins" in ach and stats.get("mines_wins",0) >= ach["need_mines_wins"]:
            earned = True
        elif "need_bj_wins" in ach and stats.get("bj_wins",0) >= ach["need_bj_wins"]:
            earned = True
        elif "need_streak" in ach and current_streak >= ach["need_streak"]:
            earned = True
        elif "need_jackpot" in ach and stats.get("slot_jackpot",0) >= ach["need_jackpot"]:
            earned = True
        elif "need_fortune" in ach and stats.get("max_fortune",0) >= ach["need_fortune"]:
            earned = True
        elif "need_lottery" in ach and stats.get("lottery_win",0) >= ach["need_lottery"]:
            earned = True
        elif "need_sport" in ach and stats.get("sport_wins",0) >= ach["need_sport"]:
            earned = True
        elif "need_rps" in ach and stats.get("rps_wins",0) >= ach["need_rps"]:
            earned = True
        if earned:
            user_achievements[uid].append(aid)
            user_balances[uid] = user_balances.get(uid, 0) + ach["reward"]
            new_achievements.append(ach)
            save_data()
    return new_achievements

def check_badges(uid):
    if uid not in user_badges:
        user_badges[uid] = []
    stats = user_stats.get(uid, {"played":0,"won":0,"total_bet":0,"total_win":0,"mines_wins":0,"bj_wins":0,"slot_jackpot":0,"max_fortune":0,"lottery_win":0,"sport_wins":0,"rps_wins":0,"bowling_strike":0,"dart_bullseye":0,"basketball_three":0})
    current_streak = daily_quests["win_3_streak"]["current_streak"].get(uid, 0) if "win_3_streak" in daily_quests else 0
    balance = user_balances.get(uid, 0)
    referrals = user_referrals.get(uid, 0)
    new_badges = []
    for bid, badge in BADGES.items():
        if bid in user_badges[uid]:
            continue
        earned = False
        if bid == "beginner" and stats.get("played",0) >= 1:
            earned = True
        elif bid == "winner" and stats.get("won",0) >= 10:
            earned = True
        elif bid == "expert" and stats.get("won",0) >= 100:
            earned = True
        elif bid == "millionaire" and balance >= 1000000:
            earned = True
        elif bid == "billionaire" and balance >= 1000000000:
            earned = True
        elif bid == "lucky" and current_streak >= 3:
            earned = True
        elif bid == "gambler" and stats.get("played",0) >= 500:
            earned = True
        elif bid == "slot_king" and stats.get("slot_jackpot",0) >= 1:
            earned = True
        elif bid == "card_master" and stats.get("bj_wins",0) >= 50:
            earned = True
        elif bid == "sapper" and stats.get("mines_wins",0) >= 25:
            earned = True
        elif bid == "fortune" and stats.get("max_fortune",0) >= 100:
            earned = True
        elif bid == "lottery" and stats.get("lottery_win",0) >= 1:
            earned = True
        elif bid == "sport" and stats.get("sport_wins",0) >= 1:
            earned = True
        elif bid == "rps" and stats.get("rps_wins",0) >= 10:
            earned = True
        elif bid == "streak10" and current_streak >= 10:
            earned = True
        elif bid == "bowler" and stats.get("bowling_strike",0) >= 1:
            earned = True
        elif bid == "dart_master" and stats.get("dart_bullseye",0) >= 1:
            earned = True
        elif bid == "basketball_star" and stats.get("basketball_three",0) >= 1:
            earned = True
        elif bid == "referrer" and referrals >= 10:
            earned = True
        if earned:
            user_badges[uid].append(bid)
            user_balances[uid] = user_balances.get(uid, 0) + 50000
            new_badges.append(badge)
            save_data()
    return new_badges

def check_titles(uid):
    if uid not in user_titles:
        user_titles[uid] = []
    stats = user_stats.get(uid, {"played":0,"won":0,"total_bet":0,"total_win":0,"mines_wins":0,"bj_wins":0,"slot_jackpot":0,"max_fortune":0})
    current_streak = daily_quests["win_3_streak"]["current_streak"].get(uid, 0) if "win_3_streak" in daily_quests else 0
    balance = user_balances.get(uid, 0)
    new_titles = []
    for tid, t in TITLES.items():
        if tid in user_titles[uid]:
            continue
        earned = False
        if "need_balance" in t and balance >= t["need_balance"]:
            earned = True
        elif "need_games" in t and stats.get("played",0) >= t["need_games"]:
            earned = True
        elif "need_wins" in t and stats.get("won",0) >= t["need_wins"]:
            earned = True
        elif "need_mines_wins" in t and stats.get("mines_wins",0) >= t["need_mines_wins"]:
            earned = True
        elif "need_bj_wins" in t and stats.get("bj_wins",0) >= t["need_bj_wins"]:
            earned = True
        elif "need_streak" in t and current_streak >= t["need_streak"]:
            earned = True
        elif "need_jackpot" in t and stats.get("slot_jackpot",0) >= t["need_jackpot"]:
            earned = True
        elif "need_fortune" in t and stats.get("max_fortune",0) >= t["need_fortune"]:
            earned = True
        if earned:
            user_titles[uid].append(tid)
            new_titles.append(t)
            save_data()
    return new_titles

def get_achievements_list(uid):
    if uid not in user_achievements:
        user_achievements[uid] = []
    lines = ["🏆 <b>ДОСТИЖЕНИЯ</b>\n"]
    items = list(achievements_data.items())
    for i, (aid, ach) in enumerate(items):
        prefix = "└" if i == len(items) - 1 else "├"
        if aid in user_achievements[uid]:
            lines.append(f"{prefix} ✅ {ach['name']} (+{format_amount(ach['reward'])})")
        else:
            lines.append(f"{prefix} ❌ {ach['name']}")
    return "\n".join(lines)

def get_badges_list(uid):
    if uid not in user_badges:
        user_badges[uid] = []
    lines = ["🎖️ <b>ЗНАЧКИ</b>\n"]
    items = list(BADGES.items())
    for i, (bid, badge) in enumerate(items):
        prefix = "└" if i == len(items) - 1 else "├"
        if bid in user_badges[uid]:
            lines.append(f"{prefix} ✅ {badge['name']}")
        else:
            lines.append(f"{prefix} ❌ {badge['name']}")
    return "\n".join(lines)

def get_titles_list(uid):
    if uid not in user_titles:
        user_titles[uid] = []
    lines = ["🏅 <b>ТИТУЛЫ</b>\n"]
    items = list(TITLES.items())
    for i, (tid, t) in enumerate(items):
        prefix = "└" if i == len(items) - 1 else "├"
        if tid in user_titles[uid]:
            lines.append(f"{prefix} ✅ {t['name']}")
        else:
            lines.append(f"{prefix} ❌ {t['name']}")
    lines.append(f"└ 📌 Активный: {user_active_title.get(uid, 'Не выбран')}")
    return "\n".join(lines)

# ========== ЗАДАНИЯ ==========
def init_quests():
    global daily_quests
    if not daily_quests:
        daily_quests={
            "play_3_games":{"name":"🎲 Сыграть 3 игры","target":3,"reward":30000,"progress":{},"completed":{}},
            "play_10_games":{"name":"🎲 Сыграть 10 игр","target":10,"reward":100000,"progress":{},"completed":{}},
            "win_3_streak":{"name":"🏆 Выиграть 3 раза подряд","target":3,"reward":25000,"progress":{},"completed":{},"current_streak":{}},
            "win_5_streak":{"name":"🏆 Выиграть 5 раз подряд","target":5,"reward":75000,"progress":{},"completed":{},"current_streak":{}},
            "make_bet":{"name":"💰 Сделать любую ставку","target":1,"reward":10000,"progress":{},"completed":{}},
            "make_5_bets":{"name":"💰 Сделать 5 ставок","target":5,"reward":50000,"progress":{},"completed":{}},
            "win_slot":{"name":"🎰 Выиграть в слоте","target":1,"reward":20000,"progress":{},"completed":{}},
            "win_dice":{"name":"🎲 Выиграть в кости","target":1,"reward":15000,"progress":{},"completed":{}},
            "win_wheel":{"name":"🎡 Выиграть на колесе","target":1,"reward":20000,"progress":{},"completed":{}},
            "win_blackjack":{"name":"🃏 Выиграть в блэкджек","target":1,"reward":25000,"progress":{},"completed":{}},
            "win_mines":{"name":"💣 Выиграть в минах","target":1,"reward":30000,"progress":{},"completed":{}},
            "earn_100k":{"name":"💰 Заработать 100 000 GOLD","target":100000,"reward":50000,"progress":{},"completed":{},"current_earn":{}}
        }

def check_quests_reset():
    global last_quest_reset
    if int(time.time())-last_quest_reset>=86400:
        for q in daily_quests:
            daily_quests[q]["progress"]={}
            daily_quests[q]["completed"]={}
            if q in ["win_3_streak","win_5_streak"]:
                daily_quests[q]["current_streak"]={}
            if q=="earn_100k":
                daily_quests[q]["current_earn"]={}
        last_quest_reset=int(time.time())
        save_data()
        return True
    return False

def update_quest_progress(uid,qid,inc=1):
    global user_balances
    check_quests_reset()
    if qid not in daily_quests or uid in daily_quests[qid].get("completed",{}):
        return 0
    curr=daily_quests[qid]["progress"].get(uid,0)
    new=min(curr+inc,daily_quests[qid]["target"])
    daily_quests[qid]["progress"][uid]=new
    if new>=daily_quests[qid]["target"] and uid not in daily_quests[qid]["completed"]:
        rew=daily_quests[qid]["reward"]
        user_balances[uid]=user_balances.get(uid,0)+rew
        daily_quests[qid]["completed"][uid]=True
        save_data()
        return rew
    save_data()
    return 0

def update_quest_earn(uid, amount):
    if "earn_100k" not in daily_quests or uid in daily_quests["earn_100k"].get("completed",{}):
        return 0
    curr=daily_quests["earn_100k"]["current_earn"].get(uid,0)
    new=curr+amount
    daily_quests["earn_100k"]["current_earn"][uid]=new
    daily_quests["earn_100k"]["progress"][uid]=new
    if new>=daily_quests["earn_100k"]["target"] and uid not in daily_quests["earn_100k"]["completed"]:
        rew=daily_quests["earn_100k"]["reward"]
        user_balances[uid]=user_balances.get(uid,0)+rew
        daily_quests["earn_100k"]["completed"][uid]=True
        save_data()
        return rew
    save_data()
    return 0

def get_quests_status(uid):
    check_quests_reset()
    lines=[]
    for qid,q in daily_quests.items():
        prog=q["progress"].get(uid,0)
        if qid=="earn_100k":
            prog=q["current_earn"].get(uid,0)
        if uid in q.get("completed",{}):
            lines.append(f"\n  └ {q['name']}: ✅ ВЫПОЛНЕНО (+{format_amount(q['reward'])} GOLD)")
        else:
            lines.append(f"\n  └ {q['name']}: 📊 {prog}/{q['target']}")
    return "\n".join(lines)

# ========== КЛАВИАТУРЫ С ТРЕМЯ СТРАНИЦАМИ И КНОПКОЙ НАЗАД ==========
def get_main_keyboard_page1():
    kb=InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("💰 Баланс",callback_data="menu_balance"),
        InlineKeyboardButton("📊 Профиль",callback_data="menu_profile"),
        InlineKeyboardButton("🎲 Рулетка",callback_data="menu_roulette"),
        InlineKeyboardButton("🎲 Кости",callback_data="menu_dice"),
        InlineKeyboardButton("🎰 Слот",callback_data="menu_slot"),
        InlineKeyboardButton("🎡 Колесо",callback_data="menu_wheel"),
        InlineKeyboardButton("➡️ ДАЛЕЕ",callback_data="menu_page2")
    )
    return kb

def get_main_keyboard_page2():
    kb=InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✊ КНБ",callback_data="menu_rps"),
        InlineKeyboardButton("⚽ Спорт",callback_data="menu_sport"),
        InlineKeyboardButton("🎫 Лотерея",callback_data="menu_lottery"),
        InlineKeyboardButton("🎳 Боулинг",callback_data="menu_bowling"),
        InlineKeyboardButton("🎯 Дартс",callback_data="menu_darts"),
        InlineKeyboardButton("🏀 Баскетбол",callback_data="menu_basketball"),
        InlineKeyboardButton("📦 Коробки",callback_data="menu_boxes"),
        InlineKeyboardButton("👥 Рефералы",callback_data="menu_referral"),
        InlineKeyboardButton("🎫 Промокод",callback_data="menu_promo"),
        InlineKeyboardButton("⬅️ НАЗАД",callback_data="menu_page1"),
        InlineKeyboardButton("➡️ ДАЛЕЕ",callback_data="menu_page3")
    )
    return kb

def get_main_keyboard_page3():
    kb=InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("💣 Мины",callback_data="menu_mines"),
        InlineKeyboardButton("🃏 Блэкджек",callback_data="menu_blackjack"),
        InlineKeyboardButton("🎁 Задания",callback_data="menu_quests"),
        InlineKeyboardButton("🏆 Топ",callback_data="menu_top"),
        InlineKeyboardButton("🏅 Достижения",callback_data="menu_achievements"),
        InlineKeyboardButton("🎖️ Значки",callback_data="menu_badges"),
        InlineKeyboardButton("🏅 Титулы",callback_data="menu_titles"),
        InlineKeyboardButton("📊 Прогресс",callback_data="menu_progress"),
        InlineKeyboardButton("🌟 Престиж",callback_data="menu_prestige"),
        InlineKeyboardButton("❓ Помощь",callback_data="menu_help"),
        InlineKeyboardButton("⬅️ НАЗАД",callback_data="menu_page2")
    )
    return kb
# ========== ИГРЫ ==========
SUITS=["♠","♥","♦","♣"]
RANKS_CARDS=["2","3","4","5","6","7","8","9","10","J","Q","K","A"]

def spin_roulette():
    n=random.randint(0,36)
    if n==0:return n,"🟢","ЗЕЛЁНОЕ"
    elif n in[1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]:return n,"🔴","КРАСНОЕ"
    else:return n,"⚫","ЧЁРНОЕ"

def normalize_bet(bet):
    b=bet.lower().strip()
    if b in["к","красное","красный","red","🔴"]:return"красное"
    if b in["ч","чёрное","черное","чёрный","черный","black","⚫"]:return"чёрное"
    if b in["чёт","чет","чётное","четное","even"]:return"чётное"
    if b in["неч","нечётное","нечетное","odd"]:return"нечётное"
    if b in["0","зеро","zero","🟢"]:return"0"
    if b in["1-я","1я","первая","первый"]:return"1-я"
    if b in["2-я","2я","вторая","второй"]:return"2-я"
    if b in["3-я","3я","третья","третий"]:return"3-я"
    return b

def check_win(bet,num,color):
    b=normalize_bet(bet)
    if b=="красное" and color=="КРАСНОЕ":return True
    if b=="чёрное" and color=="ЧЁРНОЕ":return True
    if b=="чётное" and num!=0 and num%2==0:return True
    if b=="нечётное" and num%2==1:return True
    if b=="0" and num==0:return True
    if b=="1-12" and 1<=num<=12:return True
    if b=="13-24" and 13<=num<=24:return True
    if b=="25-36" and 25<=num<=36:return True
    if b=="1-я" and num!=0 and num%3==1:return True
    if b=="2-я" and num!=0 and num%3==2:return True
    if b=="3-я" and num!=0 and num%3==0:return True
    if b.isdigit():return int(b)==num
    if "-"in b:
        try:
            p=b.split("-")
            if len(p)==2:
                s,e=int(p[0]),int(p[1])
                if s>e:s,e=e,s
                return s<=num<=e
        except:pass
    return False

def get_multiplier(bet):
    b=normalize_bet(bet)
    if b in["красное","чёрное","чётное","нечётное"]:return 2
    if b=="0" or b.isdigit():return 36
    if b in["1-12","13-24","25-36","1-я","2-я","3-я"]:return 3
    if "-"in b:
        try:
            p=b.split("-")
            if len(p)==2:
                s,e=int(p[0]),int(p[1])
                if s>e:s,e=e,s
                cnt=e-s+1
                if cnt==2:return 18
                if cnt==3:return 12
                if cnt==4:return 9
                if cnt==6:return 6
                if cnt==8:return 4
                if cnt==12:return 3
                if cnt==18:return 2
                return 36//cnt if cnt>0 else 2
        except:pass
    return 2

# ========== КОСТИ ==========
VALID_DICE_BETS = ["2","3","4","5","6","7","8","9","10","11","12","дубль","чёт","нечёт","больше","меньше"]

def roll_dice():
    return random.randint(1,6), random.randint(1,6)

def get_dice_multiplier(bet_type, d1, d2):
    total = d1 + d2
    if bet_type == "дубль":
        return 10 if d1 == d2 else 0
    elif bet_type == "чёт":
        return 2 if total % 2 == 0 else 0
    elif bet_type == "нечёт":
        return 2 if total % 2 == 1 else 0
    elif bet_type == "больше":
        return 2 if total > 7 else 0
    elif bet_type == "меньше":
        return 2 if total < 7 else 0
    elif bet_type.isdigit():
        return 8 if total == int(bet_type) else 0
    return 0

def format_dice(d1, d2):
    dice_faces = {1:"⚀",2:"⚁",3:"⚂",4:"⚃",5:"⚄",6:"⚅"}
    return f"{dice_faces[d1]} {dice_faces[d2]}"

# ========== СЛОТ ==========
SLOT_SYMBOLS = ["🍒","🍋","🍊","🔔","💎","7️⃣"]
SLOT_PAYOUTS = {("💎","💎","💎"):100,("7️⃣","7️⃣","7️⃣"):50,("🔔","🔔","🔔"):20,("🍒","🍒","🍒"):10,("🍋","🍋","🍋"):8,("🍊","🍊","🍊"):8}

def spin_slot():
    return [random.choice(SLOT_SYMBOLS) for _ in range(3)]

def get_slot_win(symbols):
    return SLOT_PAYOUTS.get(tuple(symbols),0)

def format_slot(symbols):
    return " | ".join(symbols)

# ========== КОЛЕСО ==========
FORTUNE_WHEEL = [
    {"name": "💀 ПРОИГРЫШ", "mult": 0, "prob": 20},
    {"name": "💰 x2", "mult": 2, "prob": 25},
    {"name": "💰 x3", "mult": 3, "prob": 20},
    {"name": "💰 x5", "mult": 5, "prob": 15},
    {"name": "💰 x10", "mult": 10, "prob": 10},
    {"name": "💰 x20", "mult": 20, "prob": 5},
    {"name": "💰 x50", "mult": 50, "prob": 3},
    {"name": "💰 x100", "mult": 100, "prob": 2},
]

def spin_wheel():
    r=random.randint(1,100)
    c=0
    for s in FORTUNE_WHEEL:
        c+=s["prob"]
        if r<=c:
            return s
    return FORTUNE_WHEEL[0]

# ========== МИНЫ ==========
def generate_mines_field():
    f=[["⭐" for _ in range(5)] for _ in range(5)]
    for m in random.sample(range(25),3):
        f[m//5][m%5]="💣"
    return f

def format_mines_field(field,revealed):
    return "\n".join(" ".join(field[i][j] if(i,j)in revealed else"❓"for j in range(5))for i in range(5))

def get_mines_keyboard(field,revealed):
    kb=InlineKeyboardMarkup(row_width=5)
    for i in range(5):
        row=[]
        for j in range(5):
            if(i,j)in revealed:
                row.append(InlineKeyboardButton(field[i][j],callback_data="done"))
            else:
                row.append(InlineKeyboardButton("❓",callback_data=f"m_{i}_{j}"))
        kb.row(*row)
    if revealed:
        kb.add(InlineKeyboardButton("💰 Забрать выигрыш",callback_data="cash"))
    return kb

# ========== БЛЭКДЖЕК ==========
def generate_deck():
    deck=[(r,s) for r in RANKS_CARDS for s in SUITS]
    random.shuffle(deck)
    return deck

def card_value(card):
    r=card[0]
    if r in["J","Q","K"]:return 10
    if r=="A":return 11
    return int(r)

def hand_value(hand):
    v=sum(card_value(c)for c in hand)
    aces=sum(1 for c in hand if c[0]=="A")
    while v>21 and aces>0:
        v-=10
        aces-=1
    return v

def format_cards(hand):
    return " ".join(f"{r}{s}"for r,s in hand)if hand else"пусто"

# ========== УВЕДОМЛЕНИЯ ==========
async def send_quest_notify(uid,qid,reward,msg=None):
    name=daily_quests[qid]["name"]
    text=f"🎉 <b>ЗАДАНИЕ ВЫПОЛНЕНО!</b> 🎉\n\n📋 {name}\n💰 Награда: +{format_amount(reward)} GOLD\n\n💳 Баланс: {format_amount(user_balances.get(uid,0))} GOLD"
    try:
        if msg:
            await msg.reply(text,parse_mode="HTML")
        else:
            await bot.send_message(uid,text,parse_mode="HTML")
    except:
        pass

async def send_achievement_notify(uid,ach,msg=None):
    text=f"🏆 <b>ДОСТИЖЕНИЕ ПОЛУЧЕНО!</b> 🏆\n\n{ach['name']}\n{ach['desc']}\n\n💰 Награда: +{format_amount(ach['reward'])} GOLD"
    try:
        if msg:
            await msg.reply(text,parse_mode="HTML")
        else:
            await bot.send_message(uid,text,parse_mode="HTML")
    except:
        pass

async def send_badge_notify(uid,badge,msg=None):
    text=f"🎖️ <b>НОВЫЙ ЗНАЧОК!</b> 🎖️\n\n{badge['icon']} {badge['name']}\n{badge['desc']}\n\n💰 Награда: +50 000 GOLD"
    try:
        if msg:
            await msg.reply(text,parse_mode="HTML")
        else:
            await bot.send_message(uid,text,parse_mode="HTML")
    except:
        pass

async def send_title_notify(uid,title,msg=None):
    text=f"🏅 <b>НОВЫЙ ТИТУЛ!</b> 🏅\n\n{title['name']}\n{title['desc']}"
    try:
        if msg:
            await msg.reply(text,parse_mode="HTML")
        else:
            await bot.send_message(uid,text,parse_mode="HTML")
    except:
        pass

async def send_rank_up_notify(uid,rank,msg=None):
    text=f"⭐ <b>НОВОЕ ЗВАНИЕ!</b> ⭐\n\n{rank['name']}\n\n💰 Бонус: +{format_amount(rank['reward'])} GOLD"
    try:
        if msg:
            await msg.reply(text,parse_mode="HTML")
        else:
            await bot.send_message(uid,text,parse_mode="HTML")
    except:
        pass

async def send_prestige_notify(uid,prestige,msg=None):
    text=f"🌟 <b>НОВЫЙ ПРЕСТИЖ!</b> 🌟\n\n{prestige['name']}\n\n💰 Бонус: +{format_amount(prestige['reward'])} GOLD\n📈 Уровень сброшен до 0"
    try:
        if msg:
            await msg.reply(text,parse_mode="HTML")
        else:
            await bot.send_message(uid,text,parse_mode="HTML")
    except:
        pass

def force_reset_game():
    global game_in_progress,pending_bets
    game_in_progress=False
    pending_bets.clear()

# ========== ОБРАБОТЧИКИ ==========
@dp.message_handler(commands=["start"])
async def start_cmd(m):
    init_quests()
    force_reset_game()
    
    args = m.get_args()
    if args and args.startswith("ref"):
        try:
            referrer_id = int(args[3:])
            if process_referral(m.from_user.id, referrer_id):
                await m.reply(f"✅ Ты был приглашён! Реферер получил +{format_amount(REFERRAL_REWARD)} GOLD")
        except:
            pass
    
    await m.reply(
        "<code>👑 GOLDEN GOLD ROULETTE\n\n"
        "🎲 ИГРЫ:\n├ Рулетка: 100 чёрное\n├ Кости: кости 500 на 7\n├ Слот: слот 100\n├ Колесо: колесо 100\n├ КНБ: кнб 500 камень\n├ Спорт: спорт 500 1\n├ Лотерея: лотерея 1000\n├ Мины: мины 100\n├ Блэкджек: bj 100\n├ Боулинг: боулинг 100\n├ Коробки: коробки 100 1\n├ Дартс: дартс 100\n├ Баскетбол: баскетбол 100\n\n"
        "📌 КОМАНДЫ:\n├ б - баланс\n├ профиль - статистика\n├ топ - топ игроков\n├ достижения - список достижений\n├ значки - список значков\n├ титулы - список титулов\n├ прогресс - прогресс\n├ престиж - престиж\n├ ранг - звание\n├ бонус - бонус\n├ задания - задания\n├ рефка - реферальная ссылка\n├ промокод Gold2026 - 100 000 GOLD\n├ го - запуск рулетки\n├ отмена - отмена ставок\n├ дать 500 (ответом)\n└ дать всё (ответом)</code>",
        parse_mode="HTML",
        reply_markup=get_main_keyboard_page1()
    )

@dp.message_handler(commands=["add_grams"])
async def add_grams(m):
    if m.from_user.id!=ADMIN_ID:
        return await m.reply("❌ Нет прав")
    try:
        amt=int(m.text.split()[1])
        user_balances[ADMIN_ID]=user_balances.get(ADMIN_ID,0)+amt
        save_data()
        await m.reply(f"✅ +{format_amount(amt)} GOLD")
    except:
        await m.reply("❌ /add_grams 5000")

# ========== МЕНЮ ==========
@dp.callback_query_handler(lambda c:c.data.startswith("menu_"))
async def menu_cb(call):
    await call.answer()
    uid=call.from_user.id
    act=call.data[5:]
    
    if act=="page1":
        try:
            await call.message.edit_reply_markup(reply_markup=get_main_keyboard_page1())
        except:
            pass
        return
    if act=="page2":
        try:
            await call.message.edit_reply_markup(reply_markup=get_main_keyboard_page2())
        except:
            pass
        return
    if act=="page3":
        try:
            await call.message.edit_reply_markup(reply_markup=get_main_keyboard_page3())
        except:
            pass
        return
    
    if act=="balance":
        text = f"💰 <b>Ваш баланс</b>\n\n└ {format_amount(user_balances.get(uid,0))} GOLD"
        reply_markup = get_main_keyboard_page1()
    elif act=="profile":
        name=call.from_user.full_name
        bal=user_balances.get(uid,0)
        s=user_stats.get(uid,{"played":0,"won":0,"total_bet":0,"total_win":0})
        lvl=user_levels.get(uid,0)
        rank=get_rank(bal)
        prestige=user_prestige.get(uid,0)
        active_title=user_active_title.get(uid,"Не выбран")
        badges_count=len(user_badges.get(uid,[]))
        referrals=user_referrals.get(uid,0)
        wr=(s["won"]/s["played"]*100)if s["played"]>0 else 0
        prof=s["total_win"]-s["total_bet"]
        text = f"👤 <b>{name}</b>\n├ 🆔 {uid}\n├ 📊 Уровень: {lvl}\n├ 🎖️ Звание: {rank['name']}\n├ 🌟 Престиж: {prestige}\n├ 🎖️ Значки: {badges_count}\n├ 🏅 Титул: {active_title}\n├ 👥 Пригласил: {referrals}\n└ 💰 {format_amount(bal)} GOLD\n\n📊 <b>Статистика</b>\n├ 🎲 Игр: {s['played']}\n├ 🏆 Побед: {s['won']}\n├ 📈 Винрейт: {wr:.1f}%\n└ 📊 Профит: {format_amount(prof)} GOLD"
        reply_markup = get_main_keyboard_page1()
    elif act=="referral":
        link = generate_referral_link(uid)
        referrals = user_referrals.get(uid, 0)
        text = f"👥 <b>РЕФЕРАЛЬНАЯ СИСТЕМА</b>\n\n├ 👥 Приглашено: {referrals}\n├ 💰 Награда за друга: +{format_amount(REFERRAL_REWARD)} GOLD\n└ 🔗 Твоя ссылка:\n{link}"
        reply_markup = get_main_keyboard_page2()
    elif act=="promo":
        text = f"🎫 <b>ПРОМОКОДЫ</b>\n\n├ 🏷️ Gold2026 - 100 000 GOLD\n└ 📝 Введи: промокод Gold2026"
        reply_markup = get_main_keyboard_page2()
    elif act=="bowling":
        text = f"🎳 <b>БОУЛИНГ</b>\n\n├ Команда: боулинг 100\n├ Страйк (10 кегль) = x3\n├ Спэр (8-9) = x2\n└ Мимо (0-7) = x0.5"
        reply_markup = get_main_keyboard_page2()
    elif act=="darts":
        text = f"🎯 <b>ДАРТС</b>\n\n├ Команда: дартс 100\n├ Яблочко (5%) = x10\n├ Внутреннее кольцо (15%) = x5\n├ Внешнее кольцо (30%) = x2\n└ Мимо (50%) = x0"
        reply_markup = get_main_keyboard_page2()
    elif act=="basketball":
        text = f"🏀 <b>БАСКЕТБОЛ</b>\n\n├ Команда: баскетбол 100\n├ Трёхочковый (10%) = x3\n├ Двухочковый (20%) = x2\n├ Штрафной (30%) = x1\n└ Мимо (40%) = x0"
        reply_markup = get_main_keyboard_page2()
    elif act=="boxes":
        text = f"📦 <b>КОРОБКИ</b>\n\n├ Команда: коробки 100 1\n├ Коробка 1 = x5\n├ Коробка 2 = x2\n└ Коробка 3 = x0.5"
        reply_markup = get_main_keyboard_page2()
    elif act=="roulette":
        text = f"🎲 <b>СТАВКИ НА РУЛЕТКУ</b>\n\n├ 100 чёрное\n├ 250 красное\n├ 500 чётное\n├ 1000 14\n├ 2000 0\n└ 5000 1-12"
        reply_markup = get_main_keyboard_page1()
    elif act=="dice":
        text = f"🎲 <b>ИГРА КОСТИ</b>\n\n├ Команда: кости 500 на 7\n├ кости 500 на дубль\n├ кости 500 на чёт\n├ кости 500 на нечёт\n├ кости 500 на больше\n└ кости 500 на меньше"
        reply_markup = get_main_keyboard_page1()
    elif act=="slot":
        text = f"🎰 <b>СЛОТ-МАШИНА</b>\n\n├ Команда: слот 100\n├ 🍒🍒🍒 = x10\n├ 🍋🍋🍋 = x8\n├ 🍊🍊🍊 = x8\n├ 🔔🔔🔔 = x20\n├ 7️⃣7️⃣7️⃣ = x50\n└ 💎💎💎 = ДЖЕКПОТ x100"
        reply_markup = get_main_keyboard_page1()
    elif act=="wheel":
        text = f"🎡 <b>КОЛЕСО ФОРТУНЫ</b>\n\n├ Команда: колесо 100\n├ Множители от x0 до x100\n└ Удачи!"
        reply_markup = get_main_keyboard_page1()
    elif act=="rps":
        text = f"✊ <b>КАМЕНЬ-НОЖНИЦЫ-БУМАГА</b>\n\n├ Команда: кнб 500 камень\n├ кнб @username 500 камень\n└ Победа x2, ничья возврат"
        reply_markup = get_main_keyboard_page2()
    elif act=="sport":
        text = f"⚽ <b>СПОРТИВНЫЕ СТАВКИ</b>\n\n├ Команда: спорт 500 1\n├ 1 - победа хозяев\n├ X - ничья\n└ 2 - победа гостей"
        reply_markup = get_main_keyboard_page2()
    elif act=="lottery":
        text = f"🎫 <b>ЛОТЕРЕЯ</b>\n\n├ Команда: лотерея 1000\n├ Покупай билеты\n└ Розыгрыш каждый час!"
        reply_markup = get_main_keyboard_page2()
    elif act=="quests":
        text = f"🎯 <b>ЕЖЕДНЕВНЫЕ ЗАДАНИЯ</b>{get_quests_status(uid)}\n\n⏰ Обновляются каждые 24 часа\n✨ Награда выдается автоматически!"
        reply_markup = get_main_keyboard_page3()
    elif act=="achievements":
        text = get_achievements_list(uid)
        reply_markup = get_main_keyboard_page3()
    elif act=="badges":
        text = get_badges_list(uid)
        reply_markup = get_main_keyboard_page3()
    elif act=="titles":
        text = get_titles_list(uid)
        reply_markup = get_main_keyboard_page3()
    elif act=="progress":
        rank=get_rank(user_balances.get(uid,0))
        text = f"📊 <b>ПРОГРЕСС</b>\n\n🎖️ Звание: {rank['name']}\n🌟 Престиж: {user_prestige.get(uid,0)}\n📈 Уровень: {user_levels.get(uid,0)}\n💰 Баланс: {format_amount(user_balances.get(uid,0))} GOLD"
        reply_markup = get_main_keyboard_page3()
    elif act=="prestige":
        can, info = can_prestige(uid)
        if can:
            text = f"🌟 <b>ПРЕСТИЖ</b>\n\nТы готов к новому престижу!\n{info['name']}\n💰 Награда: +{format_amount(info['reward'])} GOLD\n\nНапиши /престиж для подтверждения"
        else:
            text = f"🌟 <b>ПРЕСТИЖ</b>\n\n{info}"
        reply_markup = get_main_keyboard_page3()
    elif act=="mines":
        text = f"💣 <b>ИГРА МИНЫ</b>\n\n├ Команда: мины 100\n├ Поле 5x5, 3 мины\n├ Каждая клетка +0.14x\n└ Максимум x4.0"
        reply_markup = get_main_keyboard_page3()
    elif act=="blackjack":
        text = f"🃏 <b>БЛЭКДЖЕК</b>\n\n├ Команда: bj 100\n├ Мин. ставка: 100\n├ Блэкджек: x2.5\n├ Победа: x2\n└ Сдача: 50%"
        reply_markup = get_main_keyboard_page3()
    elif act=="help":
        text = f"👑 <b>GOLDEN GOLD ROULETTE</b>\n\n🎲 ИГРЫ:\n├ Рулетка: 100 чёрное\n├ Кости: кости 500 на 7\n├ Слот: слот 100\n├ Колесо: колесо 100\n├ КНБ: кнб 500 камень\n├ Спорт: спорт 500 1\n├ Лотерея: лотерея 1000\n├ Мины: мины 100\n├ Блэкджек: bj 100\n├ Боулинг: боулинг 100\n├ Коробки: коробки 100 1\n├ Дартс: дартс 100\n├ Баскетбол: баскетбол 100\n\n📌 КОМАНДЫ:\n├ б - баланс\n├ профиль - статистика\n├ топ - топ игроков\n├ достижения - список достижений\n├ значки - список значков\n├ титулы - список титулов\n├ прогресс - прогресс\n├ престиж - престиж\n├ ранг - звание\n├ бонус - бонус\n├ задания - задания\n├ рефка - реферальная ссылка\n├ промокод Gold2026 - 100 000 GOLD\n├ го - запуск рулетки\n├ отмена - отмена ставок\n├ дать 500 (ответом)\n└ дать всё (ответом)"
        reply_markup = get_main_keyboard_page3()
    elif act=="top":
        if not user_balances:
            text = "📊 Пусто"
        else:
            items=sorted(user_balances.items(),key=lambda x:x[1],reverse=True)[:10]
            txt="🏆 <b>ТОП-10 ИГРОКОВ</b>\n\n"
            for i,(u,b)in enumerate(items,1):
                try:
                    n=(await bot.get_chat(u)).full_name
                except:
                    n=str(u)
                txt+=f"{i}. {n}\n└ {format_amount(b)} GOLD\n\n"
            text = txt
        reply_markup = get_main_keyboard_page3()
    else:
        text = "❓ Помощь"
        reply_markup = get_main_keyboard_page3()
    
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    except Exception as e:
        if "Message is not modified" in str(e):
            pass
        else:
            logging.error(f"Ошибка: {e}")

@dp.message_handler()
async def handle(m):
    global pending_bets,game_in_progress,last_game_time,game_history,lottery_pool
    
    if game_in_progress and time.time()-last_game_time>60:
        force_reset_game()
        await m.reply("⚠️ Предыдущая игра принудительно завершена")
    uid=m.from_user.id
    name=m.from_user.full_name
    text=m.text.strip()
    if text.lower().startswith('/'):
        return
    parts=text.split()
    
    # ========== ПРОМОКОД ==========
    if text.lower().startswith("промокод "):
        code = parts[1] if len(parts) > 1 else ""
        reward, status = use_promocode(uid, code)
        if status == "success":
            user_balances[uid] = user_balances.get(uid, 0) + reward
            save_data()
            await m.reply(f"🎫 <b>ПРОМОКОД АКТИВИРОВАН!</b>\n\n💰 +{format_amount(reward)} GOLD", parse_mode="HTML")
        elif status == "already_used":
            await m.reply("❌ Ты уже использовал этот промокод!")
        else:
            await m.reply("❌ Неверный промокод!")
        return
    
    # ========== РЕФЕРАЛЫ ==========
    if text.lower() in["рефка","referral","рефералы"]:
        link = generate_referral_link(uid)
        referrals = user_referrals.get(uid, 0)
        await m.reply(f"👥 <b>РЕФЕРАЛЬНАЯ СИСТЕМА</b>\n\n├ 👥 Приглашено: {referrals}\n├ 💰 Награда за друга: +{format_amount(REFERRAL_REWARD)} GOLD\n└ 🔗 Твоя ссылка:\n{link}", parse_mode="HTML")
        return
    
    # ========== БОНУС ==========
    if text.lower()=="бонус":
        now=int(time.time())
        ds=daily_streak.get(uid,{"last":0,"streak":0})
        if now-ds["last"]>=86400:
            if now-ds["last"]>=172800:
                ds["streak"]=0
            ds["streak"]+=1
            bonus = 50000
            user_balances[uid]=user_balances.get(uid,0)+bonus
            ds["last"]=now
            daily_streak[uid]=ds
            save_data()
            await m.reply(f"<code>🎁 +{format_amount(bonus)} GOLD\n🔥 Стрик: {ds['streak']} дн.\n💳 Новый баланс: {format_amount(user_balances[uid])} GOLD</code>", parse_mode="HTML")
        else:
            rem=86400-(now-ds["last"])
            await m.reply(f"<code>⏰ Через {rem//3600} ч {(rem%3600)//60} мин</code>", parse_mode="HTML")
        return
    
    # ========== БАЛАНС ==========
    if text.lower() in["б","баланс"]:
        await m.reply(f"<code>{name}\n💰 Баланс: {format_amount(user_balances.get(uid,0))} GOLD</code>", parse_mode="HTML")
        return
    
    # ========== ПРОФИЛЬ ==========
    if text.lower() in["профиль","profile"]:
        bal=user_balances.get(uid,0)
        s=user_stats.get(uid,{"played":0,"won":0,"total_bet":0,"total_win":0})
        lvl=user_levels.get(uid,0)
        rank=get_rank(bal)
        prestige=user_prestige.get(uid,0)
        active_title=user_active_title.get(uid,"Не выбран")
        badges_count=len(user_badges.get(uid,[]))
        referrals=user_referrals.get(uid,0)
        wr=(s["won"]/s["played"]*100)if s["played"]>0 else 0
        prof=s["total_win"]-s["total_bet"]
        await m.reply(f"<code>👤 {name}\n🆔 {uid}\n📊 Уровень: {lvl}\n🎖️ Звание: {rank['name']}\n🌟 Престиж: {prestige}\n🎖️ Значки: {badges_count}\n🏅 Титул: {active_title}\n👥 Пригласил: {referrals}\n💰 {format_amount(bal)} GOLD\n\n🎲 Игр: {s['played']}\n🏆 Побед: {s['won']}\n📈 Винрейт: {wr:.1f}%\n📊 Профит: {format_amount(prof)} GOLD</code>", parse_mode="HTML")
        return
    
    # ========== РАНГ ==========
    if text.lower() in["ранг","rank"]:
        bal=user_balances.get(uid,0)
        rank=get_rank(bal)
        next_rank=None
        for i,r in enumerate(RANKS):
            if r["name"]==rank["name"] and i+1<len(RANKS):
                next_rank=RANKS[i+1]
                break
        if next_rank:
            need=next_rank["need"]-bal
            await m.reply(f"🎖️ <b>ТВОЁ ЗВАНИЕ</b>\n\n{rank['name']}\n\n📊 До звания {next_rank['name']}:\n└ {format_amount(need)} GOLD", parse_mode="HTML")
        else:
            await m.reply(f"🎖️ <b>ТВОЁ ЗВАНИЕ</b>\n\n{rank['name']}\n\n👑 Ты достиг максимального звания!", parse_mode="HTML")
        return
    
    # ========== ПРЕСТИЖ ==========
    if text.lower() in["престиж","prestige"]:
        can, info = can_prestige(uid)
        if can:
            result = do_prestige(uid)
            if result:
                await send_prestige_notify(uid, result, m)
                await m.reply(f"🌟 Поздравляем! Ты достиг {result['name']}!\n💰 +{format_amount(result['reward'])} GOLD\n📈 Уровень сброшен до 0")
            else:
                await m.reply("❌ Ошибка при повышении престижа")
        else:
            await m.reply(f"❌ {info}")
        return
    
    # ========== ПРОГРЕСС ==========
    if text.lower() in["прогресс","progress"]:
        rank=get_rank(user_balances.get(uid,0))
        await m.reply(f"📊 <b>ПРОГРЕСС</b>\n\n🎖️ Звание: {rank['name']}\n🌟 Престиж: {user_prestige.get(uid,0)}\n📈 Уровень: {user_levels.get(uid,0)}\n💰 Баланс: {format_amount(user_balances.get(uid,0))} GOLD", parse_mode="HTML")
        return
    
    # ========== ДОСТИЖЕНИЯ ==========
    if text.lower() in["достижения","achievements"]:
        await m.reply(get_achievements_list(uid), parse_mode="HTML")
        return
    
    # ========== ЗНАЧКИ ==========
    if text.lower() in["значки","badges"]:
        await m.reply(get_badges_list(uid), parse_mode="HTML")
        return
    
    # ========== ТИТУЛЫ ==========
    if text.lower() in["титулы","titles"]:
        await m.reply(get_titles_list(uid), parse_mode="HTML")
        return
    
    # ========== ЗАДАНИЯ ==========
    if text.lower() in["задания","quests"]:
        await m.reply(f"<code>🎯 ЕЖЕДНЕВНЫЕ ЗАДАНИЯ{get_quests_status(uid)}\n\n⏰ Обновляются каждые 24 часа\n✨ Награда выдается автоматически!</code>", parse_mode="HTML")
        return
    
    # ========== ТОП ==========
    if text.lower()=="топ":
        if not user_balances:
            return await m.reply("📊 Пусто")
        items=sorted(user_balances.items(),key=lambda x:x[1],reverse=True)[:10]
        txt="🏆 ТОП-10 ИГРОКОВ\n\n"
        for i,(u,b)in enumerate(items,1):
            try:
                n=(await bot.get_chat(u)).full_name
            except:
                n=str(u)
            txt+=f"{i}. {n}\n└ {format_amount(b)} GOLD\n\n"
        await m.reply(f"<code>{txt}</code>", parse_mode="HTML")
        return
    
    # ========== БОУЛИНГ ==========
    if text.lower().startswith("боулинг "):
        if len(parts)!=2:
            await m.reply("❌ Пример: боулинг 100")
            return
        try:
            bet=int(parts[1])
        except:
            await m.reply("❌ Пример: боулинг 100")
            return
        if bet<100:
            await m.reply("❌ Минимальная ставка 100 GOLD")
            return
        bal=user_balances.get(uid,0)
        if bet>bal:
            await m.reply(f"❌ Недостаточно GOLD, баланс: {format_amount(bal)} GOLD")
            return
        pins = play_bowling()
        if pins == 10:
            mult = 3
            result_text = "🎳 СТРАЙК! x3"
            if uid not in user_stats:
                user_stats[uid] = {}
            user_stats[uid]["bowling_strike"] = user_stats[uid].get("bowling_strike", 0) + 1
        elif pins >= 8:
            mult = 2
            result_text = f"🎳 Спэр! {pins} кеглей! x2"
        else:
            mult = 0.5
            result_text = f"🎳 Мимо! {pins} кеглей... x0.5"
        win_amt = int(bet * mult)
        old_bal = bal
        if mult >= 1:
            user_balances[uid] = bal - bet + win_amt
        else:
            user_balances[uid] = bal - bet
            win_amt = 0
        new_rank = check_rank_up(uid, old_bal, user_balances[uid])
        if new_rank:
            await send_rank_up_notify(uid, new_rank, m)
        await m.reply(f"🎳 <b>БОУЛИНГ</b>\n\n{result_text}\n\n{'✅ ВЫ ВЫИГРАЛИ! +' + format_amount(win_amt) if win_amt > 0 else '❌ ВЫ ПРОИГРАЛИ! -' + format_amount(bet)} GOLD", parse_mode="HTML")
        if uid not in user_stats:
            user_stats[uid] = {"played":0,"won":0,"total_bet":0,"total_win":0}
        user_stats[uid]["played"] = user_stats[uid].get("played",0) + 1
        if win_amt > 0:
            user_stats[uid]["won"] = user_stats[uid].get("won",0) + 1
        user_stats[uid]["total_bet"] = user_stats[uid].get("total_bet",0) + bet
        user_stats[uid]["total_win"] = user_stats[uid].get("total_win",0) + win_amt
        user_levels[uid] = user_levels.get(uid,0) + 1
        update_quest_progress(uid,"play_3_games")
        update_quest_progress(uid,"play_10_games")
        update_quest_progress(uid,"make_bet")
        update_quest_progress(uid,"make_5_bets")
        new_achs = check_achievements(uid)
        for ach in new_achs:
            await send_achievement_notify(uid, ach, m)
        new_badges = check_badges(uid)
        for badge in new_badges:
            await send_badge_notify(uid, badge, m)
        save_data()
        return
    
    # ========== КОРОБКИ ==========
    if text.lower().startswith("коробки "):
        if len(parts)!=3:
            await m.reply("❌ Пример: коробки 100 1\nКоробки: 1, 2 или 3")
            return
        try:
            bet=int(parts[1])
        except:
            await m.reply("❌ Пример: коробки 100 1")
            return
        try:
            box_num=int(parts[2])
        except:
            await m.reply("❌ Номер коробки должен быть числом (1-3)")
            return
        if bet<100:
            await m.reply("❌ Минимальная ставка 100 GOLD")
            return
        if box_num not in [1,2,3]:
            await m.reply("❌ Выбери коробку 1, 2 или 3")
            return
        bal=user_balances.get(uid,0)
        if bet>bal:
            await m.reply(f"❌ Недостаточно GOLD, баланс: {format_amount(bal)} GOLD")
            return
        mult = choose_box(box_num)
        win_amt = int(bet * mult)
        old_bal = bal
        if mult >= 1:
            user_balances[uid] = bal - bet + win_amt
        else:
            user_balances[uid] = bal - bet
            win_amt = 0
        new_rank = check_rank_up(uid, old_bal, user_balances[uid])
        if new_rank:
            await send_rank_up_notify(uid, new_rank, m)
        await m.reply(f"📦 <b>КОРОБКИ</b>\n\nТы выбрал коробку {box_num}\nМножитель: x{mult}\n\n{'✅ ВЫ ВЫИГРАЛИ! +' + format_amount(win_amt) if win_amt > 0 else '❌ ВЫ ПРОИГРАЛИ! -' + format_amount(bet)} GOLD", parse_mode="HTML")
        if uid not in user_stats:
            user_stats[uid] = {"played":0,"won":0,"total_bet":0,"total_win":0}
        user_stats[uid]["played"] = user_stats[uid].get("played",0) + 1
        if win_amt > 0:
            user_stats[uid]["won"] = user_stats[uid].get("won",0) + 1
        user_stats[uid]["total_bet"] = user_stats[uid].get("total_bet",0) + bet
        user_stats[uid]["total_win"] = user_stats[uid].get("total_win",0) + win_amt
        user_levels[uid] = user_levels.get(uid,0) + 1
        update_quest_progress(uid,"play_3_games")
        update_quest_progress(uid,"play_10_games")
        update_quest_progress(uid,"make_bet")
        update_quest_progress(uid,"make_5_bets")
        new_achs = check_achievements(uid)
        for ach in new_achs:
            await send_achievement_notify(uid, ach, m)
        new_badges = check_badges(uid)
        for badge in new_badges:
            await send_badge_notify(uid, badge, m)
        save_data()
        return
    
    # ========== ДАРТС ==========
    if text.lower().startswith("дартс "):
        if len(parts)!=2:
            await m.reply("❌ Пример: дартс 100")
            return
        try:
            bet=int(parts[1])
        except:
            await m.reply("❌ Пример: дартс 100")
            return
        if bet<100:
            await m.reply("❌ Минимальная ставка 100 GOLD")
            return
        bal=user_balances.get(uid,0)
        if bet>bal:
            await m.reply(f"❌ Недостаточно GOLD, баланс: {format_amount(bal)} GOLD")
            return
        result = throw_dart()
        mult = DART_MULT[result]
        win_amt = int(bet * mult)
        old_bal = bal
        if mult > 0:
            user_balances[uid] = bal - bet + win_amt
        else:
            user_balances[uid] = bal - bet
            win_amt = 0
        if result == "bullseye":
            result_text = "🎯 ЯБЛОЧКО! x10"
            if uid not in user_stats:
                user_stats[uid] = {}
            user_stats[uid]["dart_bullseye"] = user_stats[uid].get("dart_bullseye", 0) + 1
        elif result == "inner":
            result_text = "🎯 Внутреннее кольцо! x5"
        elif result == "outer":
            result_text = "🎯 Внешнее кольцо! x2"
        else:
            result_text = "🎯 Мимо! x0"
        new_rank = check_rank_up(uid, old_bal, user_balances[uid])
        if new_rank:
            await send_rank_up_notify(uid, new_rank, m)
        await m.reply(f"🎯 <b>ДАРТС</b>\n\n{result_text}\n\n{'✅ ВЫ ВЫИГРАЛИ! +' + format_amount(win_amt) if win_amt > 0 else '❌ ВЫ ПРОИГРАЛИ! -' + format_amount(bet)} GOLD", parse_mode="HTML")
        if uid not in user_stats:
            user_stats[uid] = {"played":0,"won":0,"total_bet":0,"total_win":0}
        user_stats[uid]["played"] = user_stats[uid].get("played",0) + 1
        if win_amt > 0:
            user_stats[uid]["won"] = user_stats[uid].get("won",0) + 1
        user_stats[uid]["total_bet"] = user_stats[uid].get("total_bet",0) + bet
        user_stats[uid]["total_win"] = user_stats[uid].get("total_win",0) + win_amt
        user_levels[uid] = user_levels.get(uid,0) + 1
        update_quest_progress(uid,"play_3_games")
        update_quest_progress(uid,"play_10_games")
        update_quest_progress(uid,"make_bet")
        update_quest_progress(uid,"make_5_bets")
        new_achs = check_achievements(uid)
        for ach in new_achs:
            await send_achievement_notify(uid, ach, m)
        new_badges = check_badges(uid)
        for badge in new_badges:
            await send_badge_notify(uid, badge, m)
        save_data()
        return
    
    # ========== БАСКЕТБОЛ ==========
    if text.lower().startswith("баскетбол "):
        if len(parts)!=2:
            await m.reply("❌ Пример: баскетбол 100")
            return
        try:
            bet=int(parts[1])
        except:
            await m.reply("❌ Пример: баскетбол 100")
            return
        if bet<100:
            await m.reply("❌ Минимальная ставка 100 GOLD")
            return
        bal=user_balances.get(uid,0)
        if bet>bal:
            await m.reply(f"❌ Недостаточно GOLD, баланс: {format_amount(bal)} GOLD")
            return
        result = shoot_ball()
        mult = BASKET_MULT[result]
        win_amt = int(bet * mult)
        old_bal = bal
        if mult > 0:
            user_balances[uid] = bal - bet + win_amt
        else:
            user_balances[uid] = bal - bet
            win_amt = 0
        if result == "three_point":
            result_text = "🏀 ТРЁХОЧКОВЫЙ! x3"
            if uid not in user_stats:
                user_stats[uid] = {}
            user_stats[uid]["basketball_three"] = user_stats[uid].get("basketball_three", 0) + 1
        elif result == "two_point":
            result_text = "🏀 Двухочковый! x2"
        elif result == "free_throw":
            result_text = "🏀 Штрафной! x1"
        else:
            result_text = "🏀 Мимо! x0"
        new_rank = check_rank_up(uid, old_bal, user_balances[uid])
        if new_rank:
            await send_rank_up_notify(uid, new_rank, m)
        await m.reply(f"🏀 <b>БАСКЕТБОЛ</b>\n\n{result_text}\n\n{'✅ ВЫ ВЫИГРАЛИ! +' + format_amount(win_amt) if win_amt > 0 else '❌ ВЫ ПРОИГРАЛИ! -' + format_amount(bet)} GOLD", parse_mode="HTML")
        if uid not in user_stats:
            user_stats[uid] = {"played":0,"won":0,"total_bet":0,"total_win":0}
        user_stats[uid]["played"] = user_stats[uid].get("played",0) + 1
        if win_amt > 0:
            user_stats[uid]["won"] = user_stats[uid].get("won",0) + 1
        user_stats[uid]["total_bet"] = user_stats[uid].get("total_bet",0) + bet
        user_stats[uid]["total_win"] = user_stats[uid].get("total_win",0) + win_amt
        user_levels[uid] = user_levels.get(uid,0) + 1
        update_quest_progress(uid,"play_3_games")
        update_quest_progress(uid,"play_10_games")
        update_quest_progress(uid,"make_bet")
        update_quest_progress(uid,"make_5_bets")
        new_achs = check_achievements(uid)
        for ach in new_achs:
            await send_achievement_notify(uid, ach, m)
        new_badges = check_badges(uid)
        for badge in new_badges:
            await send_badge_notify(uid, badge, m)
        save_data()
        return
    
    # ========== КНБ ==========
    if text.lower().startswith("кнб "):
        if len(parts)<3:
            await m.reply("❌ Пример: кнб 500 камень")
            return
        try:
            bet=int(parts[1])
        except:
            await m.reply("❌ Пример: кнб 500 камень")
            return
        if bet<100:
            await m.reply("❌ Минимальная ставка 100 GOLD")
            return
        choice=parts[2].lower()
        if choice not in RPS_CHOICES:
            await m.reply(f"❌ Неверный выбор! Варианты: камень, ножницы, бумага")
            return
        bal=user_balances.get(uid,0)
        if bet>bal:
            await m.reply(f"❌ Недостаточно GOLD, баланс: {format_amount(bal)} GOLD")
            return
        bot_choice=random.choice(["камень","ножницы","бумага"])
        result=rps_result(choice,bot_choice)
        old_bal=bal
        if result=="win":
            win_amt=bet*2
            user_balances[uid]=user_balances.get(uid,0)+win_amt
            new_rank=check_rank_up(uid,old_bal,user_balances[uid])
            if new_rank:
                await send_rank_up_notify(uid,new_rank,m)
            await m.reply(f"✊ <b>КАМЕНЬ-НОЖНИЦЫ-БУМАГА</b>\n\nТы: {RPS_CHOICES[choice]} | Бот: {RPS_CHOICES[bot_choice]}\n\n✅ ВЫ ВЫИГРАЛИ!\n💰 +{format_amount(win_amt)} GOLD (x2)", parse_mode="HTML")
            if uid not in user_stats:
                user_stats[uid]={"played":0,"won":0,"total_bet":0,"total_win":0,"rps_wins":0}
            user_stats[uid]["played"]=user_stats[uid].get("played",0)+1
            user_stats[uid]["won"]=user_stats[uid].get("won",0)+1
            user_stats[uid]["rps_wins"]=user_stats[uid].get("rps_wins",0)+1
            user_stats[uid]["total_bet"]=user_stats[uid].get("total_bet",0)+bet
            user_stats[uid]["total_win"]=user_stats[uid].get("total_win",0)+win_amt
            user_levels[uid]=user_levels.get(uid,0)+1
            update_quest_progress(uid,"play_3_games")
            update_quest_progress(uid,"play_10_games")
            update_quest_progress(uid,"make_bet")
            update_quest_progress(uid,"make_5_bets")
            daily_quests["win_3_streak"]["current_streak"][uid]=daily_quests["win_3_streak"]["current_streak"].get(uid,0)+1
            update_quest_progress(uid,"win_3_streak",daily_quests["win_3_streak"]["current_streak"][uid])
            update_quest_progress(uid,"win_5_streak",daily_quests["win_3_streak"]["current_streak"][uid])
        elif result=="draw":
            user_balances[uid]=bal-bet
            user_balances[uid]=user_balances.get(uid,0)+bet
            await m.reply(f"✊ <b>КАМЕНЬ-НОЖНИЦЫ-БУМАГА</b>\n\nТы: {RPS_CHOICES[choice]} | Бот: {RPS_CHOICES[bot_choice]}\n\n🤝 НИЧЬЯ!\n💰 Ставка возвращена", parse_mode="HTML")
            if uid not in user_stats:
                user_stats[uid]={"played":0,"won":0,"total_bet":0,"total_win":0}
            user_stats[uid]["played"]=user_stats[uid].get("played",0)+1
            user_stats[uid]["total_bet"]=user_stats[uid].get("total_bet",0)+bet
            user_levels[uid]=user_levels.get(uid,0)+1
            update_quest_progress(uid,"play_3_games")
            update_quest_progress(uid,"play_10_games")
            update_quest_progress(uid,"make_bet")
            update_quest_progress(uid,"make_5_bets")
        else:
            user_balances[uid]=bal-bet
            await m.reply(f"✊ <b>КАМЕНЬ-НОЖНИЦЫ-БУМАГА</b>\n\nТы: {RPS_CHOICES[choice]} | Бот: {RPS_CHOICES[bot_choice]}\n\n❌ ВЫ ПРОИГРАЛИ!\n💸 -{format_amount(bet)} GOLD", parse_mode="HTML")
            if uid not in user_stats:
                user_stats[uid]={"played":0,"won":0,"total_bet":0,"total_win":0}
            user_stats[uid]["played"]=user_stats[uid].get("played",0)+1
            user_stats[uid]["total_bet"]=user_stats[uid].get("total_bet",0)+bet
            user_levels[uid]=user_levels.get(uid,0)+1
            update_quest_progress(uid,"play_3_games")
            update_quest_progress(uid,"play_10_games")
            update_quest_progress(uid,"make_bet")
            update_quest_progress(uid,"make_5_bets")
            daily_quests["win_3_streak"]["current_streak"][uid]=0
        new_achs=check_achievements(uid)
        for ach in new_achs:
            await send_achievement_notify(uid,ach,m)
        new_titles=check_titles(uid)
        for title in new_titles:
            await send_title_notify(uid,title,m)
        new_badges=check_badges(uid)
        for badge in new_badges:
            await send_badge_notify(uid,badge,m)
        save_data()
        return
    
    # ========== СПОРТ ==========
    if text.lower().startswith("спорт "):
        if len(parts)!=3:
            await m.reply("❌ Пример: спорт 500 1\n1 - победа хозяев, X - ничья, 2 - победа гостей")
            return
        try:
            bet=int(parts[1])
        except:
            await m.reply("❌ Пример: спорт 500 1")
            return
        if bet<100:
            await m.reply("❌ Минимальная ставка 100 GOLD")
            return
        bet_type=parts[2].upper()
        if bet_type not in ["1","X","2"]:
            await m.reply("❌ Неверный тип ставки! Используй 1, X или 2")
            return
        bal=user_balances.get(uid,0)
        if bet>bal:
            await m.reply(f"❌ Недостаточно GOLD, баланс: {format_amount(bal)} GOLD")
            return
        event=get_sport_event()
        if bet_type=="1":
            coef=event["coef1"]
        elif bet_type=="X":
            coef=event["coefX"]
        else:
            coef=event["coef2"]
        win=random.choice([True,False])
        old_bal=bal
        if win:
            win_amt=int(bet*coef)
            user_balances[uid]=user_balances.get(uid,0)+win_amt
            new_rank=check_rank_up(uid,old_bal,user_balances[uid])
            if new_rank:
                await send_rank_up_notify(uid,new_rank,m)
            await m.reply(f"⚽ <b>СПОРТИВНАЯ СТАВКА</b>\n\n{event['name']}\nСтавка: {bet_type} (x{coef})\n\n✅ ВЫ ВЫИГРАЛИ!\n💰 +{format_amount(win_amt)} GOLD", parse_mode="HTML")
            if uid not in user_stats:
                user_stats[uid]={"played":0,"won":0,"total_bet":0,"total_win":0,"sport_wins":0}
            user_stats[uid]["played"]=user_stats[uid].get("played",0)+1
            user_stats[uid]["won"]=user_stats[uid].get("won",0)+1
            user_stats[uid]["sport_wins"]=user_stats[uid].get("sport_wins",0)+1
            user_stats[uid]["total_bet"]=user_stats[uid].get("total_bet",0)+bet
            user_stats[uid]["total_win"]=user_stats[uid].get("total_win",0)+win_amt
            user_levels[uid]=user_levels.get(uid,0)+1
            update_quest_progress(uid,"play_3_games")
            update_quest_progress(uid,"play_10_games")
            update_quest_progress(uid,"make_bet")
            update_quest_progress(uid,"make_5_bets")
            daily_quests["win_3_streak"]["current_streak"][uid]=daily_quests["win_3_streak"]["current_streak"].get(uid,0)+1
            update_quest_progress(uid,"win_3_streak",daily_quests["win_3_streak"]["current_streak"][uid])
            update_quest_progress(uid,"win_5_streak",daily_quests["win_3_streak"]["current_streak"][uid])
        else:
            user_balances[uid]=bal-bet
            await m.reply(f"⚽ <b>СПОРТИВНАЯ СТАВКА</b>\n\n{event['name']}\nСтавка: {bet_type} (x{coef})\n\n❌ ВЫ ПРОИГРАЛИ!\n💸 -{format_amount(bet)} GOLD", parse_mode="HTML")
            if uid not in user_stats:
                user_stats[uid]={"played":0,"won":0,"total_bet":0,"total_win":0}
            user_stats[uid]["played"]=user_stats[uid].get("played",0)+1
            user_stats[uid]["total_bet"]=user_stats[uid].get("total_bet",0)+bet
            user_levels[uid]=user_levels.get(uid,0)+1
            update_quest_progress(uid,"play_3_games")
            update_quest_progress(uid,"play_10_games")
            update_quest_progress(uid,"make_bet")
            update_quest_progress(uid,"make_5_bets")
            daily_quests["win_3_streak"]["current_streak"][uid]=0
        new_achs=check_achievements(uid)
        for ach in new_achs:
            await send_achievement_notify(uid,ach,m)
        new_titles=check_titles(uid)
        for title in new_titles:
            await send_title_notify(uid,title,m)
        new_badges=check_badges(uid)
        for badge in new_badges:
            await send_badge_notify(uid,badge,m)
        save_data()
        return
    
    # ========== ЛОТЕРЕЯ ==========
    if text.lower().startswith("лотерея "):
        if len(parts)!=2:
            await m.reply("❌ Пример: лотерея 1000")
            return
        try:
            bet=int(parts[1])
        except:
            await m.reply("❌ Пример: лотерея 1000")
            return
        if bet<100:
            await m.reply("❌ Минимальная ставка 100 GOLD")
            return
        bal=user_balances.get(uid,0)
        if bet>bal:
            await m.reply(f"❌ Недостаточно GOLD, баланс: {format_amount(bal)} GOLD")
            return
        user_balances[uid]=bal-bet
        lottery_pool+=bet
        user_lottery_tickets[uid]=user_lottery_tickets.get(uid,0)+1
        save_data()
        await m.reply(f"🎫 <b>ЛОТЕРЕЯ</b>\n\n✅ Билет куплен за {format_amount(bet)} GOLD!\n📊 Твои билеты: {user_lottery_tickets[uid]}\n💰 Призовой фонд: {format_amount(lottery_pool)} GOLD\n\n⏰ Розыгрыш каждый час!", parse_mode="HTML")
        return
    
    # ========== КОСТИ ==========
    if text.lower().startswith("кости "):
        if len(parts)!=3:
            await m.reply("❌ Пример: кости 500 на 7\nВарианты: на [2-12], на дубль, на чёт, на нечёт, на больше, на меньше")
            return
        try:
            bet=int(parts[1])
        except:
            await m.reply("❌ Пример: кости 500 на 7")
            return
        if bet<100:
            await m.reply("❌ Минимальная ставка 100 GOLD")
            return
        bet_type=parts[2].lower()
        if bet_type not in VALID_DICE_BETS:
            await m.reply(f"❌ Неверный тип ставки!\nВарианты: на [2-12], на дубль, на чёт, на нечёт, на больше, на меньше")
            return
        bal=user_balances.get(uid,0)
        if bet>bal:
            await m.reply(f"❌ Недостаточно GOLD, баланс: {format_amount(bal)} GOLD")
            return
        old_bal=bal
        user_balances[uid]=bal-bet
        d1,d2=roll_dice()
        mult=get_dice_multiplier(bet_type,d1,d2)
        if mult>0:
            win=bet*mult
            user_balances[uid]=user_balances.get(uid,0)+win
            new_rank=check_rank_up(uid,old_bal,user_balances[uid])
            if new_rank:
                await send_rank_up_notify(uid,new_rank,m)
            await m.reply(f"🎲 <b>КОСТИ</b>\n\n{format_dice(d1,d2)}\nСумма: {d1+d2}\n\n✅ ВЫ ВЫИГРАЛИ!\n💰 +{format_amount(win)} GOLD (x{mult})", parse_mode="HTML")
            if uid not in user_stats:
                user_stats[uid]={"played":0,"won":0,"total_bet":0,"total_win":0}
            user_stats[uid]["played"]=user_stats[uid].get("played",0)+1
            user_stats[uid]["won"]=user_stats[uid].get("won",0)+1
            user_stats[uid]["total_bet"]=user_stats[uid].get("total_bet",0)+bet
            user_stats[uid]["total_win"]=user_stats[uid].get("total_win",0)+win
            user_levels[uid]=user_levels.get(uid,0)+1
            update_quest_progress(uid,"play_3_games")
            update_quest_progress(uid,"play_10_games")
            update_quest_progress(uid,"make_bet")
            update_quest_progress(uid,"make_5_bets")
            update_quest_progress(uid,"win_dice")
            daily_quests["win_3_streak"]["current_streak"][uid]=daily_quests["win_3_streak"]["current_streak"].get(uid,0)+1
            update_quest_progress(uid,"win_3_streak",daily_quests["win_3_streak"]["current_streak"][uid])
            update_quest_progress(uid,"win_5_streak",daily_quests["win_3_streak"]["current_streak"][uid])
            update_quest_earn(uid,win)
        else:
            await m.reply(f"🎲 <b>КОСТИ</b>\n\n{format_dice(d1,d2)}\nСумма: {d1+d2}\n\n❌ ВЫ ПРОИГРАЛИ!\n💸 -{format_amount(bet)} GOLD", parse_mode="HTML")
            if uid not in user_stats:
                user_stats[uid]={"played":0,"won":0,"total_bet":0,"total_win":0}
            user_stats[uid]["played"]=user_stats[uid].get("played",0)+1
            user_stats[uid]["total_bet"]=user_stats[uid].get("total_bet",0)+bet
            user_levels[uid]=user_levels.get(uid,0)+1
            update_quest_progress(uid,"play_3_games")
            update_quest_progress(uid,"play_10_games")
            update_quest_progress(uid,"make_bet")
            update_quest_progress(uid,"make_5_bets")
            daily_quests["win_3_streak"]["current_streak"][uid]=0
        new_achs=check_achievements(uid)
        for ach in new_achs:
            await send_achievement_notify(uid,ach,m)
        new_titles=check_titles(uid)
        for title in new_titles:
            await send_title_notify(uid,title,m)
        new_badges=check_badges(uid)
        for badge in new_badges:
            await send_badge_notify(uid,badge,m)
        save_data()
        return
    
    # ========== СЛОТ ==========
    if text.lower().startswith("слот "):
        if len(parts)!=2:
            await m.reply("❌ Пример: слот 100")
            return
        try:
            bet=int(parts[1])
        except:
            await m.reply("❌ Пример: слот 100")
            return
        if bet<100:
            await m.reply("❌ Минимальная ставка 100 GOLD")
            return
        bal=user_balances.get(uid,0)
        if bet>bal:
            await m.reply(f"❌ Недостаточно GOLD, баланс: {format_amount(bal)} GOLD")
            return
        old_bal=bal
        user_balances[uid]=bal-bet
        symbols=spin_slot()
        mult=get_slot_win(symbols)
        if uid not in user_stats:
            user_stats[uid]={"played":0,"won":0,"total_bet":0,"total_win":0,"slot_jackpot":0}
        if symbols==["💎","💎","💎"]:
            user_stats[uid]["slot_jackpot"]=user_stats[uid].get("slot_jackpot",0)+1
        if mult>0:
            win=bet*mult
            user_balances[uid]=user_balances.get(uid,0)+win
            new_rank=check_rank_up(uid,old_bal,user_balances[uid])
            if new_rank:
                await send_rank_up_notify(uid,new_rank,m)
            await m.reply(f"🎰 <b>СЛОТ-МАШИНА</b>\n\n{format_slot(symbols)}\n\n✅ ВЫ ВЫИГРАЛИ!\n💰 +{format_amount(win)} GOLD (x{mult})", parse_mode="HTML")
            user_stats[uid]["played"]=user_stats[uid].get("played",0)+1
            user_stats[uid]["won"]=user_stats[uid].get("won",0)+1
            user_stats[uid]["total_bet"]=user_stats[uid].get("total_bet",0)+bet
            user_stats[uid]["total_win"]=user_stats[uid].get("total_win",0)+win
            user_levels[uid]=user_levels.get(uid,0)+1
            update_quest_progress(uid,"play_3_games")
            update_quest_progress(uid,"play_10_games")
            update_quest_progress(uid,"make_bet")
            update_quest_progress(uid,"make_5_bets")
            update_quest_progress(uid,"win_slot")
            daily_quests["win_3_streak"]["current_streak"][uid]=daily_quests["win_3_streak"]["current_streak"].get(uid,0)+1
            update_quest_progress(uid,"win_3_streak",daily_quests["win_3_streak"]["current_streak"][uid])
            update_quest_progress(uid,"win_5_streak",daily_quests["win_3_streak"]["current_streak"][uid])
            update_quest_earn(uid,win)
        else:
            await m.reply(f"🎰 <b>СЛОТ-МАШИНА</b>\n\n{format_slot(symbols)}\n\n❌ ВЫ ПРОИГРАЛИ!\n💸 -{format_amount(bet)} GOLD", parse_mode="HTML")
            user_stats[uid]["played"]=user_stats[uid].get("played",0)+1
            user_stats[uid]["total_bet"]=user_stats[uid].get("total_bet",0)+bet
            user_levels[uid]=user_levels.get(uid,0)+1
            update_quest_progress(uid,"play_3_games")
            update_quest_progress(uid,"play_10_games")
            update_quest_progress(uid,"make_bet")
            update_quest_progress(uid,"make_5_bets")
            daily_quests["win_3_streak"]["current_streak"][uid]=0
        new_achs=check_achievements(uid)
        for ach in new_achs:
            await send_achievement_notify(uid,ach,m)
        new_titles=check_titles(uid)
        for title in new_titles:
            await send_title_notify(uid,title,m)
        new_badges=check_badges(uid)
        for badge in new_badges:
            await send_badge_notify(uid,badge,m)
        save_data()
        return
    
    # ========== КОЛЕСО ==========
    if text.lower().startswith("колесо "):
        if len(parts)!=2:
            await m.reply("❌ Пример: колесо 100")
            return
        try:
            bet=int(parts[1])
        except:
            await m.reply("❌ Пример: колесо 100")
            return
        if bet<100:
            await m.reply("❌ Минимальная ставка 100 GOLD")
            return
        bal=user_balances.get(uid,0)
        if bet>bal:
            await m.reply(f"❌ Недостаточно GOLD, баланс: {format_amount(bal)} GOLD")
            return
        old_bal=bal
        user_balances[uid]=bal-bet
        sector=spin_wheel()
        mult=sector["mult"]
        if uid not in user_stats:
            user_stats[uid]={"played":0,"won":0,"total_bet":0,"total_win":0,"max_fortune":0}
        if mult>user_stats[uid].get("max_fortune",0):
            user_stats[uid]["max_fortune"]=mult
        if mult>0:
            win=bet*mult
            user_balances[uid]=user_balances.get(uid,0)+win
            new_rank=check_rank_up(uid,old_bal,user_balances[uid])
            if new_rank:
                await send_rank_up_notify(uid,new_rank,m)
            await m.reply(f"🎡 <b>КОЛЕСО ФОРТУНЫ</b>\n\n{sector['name']}\n\n✅ ВЫ ВЫИГРАЛИ!\n💰 +{format_amount(win)} GOLD (x{mult})", parse_mode="HTML")
            user_stats[uid]["played"]=user_stats[uid].get("played",0)+1
            user_stats[uid]["won"]=user_stats[uid].get("won",0)+1
            user_stats[uid]["total_bet"]=user_stats[uid].get("total_bet",0)+bet
            user_stats[uid]["total_win"]=user_stats[uid].get("total_win",0)+win
            user_levels[uid]=user_levels.get(uid,0)+1
            update_quest_progress(uid,"play_3_games")
            update_quest_progress(uid,"play_10_games")
            update_quest_progress(uid,"make_bet")
            update_quest_progress(uid,"make_5_bets")
            update_quest_progress(uid,"win_wheel")
            daily_quests["win_3_streak"]["current_streak"][uid]=daily_quests["win_3_streak"]["current_streak"].get(uid,0)+1
            update_quest_progress(uid,"win_3_streak",daily_quests["win_3_streak"]["current_streak"][uid])
            update_quest_progress(uid,"win_5_streak",daily_quests["win_3_streak"]["current_streak"][uid])
            update_quest_earn(uid,win)
        else:
            await m.reply(f"🎡 <b>КОЛЕСО ФОРТУНЫ</b>\n\n{sector['name']}\n\n❌ ВЫ ПРОИГРАЛИ!\n💸 -{format_amount(bet)} GOLD", parse_mode="HTML")
            user_stats[uid]["played"]=user_stats[uid].get("played",0)+1
            user_stats[uid]["total_bet"]=user_stats[uid].get("total_bet",0)+bet
            user_levels[uid]=user_levels.get(uid,0)+1
            update_quest_progress(uid,"play_3_games")
            update_quest_progress(uid,"play_10_games")
            update_quest_progress(uid,"make_bet")
            update_quest_progress(uid,"make_5_bets")
            daily_quests["win_3_streak"]["current_streak"][uid]=0
        new_achs=check_achievements(uid)
        for ach in new_achs:
            await send_achievement_notify(uid,ach,m)
        new_titles=check_titles(uid)
        for title in new_titles:
            await send_title_notify(uid,title,m)
        new_badges=check_badges(uid)
        for badge in new_badges:
            await send_badge_notify(uid,badge,m)
        save_data()
        return
    
    # ========== РУЛЕТКА (ставки) ==========
    if len(parts)>=2:
        if game_in_progress:
            await m.reply("⏳ Идёт игра, подождите...")
            return
        try:
            amt=int(parts[0])
        except:
            return
        if amt<100:
            return await m.reply("❌ Минимальная ставка 100 GOLD")
        bets=" ".join(parts[1:]).split()
        if len(bets)>MAX_BETS_PER_MESSAGE:
            return await m.reply(f"❌ Максимум {MAX_BETS_PER_MESSAGE} ставок")
        total=amt*len(bets)
        bal=user_balances.get(uid,0)
        if total>bal:
            return await m.reply(f"❌ Нужно {format_amount(total)} GOLD")
        update_quest_progress(uid,"make_bet")
        update_quest_progress(uid,"make_5_bets")
        user_balances[uid]=bal-total
        save_data()
        acc=[]
        for b in bets:
            if not b:
                continue
            pending_bets.append({"user_id":uid,"user_name":name,"amount":amt,"raw_bet":b})
            acc.append(f"Ставка принята: {name} {format_amount(amt)} GOLD на {b}")
        for i in range(0,len(acc),5):
            await m.reply("<code>"+"\n".join(acc[i:i+5])+"</code>", parse_mode="HTML")
            await asyncio.sleep(0.5)
        return
    
    # ========== ЗАПУСК РУЛЕТКИ ==========
    if text.lower()=="го":
        now=int(time.time())
        if game_in_progress:
            await m.reply("⏳ Идёт игра, подождите...")
            return
        if now-last_game_time<GAME_COOLDOWN:
            await m.reply(f"⏰ Подожди {GAME_COOLDOWN-(now-last_game_time)} сек")
            return
        if not pending_bets:
            await m.reply("❌ Нет активных ставок")
            return
        game_in_progress=True
        last_game_time=time.time()
        try:
            gif=await m.answer_animation(ROULETTE_GIF,caption="🎰 Крутим...")
        except:
            gif=None
        await asyncio.sleep(10)
        if gif:
            try:
                await bot.delete_message(m.chat.id,gif.message_id)
            except:
                pass
        try:
            num,emoji,color=spin_roulette()
            game_history.append(f"{emoji} {num}")
            if len(game_history)>10:
                game_history.pop(0)
            all_bets,wins=[],[]
            for b in pending_bets:
                uname,amt,raw=b["user_name"],b["amount"],b["raw_bet"]
                all_bets.append(f"{uname} {format_amount(amt)} GOLD на {raw}")
                if check_win(raw,num,color):
                    mult=get_multiplier(raw)
                    win_amt=amt*mult
                    old_bal_bet=user_balances.get(b["user_id"],0)
                    user_balances[b["user_id"]]=user_balances.get(b["user_id"],0)+win_amt
                    new_rank=check_rank_up(b["user_id"],old_bal_bet,user_balances[b["user_id"]])
                    if new_rank:
                        await send_rank_up_notify(b["user_id"],new_rank,m)
                    if b["user_id"] not in user_stats:
                        user_stats[b["user_id"]]={"played":0,"won":0,"total_bet":0,"total_win":0}
                    user_stats[b["user_id"]]["played"]=user_stats[b["user_id"]].get("played",0)+1
                    user_stats[b["user_id"]]["won"]=user_stats[b["user_id"]].get("won",0)+1
                    user_stats[b["user_id"]]["total_bet"]=user_stats[b["user_id"]].get("total_bet",0)+amt
                    user_stats[b["user_id"]]["total_win"]=user_stats[b["user_id"]].get("total_win",0)+win_amt
                    user_levels[b["user_id"]]=user_levels.get(b["user_id"],0)+1
                    daily_quests["win_3_streak"]["current_streak"][b["user_id"]]=daily_quests["win_3_streak"]["current_streak"].get(b["user_id"],0)+1
                    update_quest_progress(b["user_id"],"win_3_streak",daily_quests["win_3_streak"]["current_streak"][b["user_id"]])
                    update_quest_progress(b["user_id"],"win_5_streak",daily_quests["win_3_streak"]["current_streak"][b["user_id"]])
                    update_quest_earn(b["user_id"],win_amt)
                    wins.append(f"{uname} выиграл {format_amount(win_amt)} GOLD на {raw}")
                else:
                    if b["user_id"] not in user_stats:
                        user_stats[b["user_id"]]={"played":0,"won":0,"total_bet":0,"total_win":0}
                    user_stats[b["user_id"]]["played"]=user_stats[b["user_id"]].get("played",0)+1
                    user_stats[b["user_id"]]["total_bet"]=user_stats[b["user_id"]].get("total_bet",0)+amt
                    user_levels[b["user_id"]]=user_levels.get(b["user_id"],0)+1
                    daily_quests["win_3_streak"]["current_streak"][b["user_id"]]=0
                update_quest_progress(b["user_id"],"play_3_games")
                update_quest_progress(b["user_id"],"play_10_games")
                update_quest_progress(b["user_id"],"make_bet")
                update_quest_progress(b["user_id"],"make_5_bets")
                new_achs=check_achievements(b["user_id"])
                for ach in new_achs:
                    await send_achievement_notify(b["user_id"],ach,m)
                new_titles=check_titles(b["user_id"])
                for title in new_titles:
                    await send_title_notify(b["user_id"],title,m)
                new_badges=check_badges(b["user_id"])
                for badge in new_badges:
                    await send_badge_notify(b["user_id"],badge,m)
            save_data()
            await m.answer(f"<code>🎲 РУЛЕТКА: {num} {emoji}</code>", parse_mode="HTML")
            for i in range(0,len(all_bets),50):
                await m.answer("<code>"+"\n".join(all_bets[i:i+50])+"</code>", parse_mode="HTML")
                await asyncio.sleep(0.5)
            for i in range(0,len(wins),50):
                await m.answer("<code>"+"\n".join(wins[i:i+50])+"</code>", parse_mode="HTML")
                await asyncio.sleep(0.5)
        except Exception as e:
            logging.error(f"Ошибка: {e}")
            await m.answer("❌ Ошибка, ставки возвращены")
            for b in pending_bets:
                user_balances[b["user_id"]]=user_balances.get(b["user_id"],0)+b["amount"]
        finally:
            pending_bets.clear()
            game_in_progress=False
            last_game_time=int(time.time())
        return

    # ========== БЛЭКДЖЕК ==========
    if text.lower().startswith("bj ") or text.lower().startswith("блекджек "):
        if game_in_progress:
            await m.reply("⏳ Идёт игра, подождите...")
            return
        if len(parts)<2:
            return await m.reply("❌ Пример: bj 100")
        try:
            bet=int(parts[1])
        except:
            return await m.reply("❌ Пример: bj 100")
        if bet<100:
            return await m.reply("❌ Минимальная ставка 100 GOLD")
        bal=user_balances.get(uid,0)
        if bet>bal:
            return await m.reply("❌ Недостаточно GOLD")
        old_bal=bal
        user_balances[uid]=bal-bet
        update_quest_progress(uid,"make_bet")
        deck=generate_deck()
        ph=[deck.pop(),deck.pop()]
        dh=[deck.pop(),deck.pop()]
        blackjack_games[uid]={"bet":bet,"deck":deck,"player_hand":ph,"dealer_hand":dh,"active":True}
        pv=hand_value(ph)
        if pv==21:
            win=int(bet*2.5)
            user_balances[uid]=user_balances.get(uid,0)+win
            new_rank=check_rank_up(uid,old_bal,user_balances[uid])
            if new_rank:
                await send_rank_up_notify(uid,new_rank,m)
            if uid not in user_stats:
                user_stats[uid]={"played":0,"won":0,"total_bet":0,"total_win":0,"bj_wins":0}
            user_stats[uid]["played"]=user_stats[uid].get("played",0)+1
            user_stats[uid]["won"]=user_stats[uid].get("won",0)+1
            user_stats[uid]["bj_wins"]=user_stats[uid].get("bj_wins",0)+1
            user_stats[uid]["total_bet"]=user_stats[uid].get("total_bet",0)+bet
            user_stats[uid]["total_win"]=user_stats[uid].get("total_win",0)+win
            user_levels[uid]=user_levels.get(uid,0)+2
            update_quest_progress(uid,"play_3_games")
            update_quest_progress(uid,"play_10_games")
            update_quest_progress(uid,"win_blackjack")
            daily_quests["win_3_streak"]["current_streak"][uid]=daily_quests["win_3_streak"]["current_streak"].get(uid,0)+1
            update_quest_progress(uid,"win_3_streak",daily_quests["win_3_streak"]["current_streak"][uid])
            update_quest_progress(uid,"win_5_streak",daily_quests["win_3_streak"]["current_streak"][uid])
            update_quest_earn(uid,win)
            new_achs=check_achievements(uid)
            for ach in new_achs:
                await send_achievement_notify(uid,ach,m)
            new_titles=check_titles(uid)
            for title in new_titles:
                await send_title_notify(uid,title,m)
            new_badges=check_badges(uid)
            for badge in new_badges:
                await send_badge_notify(uid,badge,m)
            del blackjack_games[uid]
            save_data()
            await m.reply(f"<code>🃏 БЛЭКДЖЕК!\n\n💰 +{format_amount(win)} GOLD</code>", parse_mode="HTML")
            return
        kb=InlineKeyboardMarkup(row_width=3)
        kb.add(
            InlineKeyboardButton("🃏 Взять",callback_data="bj_hit"),
            InlineKeyboardButton("✋ Хватит",callback_data="bj_stand"),
            InlineKeyboardButton("🏳️ Сдаюсь",callback_data="bj_surrender")
        )
        await m.reply(f"<code>🃏 БЛЭКДЖЕК\n💰 Ставка: {format_amount(bet)} GOLD\n\nВаши карты: {format_cards(ph)} ({pv})\nКарта дилера: {format_cards([dh[0]])}</code>", parse_mode="HTML", reply_markup=kb)
        return
    
    # ========== МИНЫ ==========
    if text.lower().startswith("мины "):
        if game_in_progress:
            await m.reply("⏳ Идёт игра, подождите...")
            return
        if len(parts)<2:
            return await m.reply("❌ Пример: мины 100")
        try:
            bet=int(parts[1])
        except:
            return await m.reply("❌ Пример: мины 100")
        if bet<100:
            return await m.reply("❌ Минимальная ставка 100 GOLD")
        bal=user_balances.get(uid,0)
        if bet>bal:
            return await m.reply("❌ Недостаточно GOLD")
        user_balances[uid]=bal-bet
        update_quest_progress(uid,"make_bet")
        field=generate_mines_field()
        mines_games[uid]={"bet":bet,"field":field,"revealed":[],"multiplier":1.0,"active":True}
        save_data()
        kb=get_mines_keyboard(field,[])
        await m.answer(f"💎 {name}\n📌 Ставка: {format_amount(bet)} GOLD\n💲 Выигрыш: x1.0 | {format_amount(bet)} GOLD\n\n{format_mines_field(field,[])}", reply_markup=kb)
        return
    
    # ========== ОТМЕНА СТАВОК ==========
    if text.lower() in["отмена","отменить"]:
        if game_in_progress:
            return await m.reply("⏳ Идёт игра")
        ub=[b for b in pending_bets if b["user_id"]==uid]
        if not ub:
            return await m.reply("❌ Нет ставок")
        refund=sum(b["amount"]for b in ub)
        pending_bets=[b for b in pending_bets if b["user_id"]!=uid]
        user_balances[uid]=user_balances.get(uid,0)+refund
        save_data()
        await m.reply(f"✅ Возвращено {format_amount(refund)} GOLD")
        return
    
    # ========== ПЕРЕВОДЫ ==========
    if m.reply_to_message and text.lower().strip()=='дать всё':
        tid=m.reply_to_message.from_user.id
        if uid==tid:
            return await m.reply("❌ Нельзя перевести самому себе")
        bal=user_balances.get(uid,0)
        if bal<=0:
            return await m.reply(f"❌ Нет GOLD для перевода")
        user_balances[uid]=0
        user_balances[tid]=user_balances.get(tid,0)+bal
        save_data()
        await m.reply(f"✅ Переведено {format_amount(bal)} GOLD пользователю {m.reply_to_message.from_user.full_name}")
        return
    
    if m.reply_to_message and text.lower().startswith('дать') and not text.lower().startswith('дать всё'):
        try:
            amt=int(text.split()[1])
            if amt<=0:
                raise
        except:
            return await m.reply("❌ Пример: дать 500")
        tid=m.reply_to_message.from_user.id
        if uid==tid:
            return await m.reply("❌ Нельзя перевести самому себе")
        bal=user_balances.get(uid,0)
        if bal<amt:
            return await m.reply(f"❌ Не хватает, баланс: {format_amount(bal)} GOLD")
        user_balances[uid]=bal-amt
        user_balances[tid]=user_balances.get(tid,0)+amt
        save_data()
        await m.reply(f"✅ Переведено {format_amount(amt)} GOLD пользователю {m.reply_to_message.from_user.full_name}")
        return
    
    # ========== ПОМОЩЬ ==========
    if text.lower() in["помощь","команды","help"]:
        await m.reply("<code>👑 GOLDEN GOLD ROULETTE\n\n🎲 ИГРЫ:\n├ Рулетка: 100 чёрное\n├ Кости: кости 500 на 7\n├ Слот: слот 100\n├ Колесо: колесо 100\n├ КНБ: кнб 500 камень\n├ Спорт: спорт 500 1\n├ Лотерея: лотерея 1000\n├ Мины: мины 100\n├ Блэкджек: bj 100\n├ Боулинг: боулинг 100\n├ Коробки: коробки 100 1\n├ Дартс: дартс 100\n├ Баскетбол: баскетбол 100\n\n📌 КОМАНДЫ:\n├ б - баланс\n├ профиль - статистика\n├ топ - топ игроков\n├ достижения - список достижений\n├ значки - список значков\n├ титулы - список титулов\n├ прогресс - прогресс\n├ престиж - престиж\n├ ранг - звание\n├ бонус - бонус\n├ задания - задания\n├ рефка - реферальная ссылка\n├ промокод Gold2026 - 100 000 GOLD\n├ го - запуск рулетки\n├ отмена - отмена ставок\n├ дать 500 (ответом)\n└ дать всё (ответом)</code>", parse_mode="HTML")
        return

# ========== КОЛБЭКИ БЛЭКДЖЕКА ==========
@dp.callback_query_handler(lambda c:c.data.startswith("bj_"))
async def bj_cb(call):
    await call.answer()
    uid=call.from_user.id
    if uid not in blackjack_games:
        return await call.message.edit_text("❌ Игра не найдена")
    g=blackjack_games[uid]
    if not g["active"]:
        return
    action=call.data[3:]
    if action=="hit":
        g["player_hand"].append(g["deck"].pop())
        pv=hand_value(g["player_hand"])
        if pv>21:
            g["active"]=False
            del blackjack_games[uid]
            if uid not in user_stats:
                user_stats[uid]={"played":0,"won":0,"total_bet":0,"total_win":0}
            user_stats[uid]["played"]=user_stats[uid].get("played",0)+1
            user_stats[uid]["total_bet"]=user_stats[uid].get("total_bet",0)+g["bet"]
            user_levels[uid]=user_levels.get(uid,0)+1
            update_quest_progress(uid,"play_3_games")
            update_quest_progress(uid,"play_10_games")
            daily_quests["win_3_streak"]["current_streak"][uid]=0
            new_achs=check_achievements(uid)
            for ach in new_achs:
                await send_achievement_notify(uid,ach,call.message)
            new_titles=check_titles(uid)
            for title in new_titles:
                await send_title_notify(uid,title,call.message)
            new_badges=check_badges(uid)
            for badge in new_badges:
                await send_badge_notify(uid,badge,call.message)
            save_data()
            await call.message.edit_text(f"<code>🃏 ПЕРЕБОР! ({pv})\n❌ -{format_amount(g['bet'])} GOLD</code>", parse_mode="HTML")
            return
        kb=InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton("🃏 Взять",callback_data="bj_hit"),
            InlineKeyboardButton("✋ Хватит",callback_data="bj_stand")
        )
        await call.message.edit_text(f"<code>🃏 БЛЭКДЖЕК\n💰 Ставка: {format_amount(g['bet'])} GOLD\n\nВаши карты: {format_cards(g['player_hand'])} ({pv})</code>", parse_mode="HTML", reply_markup=kb)
    elif action=="stand":
        g["active"]=False
        while hand_value(g["dealer_hand"])<17:
            g["dealer_hand"].append(g["deck"].pop())
        pv=hand_value(g["player_hand"])
        dv=hand_value(g["dealer_hand"])
        win=0
        if dv>21 or pv>dv:
            win=g["bet"]*2
        elif pv==dv:
            win=g["bet"]
        if win>0:
            user_balances[uid]=user_balances.get(uid,0)+win
        if uid not in user_stats:
            user_stats[uid]={"played":0,"won":0,"total_bet":0,"total_win":0,"bj_wins":0}
        user_stats[uid]["played"]=user_stats[uid].get("played",0)+1
        if win>g["bet"]:
            user_stats[uid]["won"]=user_stats[uid].get("won",0)+1
            user_stats[uid]["bj_wins"]=user_stats[uid].get("bj_wins",0)+1
        user_stats[uid]["total_bet"]=user_stats[uid].get("total_bet",0)+g["bet"]
        user_stats[uid]["total_win"]=user_stats[uid].get("total_win",0)+win
        user_levels[uid]=user_levels.get(uid,0)+1
        update_quest_progress(uid,"play_3_games")
        update_quest_progress(uid,"play_10_games")
        if win>g["bet"]:
            update_quest_progress(uid,"win_blackjack")
            daily_quests["win_3_streak"]["current_streak"][uid]=daily_quests["win_3_streak"]["current_streak"].get(uid,0)+1
            update_quest_progress(uid,"win_3_streak",daily_quests["win_3_streak"]["current_streak"][uid])
            update_quest_progress(uid,"win_5_streak",daily_quests["win_3_streak"]["current_streak"][uid])
            update_quest_earn(uid,win)
        else:
            daily_quests["win_3_streak"]["current_streak"][uid]=0
        new_achs=check_achievements(uid)
        for ach in new_achs:
            await send_achievement_notify(uid,ach,call.message)
        new_titles=check_titles(uid)
        for title in new_titles:
            await send_title_notify(uid,title,call.message)
        new_badges=check_badges(uid)
        for badge in new_badges:
            await send_badge_notify(uid,badge,call.message)
        del blackjack_games[uid]
        save_data()
        await call.message.edit_text(f"<code>🃏 ИГРА ОКОНЧЕНА\n\nВаши карты: {format_cards(g['player_hand'])} ({pv})\nКарты дилера: {format_cards(g['dealer_hand'])} ({dv})\n💰 +{format_amount(win) if win>0 else '0'} GOLD</code>", parse_mode="HTML")
    elif action=="surrender":
        g["active"]=False
        refund=g["bet"]//2
        user_balances[uid]=user_balances.get(uid,0)+refund
        if uid not in user_stats:
            user_stats[uid]={"played":0,"won":0,"total_bet":0,"total_win":0}
        user_stats[uid]["played"]=user_stats[uid].get("played",0)+1
        user_stats[uid]["total_bet"]=user_stats[uid].get("total_bet",0)+g["bet"]
        user_levels[uid]=user_levels.get(uid,0)+1
        update_quest_progress(uid,"play_3_games")
        update_quest_progress(uid,"play_10_games")
        del blackjack_games[uid]
        save_data()
        await call.message.edit_text(f"<code>🏳️ ВЫ СДАЛИСЬ\n💰 Возвращено {format_amount(refund)} GOLD</code>", parse_mode="HTML")

# ========== КОЛБЭКИ МИН ==========
@dp.callback_query_handler(lambda c:c.data.startswith("m_"))
async def mine_cb(call):
    await call.answer()
    uid=call.from_user.id
    if uid not in mines_games:
        return
    g=mines_games[uid]
    if not g["active"]:
        return
    _,r,c=call.data.split("_")
    r,c=int(r),int(c)
    if (r,c) in g["revealed"]:
        return
    g["revealed"].append((r,c))
    if g["field"][r][c]=="💣":
        g["active"]=False
        del mines_games[uid]
        update_quest_progress(uid,"play_3_games")
        update_quest_progress(uid,"play_10_games")
        daily_quests["win_3_streak"]["current_streak"][uid]=0
        new_achs=check_achievements(uid)
        for ach in new_achs:
            await send_achievement_notify(uid,ach,call.message)
        new_titles=check_titles(uid)
        for title in new_titles:
            await send_title_notify(uid,title,call.message)
        new_badges=check_badges(uid)
        for badge in new_badges:
            await send_badge_notify(uid,badge,call.message)
        save_data()
        await call.message.edit_text(f"💥 МИНА!\n❌ -{format_amount(g['bet'])} GOLD\n\n{format_mines_field(g['field'],g['revealed'])}")
        return
    g["multiplier"]+=0.14
    pot=int(g["bet"]*g["multiplier"])
    await call.message.edit_text(f"💎 {call.from_user.full_name}\n📌 Ставка: {format_amount(g['bet'])} GOLD\n💲 Выигрыш: x{g['multiplier']:.2f} | {format_amount(pot)} GOLD\n\n{format_mines_field(g['field'],g['revealed'])}", reply_markup=get_mines_keyboard(g['field'],g['revealed']))

@dp.callback_query_handler(lambda c:c.data=="cash")
async def mine_cash_cb(call):
    await call.answer()
    uid=call.from_user.id
    if uid not in mines_games:
        return
    g=mines_games[uid]
    if not g["active"]:
        return
    g["active"]=False
    win=int(g["bet"]*g["multiplier"])
    old_bal=user_balances.get(uid,0)
    user_balances[uid]=user_balances.get(uid,0)+win
    new_rank=check_rank_up(uid,old_bal,user_balances[uid])
    if new_rank:
        await send_rank_up_notify(uid,new_rank,call.message)
    if uid not in user_stats:
        user_stats[uid]={"played":0,"won":0,"total_bet":0,"total_win":0,"mines_wins":0}
    user_stats[uid]["played"]=user_stats[uid].get("played",0)+1
    user_stats[uid]["won"]=user_stats[uid].get("won",0)+1
    user_stats[uid]["mines_wins"]=user_stats[uid].get("mines_wins",0)+1
    user_stats[uid]["total_bet"]=user_stats[uid].get("total_bet",0)+g["bet"]
    user_stats[uid]["total_win"]=user_stats[uid].get("total_win",0)+win
    user_levels[uid]=user_levels.get(uid,0)+1
    update_quest_progress(uid,"play_3_games")
    update_quest_progress(uid,"play_10_games")
    update_quest_progress(uid,"win_mines")
    daily_quests["win_3_streak"]["current_streak"][uid]=daily_quests["win_3_streak"]["current_streak"].get(uid,0)+1
    update_quest_progress(uid,"win_3_streak",daily_quests["win_3_streak"]["current_streak"][uid])
    update_quest_progress(uid,"win_5_streak",daily_quests["win_3_streak"]["current_streak"][uid])
    update_quest_earn(uid,win)
    new_achs=check_achievements(uid)
    for ach in new_achs:
        await send_achievement_notify(uid,ach,call.message)
    new_titles=check_titles(uid)
    for title in new_titles:
        await send_title_notify(uid,title,call.message)
    new_badges=check_badges(uid)
    for badge in new_badges:
        await send_badge_notify(uid,badge,call.message)
    del mines_games[uid]
    save_data()
    await call.message.edit_text(f"💰 {call.from_user.full_name} забрал выигрыш!\n✅ +{format_amount(win)} GOLD\n💲 Итоговый множитель: x{g['multiplier']:.2f}\n\n{format_mines_field(g['field'],g['revealed'])}")

# ========== ЛОТЕРЕЯ (ФОНОВЫЙ ПРОЦЕСС) ==========
async def lottery_scheduler():
    global last_lottery_time, lottery_pool, user_lottery_tickets, user_stats
    while True:
        await asyncio.sleep(3600)
        if time.time() - last_lottery_time >= 3600:
            if user_lottery_tickets:
                total_tickets = sum(user_lottery_tickets.values())
                if total_tickets > 0:
                    winners_count = min(3, len(user_lottery_tickets))
                    winners = random.sample(list(user_lottery_tickets.keys()), winners_count)
                    prize_per_winner = lottery_pool // winners_count if winners_count > 0 else 0
                    for winner in winners:
                        user_balances[winner] = user_balances.get(winner, 0) + prize_per_winner
                        if winner not in user_stats:
                            user_stats[winner] = {}
                        user_stats[winner]["lottery_win"] = user_stats[winner].get("lottery_win", 0) + 1
                        try:
                            await bot.send_message(winner, f"🎉 <b>ЛОТЕРЕЯ!</b> 🎉\n\nТы выиграл {format_amount(prize_per_winner)} GOLD!", parse_mode="HTML")
                        except:
                            pass
                    lottery_pool = 0
                    user_lottery_tickets.clear()
                    last_lottery_time = time.time()
                    save_data()

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    load_data()
    init_quests()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(lottery_scheduler())
    executor.start_polling(dp, skip_updates=True)
