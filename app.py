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

ADMIN_ID=6003768110
GAME_COOLDOWN=15
DAILY_BONUS_BASE=500
DAILY_BONUS_STREAK_MULTIPLIER=200
MAX_BETS_PER_MESSAGE=500
ROULETTE_GIF="https://i.gifer.com/3P1d3.gif"
DATA_FILE="bot_data.json"

daily_quests={}
last_quest_reset=int(time.time())

def format_amount(a): return f"{a:,}".replace(","," ")
def get_level(e):
 if e<10:return 1
 elif e<30:return 2
 elif e<60:return 3
 elif e<100:return 4
 else:return 5

def load_data():
 global user_balances,user_stats,user_levels,daily_streak,game_history,daily_quests,last_quest_reset
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
 except:pass

def save_data():
 with open(DATA_FILE,"w")as f:
  json.dump({"user_balances":user_balances,"user_stats":user_stats,"user_levels":user_levels,"daily_streak":daily_streak,"game_history":game_history[-50:],"daily_quests":daily_quests,"last_quest_reset":last_quest_reset},f,ensure_ascii=False,indent=2)

def init_quests():
 global daily_quests
 if not daily_quests:
  daily_quests={"play_3_games":{"name":"🎲 Сыграть 3 игры","target":3,"reward":30000,"progress":{},"completed":{}},"win_3_streak":{"name":"🏆 Выиграть 3 раза подряд","target":3,"reward":25000,"progress":{},"completed":{},"current_streak":{}},"make_bet":{"name":"💰 Сделать любую ставку","target":1,"reward":10000,"progress":{},"completed":{}}}

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
  InlineKeyboardButton("💣 Мины",callback_data="menu_mines"),
  InlineKeyboardButton("🃏 Блэкджек",callback_data="menu_blackjack"),
  InlineKeyboardButton("🎁 Задания",callback_data="menu_quests"),
  InlineKeyboardButton("🏆 Топ",callback_data="menu_top"),
  InlineKeyboardButton("❓ Помощь",callback_data="menu_help")
 )
 return kb

SUITS=["♠","♥","♦","♣"]
RANKS=["2","3","4","5","6","7","8","9","10","J","Q","K","A"]

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
 deck=[(r,s) for r in RANKS for s in SUITS]
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
  "💣 МИНЫ: мины 100\n🃏 БЛЭКДЖЕК: bj 100\n\n"
  "📌 КОМАНДЫ:\n├ б - баланс\n├ профиль - статистика\n├ топ - топ игроков\n├ бонус - бонус\n├ задания - задания\n├ го - запуск\n├ отмена - отмена ставок\n├ дать 500 (ответом)\n└ дать всё (ответом)</code>",
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
  wr=(s["won"]/s["played"]*100)if s["played"]>0 else 0
  prof=s["total_win"]-s["total_bet"]
  await call.message.edit_text(f"👤 <b>{name}</b>\n├ 🆔 {uid}\n├ 📊 Уровень: {lvl}\n└ 💰 {format_amount(bal)} GRAM\n\n📊 <b>Статистика</b>\n├ 🎲 Игр: {s['played']}\n├ 🏆 Побед: {s['won']}\n├ 📈 Винрейт: {wr:.1f}%\n└ 📊 Профит: {format_amount(prof)} GRAM",parse_mode="HTML",reply_markup=get_main_keyboard())
 elif act=="quests":
  await call.message.edit_text(f"🎯 <b>ЕЖЕДНЕВНЫЕ ЗАДАНИЯ</b>{get_quests_status(uid)}\n\n⏰ Обновляются каждые 24 часа\n✨ Награда выдается автоматически!",parse_mode="HTML",reply_markup=get_main_keyboard())
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
   "mines":"💣 <b>ИГРА МИНЫ</b>\n\n├ Команда: мины 100\n├ Поле 5x5, 3 мины\n├ Каждая клетка +0.14x\n└ Максимум x4.0",
   "blackjack":"🃏 <b>БЛЭКДЖЕК</b>\n\n├ Команда: bj 100\n├ Мин. ставка: 100\n├ Блэкджек: x2.5\n├ Победа: x2\n└ Сдача: 50%",
   "help":"🎰 <b>GOLDEN GRAM ROULETTE</b>\n\n🎲 СТАВКИ:\n├ 100 чёрное\n├ 250 красное\n├ 500 чётное\n├ 1000 14\n├ 2000 0\n└ 5000 1-12\n\n💣 МИНЫ: мины 100\n🃏 БЛЭКДЖЕК: bj 100\n\n📌 КОМАНДЫ:\n├ б - баланс\n├ профиль - статистика\n├ топ - топ игроков\n├ бонус - бонус\n├ задания - задания\n├ го - запуск\n├ отмена - отмена ставок\n├ дать 500 (ответом)\n└ дать всё (ответом)"
  }
  await call.message.edit_text(texts.get(act,"❓ Помощь"),parse_mode="HTML",reply_markup=get_main_keyboard())

