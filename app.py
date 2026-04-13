import os
import asyncio
import logging
import sys
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message

API_TOKEN = os.environ.get("BOT_TOKEN", "8723084939:AAEO8Jd5oLYsAN-JMht4CBh2MUy_XWxH94M")

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

user_balances = {}
game_history = []

# ========== АДМИН-ПАНЕЛЬ ==========
ADMIN_ID = 6003768110

@dp.message(Command("add_grams"))
async def add_grams(message: Message):
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
    await message.reply(f"✅ Баланс пополнен на {amount} GRAM.\n💰 Текущий баланс: {user_balances[ADMIN_ID]} GRAM")
# ================================

def spin_roulette():
    number = random.randint(0, 36)
    if number == 0:
        color = "🟢"
    elif number in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]:
        color = "🔴"
    else:
        color = "⚫"
    return number, color

@dp.message(Command("start"))
async def start_handler(message: Message):
    user_id = message.from_user.id
    if user_id not in user_balances:
        user_balances[user_id] = 10000
    await message.answer(
        f"🎰 GOLDEN GRAM ROULETTE\n\n"
        f"/bet 100 red — красное\n"
        f"/bet 100 black — черное\n"
        f"/log — история\n\n"
        f"Баланс: {user_balances[user_id]} GRAM"
    )

@dp.message(Command("log"))
async def log_handler(message: Message):
    if not game_history:
        await message.answer("📋 История пуста.")
        return
    log_text = "📋 Последние выпадения:\n"
    for entry in game_history[-10:]:
        log_text += f"{entry}\n"
    await message.answer(log_text)

@dp.message(Command("bet"))
async def bet_handler(message: Message):
    user_id = message.from_user.id
    parts = message.text.split()
    
    if len(parts) != 3:
        await message.reply("❌ Формат: /bet 100 red")
        return
    
    try:
        amount = int(parts[1])
    except:
        await message.reply("❌ Сумма числом!")
        return
        
    bet_type = parts[2].lower()
    balance = user_balances.get(user_id, 0)
    
    if amount <= 0:
        await message.reply("❌ Ставка > 0")
        return
    if amount > balance:
        await message.reply(f"❌ Мало GRAM. Баланс: {balance}")
        return

    win_num, win_color = spin_roulette()
    
    win = False
    if (bet_type == "red" and win_color == "🔴") or (bet_type == "black" and win_color == "⚫"):
        win = True
        
    if win:
        winnings = amount * 2
        user_balances[user_id] += amount
        result_text = f"✅ ВЫИГРЫШ! +{winnings} GRAM\n"
    else:
        user_balances[user_id] -= amount
        result_text = f"❌ ПРОИГРЫШ. -{amount} GRAM\n"

    game_history.append(f"{win_color} {win_num}")
    if len(game_history) > 10:
        game_history.pop(0)

    await message.answer(
        f"🎲 СТАВКА: {amount} GRAM на {bet_type}\n"
        f"🎯 ВЫПАЛО: {win_num} {win_color}\n"
        f"{result_text}"
        f"💰 БАЛАНС: {user_balances[user_id]} GRAM"
    )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
