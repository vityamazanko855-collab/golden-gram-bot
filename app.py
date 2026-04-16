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

ADMIN_ID=6003768110
GAME_COOLDOWN=15
DAILY_BONUS_BASE=500
DAILY_BONUS_STREAK_MULTIPLIER=200
MAX_BETS_PER_MESSAGE=500
ROULETTE_GIF="https://i.gifer.com/3P1d3.gif"
DATA_FILE="bot_data.json"

daily_quests={}
last_quest_reset=int(time.time())

# ========== РАНГИ ==========
RANKS = [
    {"name": "🟢 НОВИЧОК", "need": 0, "reward": 0},
    {"name": "🔵 ИГРОК", "need": 10000, "reward": 5000},
    {"name": "🟣 ОПЫТНЫЙ", "need": 100000, "reward": 25000},
    {"name": "🟠 ПРОФИ", "need": 1000000, "reward": 100000},
    {"name": "🔴 ЛЕГЕНДА", "need": 10000000, "reward": 500000},
    {"name": "👑 КОРОЛЬ", "need": 50000000, "reward": 2000000}
]

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

# ========== СЛОТ-МАШИНА ==========
SLOT_SYMBOLS = ["🍒", "🍋", "🍊", "🔔", "💎", "7️⃣"]
SLOT_PAYOUTS = {
    ("💎", "💎", "💎"): 100,
    ("7️⃣", "7️⃣", "7️⃣"): 50,
    ("🔔", "🔔", "🔔"): 20,
    ("🍒", "🍒", "🍒"): 10,
    ("🍋", "🍋", "🍋"): 8,
    ("🍊", "🍊", "🍊"): 8,
}

def spin_slot():
    return [random.choice(SLOT_SYMBOLS) for _ in range(3)]

def get_slot_win(symbols):
    key = tuple(symbols)
    if key in SLOT_PAYOUTS:
        return SLOT_PAYOUTS[key]
    return 0

def format_slot(symbols):
    return " | ".join(symbols)

# ========== КОЛЕСО ФОРТУНЫ ==========
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
    total_prob = sum(s["prob"] for s in FORTUNE_WHEEL)
    r = random.randint(1, total_prob)
    current = 0
    for sector in FORTUNE_WHEEL:
        current += sector["prob"]
        if r <= current:
            return sector
    return FORTUNE_WHEEL[0]

# ========== АЧИВКИ ==========
achievements_data = {
    "millionaire": {"name": "💰 МИЛЛИОНЕР", "desc": "Накопить 1 000 000 GRAM", "reward": 100000, "need_balance": 1000000},
    "gambler": {"name": "🎲 АЗАРТНЫЙ", "desc": "Сыграть 100 игр", "reward": 50000, "need_games": 100},
    "winner": {"name": "🏆 ПОБЕДИТЕЛЬ", "desc": "Выиграть 50 раз", "reward": 75000, "need_wins": 50},
    "sapper": {"name": "💣 САПЁР", "desc": "Выиграть в минах 10 раз", "reward": 50000, "need_mines_wins": 10},
    "carder": {"name": "🃏 КАРТЁЖНИК", "desc": "Выиграть в блэкджек 25 раз", "reward": 50000, "need_bj_wins": 25},
    "streak": {"name": "🔥 СТРИКЕР", "desc": "Выиграть 5 раз подряд", "reward": 30000, "need_streak": 5},
    "slot_winner": {"name": "🎰 СЛОТ-МАСТЕР", "desc": "Выиграть джекпот в слотах", "reward": 50000, "need_jackpot": 1},
    "fortune": {"name": "🍀 ВЕЗУНЧИК", "desc": "Выиграть x50+ на колесе", "reward": 50000, "need_fortune": 50}
}

def check_achievements(uid):
    if uid not in user_achievements:
        user_achievements[uid] = []
    
    stats = user_stats.get(uid, {"played":0, "won":0, "total_bet":0, "total_win":0, "mines_wins":0, "bj_wins":0, "slot_jackpot":0, "max_fortune":0})
    current_streak = daily_quests["win_3_streak"]["current_streak"].get(uid, 0)
    balance = user_balances.get(uid, 0)
    
    new_achievements = []
    
    for ach_id, ach in achievements_data.items():
        if ach_id in user_achievements[uid]:
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
        
        if earned:
            user_achievements[uid].append(ach_id)
            user_balances[uid] = user_balances.get(uid, 0) + ach["reward"]
            new_achievements.append(ach)
            save_data()
    
    return new_achievements

def get_achievements_list(uid):
    if uid not in user_achievements:
        user_achievements[uid] = []
    
    lines = ["🏆 <b>ТВОИ ДОСТИЖЕНИЯ</b>\n"]
    
    for ach_id, ach in achievements_data.items():
        if ach_id in user_achievements[uid]:
            lines.append(f"✅ {ach['name']} - {ach['desc']} (+{format_amount(ach['reward'])} GRAM)")
        else:
            lines.append(f"❌ {ach['name']} - {ach['desc']}")
    
    return "\n".join(lines)

# ========== КОСТИ ==========
VALID_DICE_BETS = ["2","3","4","5","6","7","8","9","10","11","12","дубль","чёт","нечёт","больше","меньше"]

def roll_dice():
    return random.randint(1, 6), random.randint(1, 6)

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

# ========== ОСТАЛЬНЫЕ ФУНКЦИИ ==========
def format_amount(a): return f"{a:,}".replace(","," ")
def get_level(e):
 if e<10:return 1
 elif e<30:return 2
 elif e<60:return 3
 elif e<100:return 4
 else:return 5

def load_data():
 global user_balances,user_stats,user_levels,daily_streak,game_history,daily_quests,last_quest_reset,user_achievements
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
 except:pass

def save_data():
 with open(DATA_FILE,"w")as f:
  json.dump({"user_balances":user_balances,"user_stats":user_stats,"user_levels":user_levels,"daily_streak":daily_streak,"game_history":game_history[-50:],"daily_quests":daily_quests,"last_quest_reset":last_quest_reset,"user_achievements":user_achievements},f,ensure_ascii=False,indent=2)

def init_quests():
 global daily_quests
 if not daily_quests:
  daily_quests={
   "play_3_games":{"name":"🎲 Сыграть 3 игры","target":3,"reward":30000,"progress":{},"completed":{}},
   "win_3_streak":{"name":"🏆 Выиграть 3 раза подряд","target":3,"reward":25000,"progress":{},"completed":{},"current_streak":{}},
   "make_bet":{"name":"💰 Сделать любую ставку","target":1,"reward":10000,"progress":{},"completed":{}}
  }