@dp.message_handler()
async def handle(m):
 global pending_bets,game_in_progress,last_game_time,game_history
 
 # Принудительный сброс зависшей игры (если прошло больше 60 секунд)
 if game_in_progress and time.time() - last_game_time > 60:
  force_reset_game()
  await m.reply("⚠️ Предыдущая игра принудительно завершена (таймаут)")
 
 uid=m.from_user.id
 name=m.from_user.full_name
 text=m.text.strip()
 if text.lower().startswith('/'):return
 parts=text.split()
 
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
   user_stats[uid]=user_stats.get(uid,{"played":0,"won":0,"total_bet":0,"total_win":0})
   user_stats[uid]["played"]+=1
   user_stats[uid]["won"]+=1
   user_stats[uid]["total_bet"]+=bet
   user_stats[uid]["total_win"]+=win
   user_levels[uid]=user_levels.get(uid,0)+2
   rew2=update_quest_progress(uid,"play_3_games")
   if rew2:await send_quest_notify(uid,"play_3_games",rew2,m)
   daily_quests["win_3_streak"]["current_streak"][uid]=daily_quests["win_3_streak"]["current_streak"].get(uid,0)+1
   rew3=update_quest_progress(uid,"win_3_streak",daily_quests["win_3_streak"]["current_streak"][uid])
   if rew3:await send_quest_notify(uid,"win_3_streak",rew3,m)
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
  wr=(s["won"]/s["played"]*100)if s["played"]>0 else 0
  prof=s["total_win"]-s["total_bet"]
  await m.reply(f"<code>👤 {name}\n🆔 {uid}\n📊 Уровень: {lvl}\n💰 {format_amount(bal)} GRAM\n\n🎲 Игр: {s['played']}\n🏆 Побед: {s['won']}\n📈 Винрейт: {wr:.1f}%\n📊 Профит: {format_amount(prof)} GRAM</code>",parse_mode="HTML")
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
  await m.reply("<code>🎰 GOLDEN GRAM ROULETTE\n\n🎲 СТАВКИ:\n├ 100 чёрное\n├ 250 красное\n├ 500 чётное\n├ 1000 14\n├ 2000 0\n└ 5000 1-12\n\n💣 МИНЫ: мины 100\n🃏 БЛЭКДЖЕК: bj 100\n\n📌 КОМАНДЫ:\n├ б - баланс\n├ профиль - статистика\n├ топ - топ игроков\n├ бонус - бонус\n├ задания - задания\n├ го - запуск\n├ отмена - отмена ставок\n├ дать 500 (ответом)\n└ дать всё (ответом)</code>",parse_mode="HTML")
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
     user_balances[b["user_id"]]=user_balances.get(b["user_id"],0)+win_amt
     if b["user_id"] not in user_stats:user_stats[b["user_id"]]={"played":0,"won":0,"total_bet":0,"total_win":0}
     user_stats[b["user_id"]]["played"]+=1
     user_stats[b["user_id"]]["won"]+=1
     user_stats[b["user_id"]]["total_bet"]+=amt
     user_stats[b["user_id"]]["total_win"]+=win_amt
     user_levels[b["user_id"]]=user_levels.get(b["user_id"],0)+1
     daily_quests["win_3_streak"]["current_streak"][b["user_id"]]=daily_quests["win_3_streak"]["current_streak"].get(b["user_id"],0)+1
     rew=update_quest_progress(b["user_id"],"win_3_streak",daily_quests["win_3_streak"]["current_streak"][b["user_id"]])
     if rew:await send_quest_notify(b["user_id"],"win_3_streak",rew,m)
     wins.append(f"{uname} выиграл {format_amount(win_amt)} на {raw}")
    else:
     if b["user_id"] not in user_stats:user_stats[b["user_id"]]={"played":0,"won":0,"total_bet":0,"total_win":0}
     user_stats[b["user_id"]]["played"]+=1
     user_stats[b["user_id"]]["total_bet"]+=amt
     user_levels[b["user_id"]]=user_levels.get(b["user_id"],0)+1
     daily_quests["win_3_streak"]["current_streak"][b["user_id"]]=0
    rew2=update_quest_progress(b["user_id"],"play_3_games")
    if rew2:await send_quest_notify(b["user_id"],"play_3_games",rew2,m)
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
   user_stats[uid]=user_stats.get(uid,{"played":0,"won":0,"total_bet":0,"total_win":0})
   user_stats[uid]["played"]+=1
   user_stats[uid]["total_bet"]+=g["bet"]
   user_levels[uid]=user_levels.get(uid,0)+1
   rew=update_quest_progress(uid,"play_3_games")
   if rew:await send_quest_notify(uid,"play_3_games",rew,call.message)
   daily_quests["win_3_streak"]["current_streak"][uid]=0
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
  user_stats[uid]=user_stats.get(uid,{"played":0,"won":0,"total_bet":0,"total_win":0})
  user_stats[uid]["played"]+=1
  if win>g["bet"]:user_stats[uid]["won"]+=1
  user_stats[uid]["total_bet"]+=g["bet"]
  user_stats[uid]["total_win"]+=win
  user_levels[uid]=user_levels.get(uid,0)+1
  rew=update_quest_progress(uid,"play_3_games")
  if rew:await send_quest_notify(uid,"play_3_games",rew,call.message)
  if win>g["bet"]:
   daily_quests["win_3_streak"]["current_streak"][uid]=daily_quests["win_3_streak"]["current_streak"].get(uid,0)+1
   rew2=update_quest_progress(uid,"win_3_streak",daily_quests["win_3_streak"]["current_streak"][uid])
   if rew2:await send_quest_notify(uid,"win_3_streak",rew2,call.message)
  else:daily_quests["win_3_streak"]["current_streak"][uid]=0
  del blackjack_games[uid]
  save_data()
  await call.message.edit_text(f"<code>🃏 ИГРА ОКОНЧЕНА\n\nВаши карты: {format_cards(g['player_hand'])} ({pv})\nКарты дилера: {format_cards(g['dealer_hand'])} ({dv})\n💰 +{format_amount(win) if win>0 else '0'} GRAM</code>",parse_mode="HTML")
 elif action=="surrender":
  g["active"]=False
  refund=g["bet"]//2
  user_balances[uid]=user_balances.get(uid,0)+refund
  user_stats[uid]=user_stats.get(uid,{"played":0,"won":0,"total_bet":0,"total_win":0})
  user_stats[uid]["played"]+=1
  user_stats[uid]["total_bet"]+=g["bet"]
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
 user_balances[uid]=user_balances.get(uid,0)+win
 user_stats[uid]=user_stats.get(uid,{"played":0,"won":0,"total_bet":0,"total_win":0})
 user_stats[uid]["played"]+=1
 user_stats[uid]["won"]+=1
 user_stats[uid]["total_bet"]+=g["bet"]
 user_stats[uid]["total_win"]+=win
 user_levels[uid]=user_levels.get(uid,0)+1
 rew=update_quest_progress(uid,"play_3_games")
 if rew:await send_quest_notify(uid,"play_3_games",rew,call.message)
 daily_quests["win_3_streak"]["current_streak"][uid]=daily_quests["win_3_streak"]["current_streak"].get(uid,0)+1
 rew2=update_quest_progress(uid,"win_3_streak",daily_quests["win_3_streak"]["current_streak"][uid])
 if rew2:await send_quest_notify(uid,"win_3_streak",rew2,call.message)
 del mines_games[uid]
 save_data()
 await call.message.edit_text(f"💰 {call.from_user.full_name} забрал выигрыш!\n✅ +{format_amount(win)} GRAM\n💲 Итоговый множитель: x{g['multiplier']:.2f}\n\n{format_mines_field(g['field'],g['revealed'])}")

if __name__=="__main__":
 load_data()
 init_quests()
 executor.start_polling(dp,skip_updates=True)
