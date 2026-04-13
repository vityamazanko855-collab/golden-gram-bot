import asyncio
import logging
import sys
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message

# --- ВСТАВЬ СВОЙ ТОКЕН НИЖЕ В КАВЫЧКАХ ---
API_TOKEN = "8723084939:AAEO8Jd5oLYsAN-JMht4CBh2MUy_XWxH94M"
# ---------------------------------------

# Настройка логов (чтобы видеть ошибки, если бот упадет)
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Тут будем хранить баланс игроков в памяти телефона (при перезапуске сбросится)
user_balances = {}
# Тут будем хранить последние 10 чисел
game_history = []

def spin_roulette():
    """Крутим рулетку: число от 0 до 36 и цвет"""
    number = random.randint(0, 36)
    
    if number == 0:
        color = "🟢" # Зеленый
    elif number in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]:
        color = "🔴" # Красный
    else:
        color = "⚫" # Черный

    return number, color

@dp.message(Command("start"))
async def start_handler(message: Message):
    user_id = message.from_user.id
    if user_id not in user_balances:
        user_balances[user_id] = 10000
    await message.answer(
        "🎰 *GOLDEN GRAM ROULETTE*\n\n"
        "Команды:\n"
        "`/bet 100 red` — ставка 100 на красное\n"
        "`/bet 100 black` — ставка на черное\n"
        "`/log` — история выпадений\n\n"
        "Твой баланс: `{0}` GRAM".format(user_balances[user_id]),
        parse_mode="Markdown"
    )

@dp.message(Command("log"))
async def log_handler(message: Message):
    if not game_history:
        await message.answer("📋 История пока пуста.")
        return
        
    log_text = "📋 Последние выпадения:\n"
    for entry in game_history[-10:]: # Показываем до 10 последних
        log_text += f"{entry}\n"
    await message.answer(log_text)

@dp.message(Command("bet"))
async def bet_handler(message: Message):
    user_id = message.from_user.id
    parts = message.text.split()
    
    # Проверка: правильно ли введена команда? (/bet 100 red)
    if len(parts) != 3:
        await message.reply("❌ Неверный формат. Пример: `/bet 50 red`")
        return
    
    try:
        amount = int(parts[1])
    except ValueError:
        await message.reply("❌ Сумма должна быть числом!")
        return
        
    bet_type = parts[2].lower()
    
    # Проверяем баланс
    balance = user_balances.get(user_id, 0)
    if amount <= 0:
        await message.reply("❌ Ставка должна быть больше нуля.")
        return
    if amount > balance:
        await message.reply(f"❌ Недостаточно GRAM. Твой баланс: `{balance}`")
        return

    # Крутим рулетку
    win_num, win_color = spin_roulette()
    
    # Определяем победу (коэффициент х2 на цвета)
    win = False
    if (bet_type == "red" and win_color == "🔴") or (bet_type == "black" and win_color == "⚫"):
        win = True
        
    # Рассчитываем итог
    if win:
        winnings = amount * 2
        user_balances[user_id] += amount # Возвращаем ставку + выигрыш
        result_text = f"✅ ВЫИГРЫШ! +{winnings} GRAM\n"
    else:
        user_balances[user_id] -= amount
        result_text = f"❌ ПРОИГРЫШ. -{amount} GRAM\n"

    # Сохраняем историю
    game_history.append(f"{win_color} {win_num}")
    if len(game_history) > 10:
        game_history.pop(0)

    # Отправляем красивое сообщение как на скриншоте
    await message.answer(
        f"🎲 *СТАВКА:* {amount} GRAM на *{bet_type}*\n"
        f"🎯 *ВЫПАЛО:* {win_num} {win_color}\n"
        f"{result_text}"
        f"💰 *БАЛАНС:* {user_balances[user_id]} GRAM",
        parse_mode="Markdown"
    )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())