def check_quests_reset():
 global last_quest_reset
 if int(time.time())-last_quest_reset>=86400:
  for q in daily_quests:
   daily_quests[q]["progress"]={}
   daily_quests[q]["completed"]={}
   if q=="win_3_streak":daily_quests[q]["current_streak"]={}
  last_quest_reset=int(time.time())
  save_data()
  return True
 return False

def update_quest_progress(uid,qid,inc=1):
 global user_balances
 check_quests_reset()
 if uid in daily_quests[qid].get("completed",{}):return 0
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

def get_quests_status(uid):
 check_quests_reset()
 lines=[]
 for qid,q in daily_quests.items():
  prog=q["progress"].get(uid,0)
  if uid in q.get("completed",{}):
   lines.append(f"\n  └ {q['name']}: ✅ ВЫПОЛНЕНО (+{format_amount(q['reward'])} GRAM)")
  else:
   lines.append(f"\n  └ {q['name']}: 📊 {prog}/{q['target']}")
 return "\n".join(lines)

def get_main_keyboard():
 kb=InlineKeyboardMarkup(row_width=2)
 kb.add(
  InlineKeyboardButton("💰 Баланс",callback_data="menu_balance"),
  InlineKeyboardButton("📊 Профиль",callback_data="menu_profile"),
  InlineKeyboardButton("🎲 Рулетка",callback_data="menu_roulette"),
  InlineKeyboardButton("🎲 Кости",callback_data="menu_dice"),
  InlineKeyboardButton("🎰 Слот",callback_data="menu_slot"),
  InlineKeyboardButton("🎡 Колесо",callback_data="menu_wheel"),
  InlineKeyboardButton("💣 Мины",callback_data="menu_mines"),
  InlineKeyboardButton("🃏 Блэкджек",callback_data="menu_blackjack"),
  InlineKeyboardButton("🎁 Задания",callback_data="menu_quests"),
  InlineKeyboardButton("🏆 Топ",callback_data="menu_top"),
  InlineKeyboardButton("🏅 Ачивки",callback_data="menu_achievements"),
  InlineKeyboardButton("❓ Помощь",callback_data="menu_help")
 )
 return kb

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

def generate_mines_field():
 f=[["⭐" for _ in range(5)] for _ in range(5)]
 for m in random.sample(range(25),3):f[m//5][m%5]="💣"
 return f

def format_mines_field(field,revealed):
 return "\n".join(" ".join(field[i][j] if(i,j)in revealed else"❓"for j in range(5))for i in range(5))

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
 while v>21 and aces>0:v-=10;aces-=1
 return v

def format_cards(hand):
 return " ".join(f"{r}{s}"for r,s in hand)if hand else"пусто"

def get_mines_keyboard(field,revealed):
 kb=InlineKeyboardMarkup(row_width=5)
 for i in range(5):
  row=[]
  for j in range(5):
   if(i,j)in revealed:row.append(InlineKeyboardButton(field[i][j],callback_data="done"))
   else:row.append(InlineKeyboardButton("❓",callback_data=f"m_{i}_{j}"))
  kb.row(*row)
 if revealed:kb.add(InlineKeyboardButton("💰 Забрать выигрыш",callback_data="cash"))
 return kb

async def send_quest_notify(uid,qid,reward,msg=None):
 name=daily_quests[qid]["name"]
 text=f"🎉 <b>ЗАДАНИЕ ВЫПОЛНЕНО!</b> 🎉\n\n📋 {name}\n💰 Награда: +{format_amount(reward)} GRAM\n\n💳 Баланс: {format_amount(user_balances.get(uid,0))} GRAM"
 try:
  if msg:await msg.reply(text,parse_mode="HTML")
  else:await bot.send_message(uid,text,parse_mode="HTML")
 except:pass

async def send_achievement_notify(uid,ach,msg=None):
 text=f"🏆 <b>ДОСТИЖЕНИЕ ПОЛУЧЕНО!</b> 🏆\n\n{ach['name']}\n{ach['desc']}\n\n💰 Награда: +{format_amount(ach['reward'])} GRAM"
 try:
  if msg:await msg.reply(text,parse_mode="HTML")
  else:await bot.send_message(uid,text,parse_mode="HTML")
 except:pass

async def send_rank_up_notify(uid,rank,msg=None):
 text=f"⭐ <b>НОВЫЙ РАНГ!</b> ⭐\n\n{rank['name']}\n\n💰 Бонус: +{format_amount(rank['reward'])} GRAM"
 try:
  if msg:await msg.reply(text,parse_mode="HTML")
  else:await bot.send_message(uid,text,parse_mode="HTML")
 except:pass

def force_reset_game():
 global game_in_progress, pending_bets
 game_in_progress = False
 pending_bets.clear()

@dp.message_handler(commands=["start"])
async def start_cmd(m):
 init_quests()
 force_reset_game()
 await m.reply(
  "<code>🎰 GOLDEN GRAM ROULETTE\n\n"
  "🎲 СТАВКИ:\n├ 100 чёрное\n├ 250 красное\n├ 500 чётное\n├ 1000 14\n├ 2000 0\n└ 5000 1-12\n\n"
  "🎲 КОСТИ: кости 500 на 7\n"
  "🎰 СЛОТ: слот 100\n"
  "🎡 КОЛЕСО: колесо 100\n"
  "💣 МИНЫ: мины 100\n"
  "🃏 БЛЭКДЖЕК: bj 100\n\n"
  "📌 КОМАНДЫ:\n├ б - баланс\n├ профиль - статистика\n├ топ - топ игроков\n├ ачивки - достижения\n├ ранг - твой ранг\n├ бонус - бонус\n├ задания - задания\n├ го - запуск\n├ отмена - отмена ставок\n├ дать 500 (ответом)\n└ дать всё (ответом)</code>",
  parse_mode="HTML",
  reply_markup=get_main_keyboard()
 )

@dp.message_handler(commands=["add_grams"])
async def add_grams(m):
 if m.from_user.id!=ADMIN_ID:return await m.reply("❌ Нет прав")
 try:
  amt=int(m.text.split()[1])
  user_balances[ADMIN_ID]=user_balances.get(ADMIN_ID,0)+amt
  save_data()
  await m.reply(f"✅ +{format_amount(amt)} GRAM")
 except:await m.reply("❌ /add_grams 5000")

@dp.callback_query_handler(lambda c:c.data.startswith("menu_"))
async def menu_cb(call):
 await call.answer()
 uid=call.from_user.id
 act=call.data[5:]
 if act=="balance":
  await call.message.edit_text(f"💰 <b>Ваш баланс</b>\n\n└ {format_amount(user_balances.get(uid,0))} GRAM",parse_mode="HTML",reply_markup=get_main_keyboard())
 elif act=="profile":
  name=call.from_user.full_name
  bal=user_balances.get(uid,0)
  s=user_stats.get(uid,{"played":0,"won":0,"total_bet":0,"total_win":0})
  lvl=get_level(user_levels.get(uid,0))
  rank=get_rank(bal)
  wr=(s["won"]/s["played"]*100)if s["played"]>0 else 0
  prof=s["total_win"]-s["total_bet"]
  await call.message.edit_text(f"👤 <b>{name}</b>\n├ 🆔 {uid}\n├ 📊 Уровень: {lvl}\n├ 🏅 Ранг: {rank['name']}\n└ 💰 {format_amount(bal)} GRAM\n\n📊 <b>Статистика</b>\n├ 🎲 Игр: {s['played']}\n├ 🏆 Побед: {s['won']}\n├ 📈 Винрейт: {wr:.1f}%\n└ 📊 Профит: {format_amount(prof)} GRAM",parse_mode="HTML",reply_markup=get_main_keyboard())
 elif act=="quests":
  await call.message.edit_text(f"🎯 <b>ЕЖЕДНЕВНЫЕ ЗАДАНИЯ</b>{get_quests_status(uid)}\n\n⏰ Обновляются каждые 24 часа\n✨ Награда выдается автоматически!",parse_mode="HTML",reply_markup=get_main_keyboard())
 elif act=="achievements":
  await call.message.edit_text(get_achievements_list(uid),parse_mode="HTML",reply_markup=get_main_keyboard())
 elif act=="top":
  if not user_balances:return await call.message.edit_text("📊 Пусто",reply_markup=get_main_keyboard())
  items=sorted(user_balances.items(),key=lambda x:x[1],reverse=True)[:10]
  txt="🏆 <b>ТОП-10 ИГРОКОВ</b>\n\n"
  for i,(u,b)in enumerate(items,1):
   try:n=(await bot.get_chat(u)).full_name
   except:n=str(u)
   txt+=f"{i}. {n}\n└ {format_amount(b)} GRAM\n\n"
  await call.message.edit_text(txt,parse_mode="HTML",reply_markup=get_main_keyboard())
 else:
  texts={
   "roulette":"🎲 <b>СТАВКИ НА РУЛЕТКУ</b>\n\n├ 100 чёрное\n├ 250 красное\n├ 500 чётное\n├ 1000 14\n├ 2000 0\n└ 5000 1-12",
   "dice":"🎲 <b>ИГРА КОСТИ</b>\n\n├ Команда: кости 500 на 7\n├ кости 500 на дубль\n├ кости 500 на чёт\n├ кости 500 на нечёт\n├ кости 500 на больше\n└ кости 500 на меньше",
   "slot":"🎰 <b>СЛОТ-МАШИНА</b>\n\n├ Команда: слот 100\n├ 🍒🍒🍒 = x10\n├ 🍋🍋🍋 = x8\n├ 🍊🍊🍊 = x8\n├ 🔔🔔🔔 = x20\n├ 7️⃣7️⃣7️⃣ = x50\n└ 💎💎💎 = ДЖЕКПОТ x100",
   "wheel":"🎡 <b>КОЛЕСО ФОРТУНЫ</b>\n\n├ Команда: колесо 100\n├ Множители от x0 до x100\n└ Удачи!",
   "mines":"💣 <b>ИГРА МИНЫ</b>\n\n├ Команда: мины 100\n├ Поле 5x5, 3 мины\n├ Каждая клетка +0.14x\n└ Максимум x4.0",
   "blackjack":"🃏 <b>БЛЭКДЖЕК</b>\n\n├ Команда: bj 100\n├ Мин. ставка: 100\n├ Блэкджек: x2.5\n├ Победа: x2\n└ Сдача: 50%",
   "help":"🎰 <b>GOLDEN GRAM ROULETTE</b>\n\n🎲 СТАВКИ:\n├ 100 чёрное\n├ 250 красное\n├ 500 чётное\n├ 1000 14\n├ 2000 0\n└ 5000 1-12\n\n🎲 КОСТИ: кости 500 на 7\n🎰 СЛОТ: слот 100\n🎡 КОЛЕСО: колесо 100\n💣 МИНЫ: мины 100\n🃏 БЛЭКДЖЕК: bj 100\n\n📌 КОМАНДЫ:\n├ б - баланс\n├ профиль - статистика\n├ топ - топ игроков\n├ ачивки - достижения\n├ ранг - твой ранг\n├ бонус - бонус\n├ задания - задания\n├ го - запуск\n├ отмена - отмена ставок\n├ дать 500 (ответом)\n└ дать всё (ответом)"
  }
  await call.message.edit_text(texts.get(act,"❓ Помощь"),parse_mode="HTML",reply_markup=get_main_keyboard())

@dp.message_handler()
async def handle(m):
 global pending_bets,game_in_progress,last_game_time,game_history
 
 if game_in_progress and time.time() - last_game_time > 60:
  force_reset_game()
  await m.reply("⚠️ Предыдущая игра принудительно завершена (таймаут)")
 
 uid=m.from_user.id
 name=m.from_user.full_name
 text=m.text.strip()
 if text.lower().startswith('/'):return
 parts=text.split()
 
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
   await m.reply(f"🏅 <b>ТВОЙ РАНГ</b>\n\n{rank['name']}\n\n📊 До следующего ранга ({next_rank['name']}):\n└ {format_amount(need)} GRAM",parse_mode="HTML")
  else:
   await m.reply(f"🏅 <b>ТВОЙ РАНГ</b>\n\n{rank['name']}\n\n👑 Ты достиг максимального ранга!",parse_mode="HTML")
  return
 
 # ========== СЛОТ-МАШИНА ==========
 if text.lower().startswith("слот "):
  if len(parts)<2:return await m.reply("❌ Пример: слот 100")
  try:bet=int(parts[1])
  except:return await m.reply("❌ Пример: слот 100")
  if bet<100:return await m.reply("❌ Минимальная ставка 100 GRAM")
  bal=user_balances.get(uid,0)
  if bet>bal:return await m.reply(f"❌ Недостаточно GRAM, баланс: {format_amount(bal)}")
  
  user_balances[uid]=bal-bet
  symbols=spin_slot()
  mult=get_slot_win(symbols)
  
  # Обновляем статистику джекпота
  if uid not in user_stats:user_stats[uid]={"played":0,"won":0,"total_bet":0,"total_win":0,"slot_jackpot":0}
  if symbols==["💎","💎","💎"]:
   user_stats[uid]["slot_jackpot"]=user_stats[uid].get("slot_jackpot",0)+1
  
  if mult>0:
   win=bet*mult
   user_balances[uid]=user_balances.get(uid,0)+win
   await m.reply(f"🎰 <b>СЛОТ-МАШИНА</b>\n\n{format_slot(symbols)}\n\n✅ ВЫ ВЫИГРАЛИ!\n💰 +{format_amount(win)} GRAM (x{mult})",parse_mode="HTML")
   if uid not in user_stats:user_stats[uid]={"played":0,"won":0,"total_bet":0,"total_win":0}
   user_stats[uid]["played"]=user_stats[uid].get("played",0)+1
   user_stats[uid]["won"]=user_stats[uid].get("won",0)+1
   user_stats[uid]["total_bet"]=user_stats[uid].get("total_bet",0)+bet
   user_stats[uid]["total_win"]=user_stats[uid].get("total_win",0)+win
   user_levels[uid]=user_levels.get(uid,0)+1
   rew=update_quest_progress(uid,"play_3_games")
   if rew:await send_quest_notify(uid,"play_3_games",rew,m)
   daily_quests["win_3_streak"]["current_streak"][uid]=daily_quests["win_3_streak"]["current_streak"].get(uid,0)+1
   rew2=update_quest_progress(uid,"win_3_streak",daily_quests["win_3_streak"]["current_streak"][uid])
   if rew2:await send_quest_notify(uid,"win_3_streak",rew2,m)
  else:
   await m.reply(f"🎰 <b>СЛОТ-МАШИНА</b>\n\n{format_slot(symbols)}\n\n❌ ВЫ ПРОИГРАЛИ!\n💸 -{format_amount(bet)} GRAM",parse_mode="HTML")
   if uid not in user_stats:user_stats[uid]={"played":0,"won":0,"total_bet":0,"total_win":0}
   user_stats[uid]["played"]=user_stats[uid].get("played",0)+1
   user_stats[uid]["total_bet"]=user_stats[uid].get("total_bet",0)+bet
   user_levels[uid]=user_levels.get(uid,0)+1
   rew=update_quest_progress(uid,"play_3_games")
   if rew:await send_quest_notify(uid,"play_3_games",rew,m)
   daily_quests["win_3_streak"]["current_streak"][uid]=0
  new_achs=check_achievements(uid)
  for ach in new_achs:await send_achievement_notify(uid,ach,m)
  save_data()
  return
 
 # ========== КОЛЕСО ФОРТУНЫ ==========
 if text.lower().startswith("колесо "):
  if len(parts)<2:return await m.reply("❌ Пример: колесо 100")
  try:bet=int(parts[1])
  except:return await m.reply("❌ Пример: колесо 100")
  if bet<100:return await m.reply("❌ Минимальная ставка 100 GRAM")
  bal=user_balances.get(uid,0)
  if bet>bal:return await m.reply(f"❌ Недостаточно GRAM, баланс: {format_amount(bal)}")
  
  user_balances[uid]=bal-bet
  sector=spin_wheel()
  mult=sector["mult"]
  
  # Обновляем статистику колеса
  if uid not in user_stats:user_stats[uid]={"played":0,"won":0,"total_bet":0,"total_win":0,"max_fortune":0}
  if mult>user_stats[uid].get("max_fortune",0):
   user_stats[uid]["max_fortune"]=mult
  
  if mult>0:
   win=bet*mult
   user_balances[uid]=user_balances.get(uid,0)+win
   await m.reply(f"🎡 <b>КОЛЕСО ФОРТУНЫ</b>\n\n{sector['name']}\n\n✅ ВЫ ВЫИГРАЛИ!\n💰 +{format_amount(win)} GRAM (x{mult})",parse_mode="HTML")
   if uid not in user_stats:user_stats[uid]={"played":0,"won":0,"total_bet":0,"total_win":0}
   user_stats[uid]["played"]=user_stats[uid].get("played",0)+1
   user_stats[uid]["won"]=user_stats[uid].get("won",0)+1
   user_stats[uid]["total_bet"]=user_stats[uid].get("total_bet",0)+bet
   user_stats[uid]["total_win"]=user_stats[uid].get("total_win",0)+win
   user_levels[uid]=user_levels.get(uid,0)+1
   rew=update_quest_progress(uid,"play_3_games")
   if rew:await send_quest_notify(uid,"play_3_games",rew,m)
   daily_quests["win_3_streak"]["current_streak"][uid]=daily_quests["win_3_streak"]["current_streak"].get(uid,0)+1
   rew2=update_quest_progress(uid,"win_3_streak",daily_quests["win_3_streak"]["current_streak"][uid])
   if rew2:await send_quest_notify(uid,"win_3_streak",rew2,m)
  else:
   await m.reply(f"🎡 <b>КОЛЕСО ФОРТУНЫ</b>\n\n{sector['name']}\n\n❌ ВЫ ПРОИГРАЛИ!\n💸 -{format_amount(bet)} GRAM",parse_mode="HTML")
   if uid not in user_stats:user_stats[uid]={"played":0,"won":0,"total_bet":0,"total_win":0}
   user_stats[uid]["played"]=user_stats[uid].get("played",0)+1
   user_stats[uid]["total_bet"]=user_stats[uid].get("total_bet",0)+bet
   user_levels[uid]=user_levels.get(uid,0)+1
   rew=update_quest_progress(uid,"play_3_games")
   if rew:await send_quest_notify(uid,"play_3_games",rew,m)
   daily_quests["win_3_streak"]["current_streak"][uid]=0
  new_achs=check_achievements(uid)
  for ach in new_achs:await send_achievement_notify(uid,ach,m)
  save_data()
  return
 
 # ========== КОСТИ ==========
 if text.lower().startswith("кости "):
  if len(parts)<3:
   await m.reply("❌ Пример: кости 500 на 7\nВарианты: на [2-12], на дубль, на чёт, на нечёт, на больше, на меньше")
   return
  try:bet=int(parts[1])
  except:
   await m.reply("❌ Пример: кости 500 на 7")
   return
  if bet<100:
   await m.reply("❌ Минимальная ставка 100 GRAM")
   return
  
  bet_type = " ".join(parts[2:]).lower()
  
  if bet_type not in VALID_DICE_BETS:
   await m.reply(f"❌ Неверный тип ставки!\nВарианты: на [2-12], на дубль, на чёт, на нечёт, на больше, на меньше\nПример: кости 500 на 7")
   return
  
  bal=user_balances.get(uid,0)
  if bet>bal:
   await m.reply(f"❌ Недостаточно GRAM, баланс: {format_amount(bal)}")
   return
  
  old_bal=bal
  user_balances[uid]=bal-bet
  d1,d2=roll_dice()
  mult=get_dice_multiplier(bet_type,d1,d2)
  
  if mult>0:
   win=bet*mult
   user_balances[uid]=user_balances.get(uid,0)+win
   # Проверяем повышение ранга
   new_rank=check_rank_up(uid, old_bal, user_balances[uid])
   if new_rank:await send_rank_up_notify(uid,new_rank,m)
   await m.reply(f"🎲 <b>КОСТИ</b>\n\n{format_dice(d1,d2)}\nСумма: {d1+d2}\n\n✅ ВЫ ВЫИГРАЛИ!\n💰 +{format_amount(win)} GRAM (x{mult})",parse_mode="HTML")
   if uid not in user_stats:user_stats[uid]={"played":0,"won":0,"total_bet":0,"total_win":0}
   user_stats[uid]["played"]=user_stats[uid].get("played",0)+1
   user_stats[uid]["won"]=user_stats[uid].get("won",0)+1
   user_stats[uid]["total_bet"]=user_stats[uid].get("total_bet",0)+bet
   user_stats[uid]["total_win"]=user_stats[uid].get("total_win",0)+win
   user_levels[uid]=user_levels.get(uid,0)+1
   rew=update_quest_progress(uid,"play_3_games")
   if rew:await send_quest_notify(uid,"play_3_games",rew,m)
   daily_quests["win_3_streak"]["current_streak"][uid]=daily_quests["win_3_streak"]["current_streak"].get(uid,0)+1
   rew2=update_quest_progress(uid,"win_3_streak",daily_quests["win_3_streak"]["current_streak"][uid])
   if rew2:await send_quest_notify(uid,"win_3_streak",rew2,m)
  else:
   await m.reply(f"🎲 <b>КОСТИ</b>\n\n{format_dice(d1,d2)}\nСумма: {d1+d2}\n\n❌ ВЫ ПРОИГРАЛИ!\n💸 -{format_amount(bet)} GRAM",parse_mode="HTML")
   if uid not in user_stats:user_stats[uid]={"played":0,"won":0,"total_bet":0,"total_win":0}
   user_stats[uid]["played"]=user_stats[uid].get("played",0)+1
   user_stats[uid]["total_bet"]=user_stats[uid].get("total_bet",0)+bet
   user_levels[uid]=user_levels.get(uid,0)+1
   rew=update_quest_progress(uid,"play_3_games")
   if rew:await send_quest_notify(uid,"play_3_games",rew,m)
   daily_quests["win_3_streak"]["current_streak"][uid]=0
  new_achs=check_achievements(uid)
  for ach in new_achs:await send_achievement_notify(uid,ach,m)
  save_data()
  return
 
 # ========== ОСТАЛЬНЫЕ КОМАНДЫ ==========
 if m.reply_to_message and text.lower().strip()=='дать всё':
  tid=m.reply_to_message.from_user.id
  if uid==tid:return await m.reply("❌ Нельзя перевести самому себе")
  bal=user_balances.get(uid,0)
  if bal<=0:return await m.reply(f"❌ Нет GRAM для перевода")
  user_balances[uid]=0
  user_balances[tid]=user_balances.get(tid,0)+bal
  save_data()
  await m.reply(f"✅ Переведено {format_amount(bal)} GRAM пользователю {m.reply_to_message.from_user.full_name}")
  return
 if m.reply_to_message and text.lower().startswith('дать') and not text.lower().startswith('дать всё'):
  try:
   amt=int(text.split()[1])
   if amt<=0:raise
  except:return await m.reply("❌ Пример: дать 500")
  tid=m.reply_to_message.from_user.id
  if uid==tid:return await m.reply("❌ Нельзя перевести самому себе")
  bal=user_balances.get(uid,0)
  if bal<amt:return await m.reply(f"❌ Не хватает, баланс: {format_amount(bal)} GRAM")
  user_balances[uid]=bal-amt
  user_balances[tid]=user_balances.get(tid,0)+amt
  save_data()
  await m.reply(f"✅ Переведено {format_amount(amt)} GRAM пользователю {m.reply_to_message.from_user.full_name}")
  return
 if text.lower().startswith("bj ") or text.lower().startswith("блекджек "):
  if game_in_progress:
   await m.reply("⏳ Идёт игра, подождите...")
   return
  if len(parts)<2:return await m.reply("❌ Пример: bj 100")
  try:bet=int(parts[1])
  except:return await m.reply("❌ Пример: bj 100")
  if bet<100:return await m.reply("❌ Минимальная ставка 100 GRAM")
  bal=user_balances.get(uid,0)
  if bet>bal:return await m.reply("❌ Недостаточно GRAM")
  old_bal=bal
  user_balances[uid]=bal-bet
  rew=update_quest_progress(uid,"make_bet")
  if rew:await send_quest_notify(uid,"make_bet",rew,m)
  deck=generate_deck()
  ph=[deck.pop(),deck.pop()]
  dh=[deck.pop(),deck.pop()]
  blackjack_games[uid]={"bet":bet,"deck":deck,"player_hand":ph,"dealer_hand":dh,"active":True}
  pv=hand_value(ph)
  if pv==21:
   win=int(bet*2.5)
   user_balances[uid]=user_balances.get(uid,0)+win
   new_rank=check_rank_up(uid, old_bal, user_balances[uid])
   if new_rank:await send_rank_up_notify(uid,new_rank,m)
   if uid not in user_stats:user_stats[uid]={"played":0,"won":0,"total_bet":0,"total_win":0,"bj_wins":0}
   user_stats[uid]["played"]=user_stats[uid].get("played",0)+1
   user_stats[uid]["won"]=user_stats[uid].get("won",0)+1
   user_stats[uid]["bj_wins"]=user_stats[uid].get("bj_wins",0)+1
   user_stats[uid]["total_bet"]=user_stats[uid].get("total_bet",0)+bet
   user_stats[uid]["total_win"]=user_stats[uid].get("total_win",0)+win
   user_levels[uid]=user_levels.get(uid,0)+2
   rew2=update_quest_progress(uid,"play_3_games")
   if rew2:await send_quest_notify(uid,"play_3_games",rew2,m)
   daily_quests["win_3_streak"]["current_streak"][uid]=daily_quests["win_3_streak"]["current_streak"].get(uid,0)+1
   rew3=update_quest_progress(uid,"win_3_streak",daily_quests["win_3_streak"]["current_streak"][uid])
   if rew3:await send_quest_notify(uid,"win_3_streak",rew3,m)
   new_achs=check_achievements(uid)
   for ach in new_achs:await send_achievement_notify(uid,ach,m)
   del blackjack_games[uid]
   save_data()
   await m.reply(f"<code>🃏 БЛЭКДЖЕК!\n\n💰 +{format_amount(win)} GRAM</code>",parse_mode="HTML")
   return
  kb=InlineKeyboardMarkup(row_width=3)
  kb.add(InlineKeyboardButton("🃏 Взять",callback_data="bj_hit"),InlineKeyboardButton("✋ Хватит",callback_data="bj_stand"),InlineKeyboardButton("🏳️ Сдаюсь",callback_data="bj_surrender"))
  await m.reply(f"<code>🃏 БЛЭКДЖЕК\n💰 Ставка: {format_amount(bet)} GRAM\n\nВаши карты: {format_cards(ph)} ({pv})\nКарта дилера: {format_cards([dh[0]])}</code>",parse_mode="HTML",reply_markup=kb)
  return
 if text.lower().startswith("мины "):
  if game_in_progress:
   await m.reply("⏳ Идёт игра, подождите...")
   return
  if len(parts)<2:return await m.reply("❌ Пример: мины 100")
  try:bet=int(parts[1])
  except:return await m.reply("❌ Пример: мины 100")
  if bet<100:return await m.reply("❌ Минимальная ставка 100 GRAM")
  bal=user_balances.get(uid,0)
  if bet>bal:return await m.reply("❌ Недостаточно GRAM")
  user_balances[uid]=bal-bet
  rew=update_quest_progress(uid,"make_bet")
  if rew:await send_quest_notify(uid,"make_bet",rew,m)
  field=generate_mines_field()
  mines_games[uid]={"bet":bet,"field":field,"revealed":[],"multiplier":1.0,"active":True}
  save_data()
  kb=get_mines_keyboard(field,[])
  await m.answer(f"💎 {name}\n📌 Ставка: {format_amount(bet)} GRAM\n💲 Выигрыш: x1.0 | {format_amount(bet)} GRAM\n\n{format_mines_field(field,[])}",reply_markup=kb)
  return
 if text.lower() in["отмена","отменить"]:
  if game_in_progress:return await m.reply("⏳ Идёт игра")
  ub=[b for b in pending_bets if b["user_id"]==uid]
  if not ub:return await m.reply("❌ Нет ставок")
  refund=sum(b["amount"]for b in ub)
  pending_bets=[b for b in pending_bets if b["user_id"]!=uid]
  user_balances[uid]=user_balances.get(uid,0)+refund
  save_data()
  await m.reply(f"✅ Возвращено {format_amount(refund)} GRAM")
  return
 if text.lower() in["профиль","profile"]:
  bal=user_balances.get(uid,0)
  s=user_stats.get(uid,{"played":0,"won":0,"total_bet":0,"total_win":0})
  lvl=get_level(user_levels.get(uid,0))
  rank=get_rank(bal)
  wr=(s["won"]/s["played"]*100)if s["played"]>0 else 0
  prof=s["total_win"]-s["total_bet"]
  await m.reply(f"<code>👤 {name}\n🆔 {uid}\n📊 Уровень: {lvl}\n🏅 Ранг: {rank['name']}\n💰 {format_amount(bal)} GRAM\n\n🎲 Игр: {s['played']}\n🏆 Побед: {s['won']}\n📈 Винрейт: {wr:.1f}%\n📊 Профит: {format_amount(prof)} GRAM</code>",parse_mode="HTML")
  return
 if text.lower() in["ачивки","achievements"]:
  await m.reply(get_achievements_list(uid),parse_mode="HTML")
  return
 if text.lower()=="бонус":
  now=int(time.time())
  ds=daily_streak.get(uid,{"last":0,"streak":0})
  if now-ds["last"]>=86400:
   if now-ds["last"]>=172800:ds["streak"]=0
   ds["streak"]+=1
   bonus=DAILY_BONUS_BASE+(ds["streak"]-1)*DAILY_BONUS_STREAK_MULTIPLIER
   user_balances[uid]=user_balances.get(uid,0)+bonus
   ds["last"]=now
   daily_streak[uid]=ds
   save_data()
   await m.reply(f"<code>🎁 +{format_amount(bonus)} GRAM\n🔥 Стрик: {ds['streak']} дн.</code>",parse_mode="HTML")
  else:
   rem=86400-(now-ds["last"])
   await m.reply(f"<code>⏰ Через {rem//3600} ч {(rem%3600)//60} мин</code>",parse_mode="HTML")
  return
 if text.lower() in["б","баланс"]:
  await m.reply(f"<code>{name}\n💰 Баланс: {format_amount(user_balances.get(uid,0))} GRAM</code>",parse_mode="HTML")
  return
 if text.lower() in["лог","история"]:
  if not game_history:return await m.reply("📋 История пуста")
  await m.reply(f"<code>{chr(10).join(game_history[-10:])}</code>",parse_mode="HTML")
  return
 if text.lower() in["задания","quests"]:
  await m.reply(f"<code>🎯 ЕЖЕДНЕВНЫЕ ЗАДАНИЯ{get_quests_status(uid)}\n\n⏰ Обновляются каждые 24 часа\n✨ Награда выдается автоматически!</code>",parse_mode="HTML")
  return
 if text.lower() in["помощь","команды","help"]:
  await m.reply("<code>🎰 GOLDEN GRAM ROULETTE\n\n🎲 СТАВКИ:\n├ 100 чёрное\n├ 250 красное\n├ 500 чётное\n├ 1000 14\n├ 2000 0\n└ 5000 1-12\n\n🎲 КОСТИ: кости 500 на 7\n🎰 СЛОТ: слот 100\n🎡 КОЛЕСО: колесо 100\n💣 МИНЫ: мины 100\n🃏 БЛЭКДЖЕК: bj 100\n\n📌 КОМАНДЫ:\n├ б - баланс\n├ профиль - статистика\n├ топ - топ игроков\n├ ачивки - достижения\n├ ранг - твой ранг\n├ бонус - бонус\n├ задания - задания\n├ го - запуск\n├ отмена - отмена ставок\n├ дать 500 (ответом)\n└ дать всё (ответом)</code>",parse_mode="HTML")
  return
 if text.lower()=="топ":
  if not user_balances:return await m.reply("📊 Пусто")
  items=sorted(user_balances.items(),key=lambda x:x[1],reverse=True)[:10]
  txt="🏆 ТОП-10 ИГРОКОВ\n\n"
  for i,(u,b)in enumerate(items,1):
   try:n=(await bot.get_chat(u)).full_name
   except:n=str(u)
   txt+=f"{i}. {n}\n└ {format_amount(b)} GRAM\n\n"
  await m.reply(f"<code>{txt}</code>",parse_mode="HTML")
  return
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
  try:gif=await m.answer_animation(ROULETTE_GIF,caption="🎰 Крутим...")
  except:gif=None
  await asyncio.sleep(10)
  if gif:
   try:await bot.delete_message(m.chat.id,gif.message_id)
   except:pass
  try:
   num,emoji,color=spin_roulette()
   game_history.append(f"{emoji} {num}")
   if len(game_history)>10:game_history.pop(0)
   all_bets,wins=[],[]
   for b in pending_bets:
    uname,amt,raw=b["user_name"],b["amount"],b["raw_bet"]
    all_bets.append(f"{uname} {format_amount(amt)} GRAM на {raw}")
    if check_win(raw,num,color):
     mult=get_multiplier(raw)
     win_amt=amt*mult
     old_bal_bet=user_balances.get(b["user_id"],0)
     user_balances[b["user_id"]]=user_balances.get(b["user_id"],0)+win_amt
     new_rank=check_rank_up(b["user_id"], old_bal_bet, user_balances[b["user_id"]])
     if new_rank:await send_rank_up_notify(b["user_id"],new_rank,m)
     if b["user_id"] not in user_stats:user_stats[b["user_id"]]={"played":0,"won":0,"total_bet":0,"total_win":0}
     user_stats[b["user_id"]]["played"]=user_stats[b["user_id"]].get("played",0)+1
     user_stats[b["user_id"]]["won"]=user_stats[b["user_id"]].get("won",0)+1
     user_stats[b["user_id"]]["total_bet"]=user_stats[b["user_id"]].get("total_bet",0)+amt
     user_stats[b["user_id"]]["total_win"]=user_stats[b["user_id"]].get("total_win",0)+win_amt
     user_levels[b["user_id"]]=user_levels.get(b["user_id"],0)+1
     daily_quests["win_3_streak"]["current_streak"][b["user_id"]]=daily_quests["win_3_streak"]["current_streak"].get(b["user_id"],0)+1
     rew=update_quest_progress(b["user_id"],"win_3_streak",daily_quests["win_3_streak"]["current_streak"][b["user_id"]])
     if rew:await send_quest_notify(b["user_id"],"win_3_streak",rew,m)
     wins.append(f"{uname} выиграл {format_amount(win_amt)} на {raw}")
    else:
     if b["user_id"] not in user_stats:user_stats[b["user_id"]]={"played":0,"won":0,"total_bet":0,"total_win":0}
     user_stats[b["user_id"]]["played"]=user_stats[b["user_id"]].get("played",0)+1
     user_stats[b["user_id"]]["total_bet"]=user_stats[b["user_id"]].get("total_bet",0)+amt
     user_levels[b["user_id"]]=user_levels.get(b["user_id"],0)+1
     daily_quests["win_3_streak"]["current_streak"][b["user_id"]]=0
    rew2=update_quest_progress(b["user_id"],"play_3_games")
    if rew2:await send_quest_notify(b["user_id"],"play_3_games",rew2,m)
    new_achs=check_achievements(b["user_id"])
    for ach in new_achs:await send_achievement_notify(b["user_id"],ach,m)
   save_data()
   await m.answer(f"<code>🎲 РУЛЕТКА: {num} {emoji}</code>",parse_mode="HTML")
   for i in range(0,len(all_bets),50):await m.answer("<code>"+"\n".join(all_bets[i:i+50])+"</code>",parse_mode="HTML")
   for i in range(0,len(wins),50):await m.answer("<code>"+"\n".join(wins[i:i+50])+"</code>",parse_mode="HTML")
  except Exception as e:
   logging.error(f"Ошибка: {e}")
   await m.answer("❌ Ошибка, ставки возвращены")
   for b in pending_bets:user_balances[b["user_id"]]=user_balances.get(b["user_id"],0)+b["amount"]
  finally:
   pending_bets.clear()
   game_in_progress=False
   last_game_time=int(time.time())
  return
 if len(parts)>=2:
  if game_in_progress:
   await m.reply("⏳ Идёт игра, подождите...")
   return
  try:amt=int(parts[0])
  except:return
  if amt<100:return await m.reply("❌ Минимальная ставка 100 GRAM")
  bets=" ".join(parts[1:]).split()
  if len(bets)>MAX_BETS_PER_MESSAGE:return await m.reply(f"❌ Максимум {MAX_BETS_PER_MESSAGE} ставок")
  total=amt*len(bets)
  bal=user_balances.get(uid,0)
  if total>bal:return await m.reply(f"❌ Нужно {format_amount(total)} GRAM")
  rew=update_quest_progress(uid,"make_bet")
  if rew:await send_quest_notify(uid,"make_bet",rew,m)
  user_balances[uid]=bal-total
  save_data()
  acc=[]
  for b in bets:
   if not b:continue
   pending_bets.append({"user_id":uid,"user_name":name,"amount":amt,"raw_bet":b})
   acc.append(f"Ставка принята: {name} {format_amount(amt)} GRAM на {b}")
  for i in range(0,len(acc),20):await m.reply("<code>"+"\n".join(acc[i:i+20])+"</code>",parse_mode="HTML")

# ========== КОЛБЭКИ ==========
@dp.callback_query_handler(lambda c:c.data.startswith("bj_"))
async def bj_cb(call):
 await call.answer()
 uid=call.from_user.id
 if uid not in blackjack_games:return await call.message.edit_text("❌ Игра не найдена")
 g=blackjack_games[uid]
 if not g["active"]:return
 action=call.data[3:]
 if action=="hit":
  g["player_hand"].append(g["deck"].pop())
  pv=hand_value(g["player_hand"])
  if pv>21:
   g["active"]=False
   del blackjack_games[uid]
   if uid not in user_stats:user_stats[uid]={"played":0,"won":0,"total_bet":0,"total_win":0}
   user_stats[uid]["played"]=user_stats[uid].get("played",0)+1
   user_stats[uid]["total_bet"]=user_stats[uid].get("total_bet",0)+g["bet"]
   user_levels[uid]=user_levels.get(uid,0)+1
   rew=update_quest_progress(uid,"play_3_games")
   if rew:await send_quest_notify(uid,"play_3_games",rew,call.message)
   daily_quests["win_3_streak"]["current_streak"][uid]=0
   new_achs=check_achievements(uid)
   for ach in new_achs:await send_achievement_notify(uid,ach,call.message)
   save_data()
   await call.message.edit_text(f"<code>🃏 ПЕРЕБОР! ({pv})\n❌ -{format_amount(g['bet'])} GRAM</code>",parse_mode="HTML")
   return
  kb=InlineKeyboardMarkup(row_width=2)
  kb.add(InlineKeyboardButton("🃏 Взять",callback_data="bj_hit"),InlineKeyboardButton("✋ Хватит",callback_data="bj_stand"))
  await call.message.edit_text(f"<code>🃏 БЛЭКДЖЕК\n💰 Ставка: {format_amount(g['bet'])} GRAM\n\nВаши карты: {format_cards(g['player_hand'])} ({pv})</code>",parse_mode="HTML",reply_markup=kb)
 elif action=="stand":
  g["active"]=False
  while hand_value(g["dealer_hand"])<17:g["dealer_hand"].append(g["deck"].pop())
  pv=hand_value(g["player_hand"])
  dv=hand_value(g["dealer_hand"])
  win=0
  if dv>21 or pv>dv:win=g["bet"]*2
  elif pv==dv:win=g["bet"]
  if win>0:user_balances[uid]=user_balances.get(uid,0)+win
  if uid not in user_stats:user_stats[uid]={"played":0,"won":0,"total_bet":0,"total_win":0,"bj_wins":0}
  user_stats[uid]["played"]=user_stats[uid].get("played",0)+1
  if win>g["bet"]:
   user_stats[uid]["won"]=user_stats[uid].get("won",0)+1
   user_stats[uid]["bj_wins"]=user_stats[uid].get("bj_wins",0)+1
  user_stats[uid]["total_bet"]=user_stats[uid].get("total_bet",0)+g["bet"]
  user_stats[uid]["total_win"]=user_stats[uid].get("total_win",0)+win
  user_levels[uid]=user_levels.get(uid,0)+1
  rew=update_quest_progress(uid,"play_3_games")
  if rew:await send_quest_notify(uid,"play_3_games",rew,call.message)
  if win>g["bet"]:
   daily_quests["win_3_streak"]["current_streak"][uid]=daily_quests["win_3_streak"]["current_streak"].get(uid,0)+1
   rew2=update_quest_progress(uid,"win_3_streak",daily_quests["win_3_streak"]["current_streak"][uid])
   if rew2:await send_quest_notify(uid,"win_3_streak",rew2,call.message)
  else:daily_quests["win_3_streak"]["current_streak"][uid]=0
  new_achs=check_achievements(uid)
  for ach in new_achs:await send_achievement_notify(uid,ach,call.message)
  del blackjack_games[uid]
  save_data()
  await call.message.edit_text(f"<code>🃏 ИГРА ОКОНЧЕНА\n\nВаши карты: {format_cards(g['player_hand'])} ({pv})\nКарты дилера: {format_cards(g['dealer_hand'])} ({dv})\n💰 +{format_amount(win) if win>0 else '0'} GRAM</code>",parse_mode="HTML")
 elif action=="surrender":
  g["active"]=False
  refund=g["bet"]//2
  user_balances[uid]=user_balances.get(uid,0)+refund
  if uid not in user_stats:user_stats[uid]={"played":0,"won":0,"total_bet":0,"total_win":0}
  user_stats[uid]["played"]=user_stats[uid].get("played",0)+1
  user_stats[uid]["total_bet"]=user_stats[uid].get("total_bet",0)+g["bet"]
  user_levels[uid]=user_levels.get(uid,0)+1
  rew=update_quest_progress(uid,"play_3_games")
  if rew:await send_quest_notify(uid,"play_3_games",rew,call.message)
  del blackjack_games[uid]
  save_data()
  await call.message.edit_text(f"<code>🏳️ ВЫ СДАЛИСЬ\n💰 Возвращено {format_amount(refund)} GRAM</code>",parse_mode="HTML")

@dp.callback_query_handler(lambda c:c.data.startswith("m_"))
async def mine_cb(call):
 await call.answer()
 uid=call.from_user.id
 if uid not in mines_games:return
 g=mines_games[uid]
 if not g["active"]:return
 _,r,c=call.data.split("_")
 r,c=int(r),int(c)
 if (r,c) in g["revealed"]:return
 g["revealed"].append((r,c))
 if g["field"][r][c]=="💣":
  g["active"]=False
  del mines_games[uid]
  rew=update_quest_progress(uid,"play_3_games")
  if rew:await send_quest_notify(uid,"play_3_games",rew,call.message)
  daily_quests["win_3_streak"]["current_streak"][uid]=0
  new_achs=check_achievements(uid)
  for ach in new_achs:await send_achievement_notify(uid,ach,call.message)
  save_data()
  await call.message.edit_text(f"💥 МИНА!\n❌ -{format_amount(g['bet'])} GRAM\n\n{format_mines_field(g['field'],g['revealed'])}")
  return
 g["multiplier"]+=0.14
 pot=int(g["bet"]*g["multiplier"])
 await call.message.edit_text(f"💎 {call.from_user.full_name}\n📌 Ставка: {format_amount(g['bet'])} GRAM\n💲 Выигрыш: x{g['multiplier']:.2f} | {format_amount(pot)} GRAM\n\n{format_mines_field(g['field'],g['revealed'])}",reply_markup=get_mines_keyboard(g['field'],g['revealed']))

@dp.callback_query_handler(lambda c:c.data=="cash")
async def mine_cash_cb(call):
 await call.answer()
 uid=call.from_user.id
 if uid not in mines_games:return
 g=mines_games[uid]
 if not g["active"]:return
 g["active"]=False
 win=int(g["bet"]*g["multiplier"])
 old_bal=user_balances.get(uid,0)
 user_balances[uid]=user_balances.get(uid,0)+win
 new_rank=check_rank_up(uid, old_bal, user_balances[uid])
 if new_rank:await send_rank_up_notify(uid,new_rank,call.message)
 if uid not in user_stats:user_stats[uid]={"played":0,"won":0,"total_bet":0,"total_win":0,"mines_wins":0}
 user_stats[uid]["played"]=user_stats[uid].get("played",0)+1
 user_stats[uid]["won"]=user_stats[uid].get("won",0)+1
 user_stats[uid]["mines_wins"]=user_stats[uid].get("mines_wins",0)+1
 user_stats[uid]["total_bet"]=user_stats[uid].get("total_bet",0)+g["bet"]
 user_stats[uid]["total_win"]=user_stats[uid].get("total_win",0)+win
 user_levels[uid]=user_levels.get(uid,0)+1
 rew=update_quest_progress(uid,"play_3_games")
 if rew:await send_quest_notify(uid,"play_3_games",rew,call.message)
 daily_quests["win_3_streak"]["current_streak"][uid]=daily_quests["win_3_streak"]["current_streak"].get(uid,0)+1
 rew2=update_quest_progress(uid,"win_3_streak",daily_quests["win_3_streak"]["current_streak"][uid])
 if rew2:await send_quest_notify(uid,"win_3_streak",rew2,call.message)
 new_achs=check_achievements(uid)
 for ach in new_achs:await send_achievement_notify(uid,ach,call.message)
 del mines_games[uid]
 save_data()
 await call.message.edit_text(f"💰 {call.from_user.full_name} забрал выигрыш!\n✅ +{format_amount(win)} GRAM\n💲 Итоговый множитель: x{g['multiplier']:.2f}\n\n{format_mines_field(g['field'],g['revealed'])}")

if __name__=="__main__":
 load_data()
 init_quests()
 executor.start_polling(dp,skip_updates=True)
