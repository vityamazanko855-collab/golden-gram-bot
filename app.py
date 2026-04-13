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
        color = "🟢 ЗЕЛЁНОЕ"
    elif number in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]:
        color = "🔴 КРАСНОЕ"
    else:
        color = "⚫ ЧЁРНОЕ"
    
    if number == 0:
        parity = "ZERO"
    elif number % 2 == 0:
        parity = "ЧЁТНОЕ"
    else:
        parity = "НЕЧЁТНОЕ"
    
    return number, color, parity

# ========== ОБРАБОТЧИК РУССКИХ КОМАНД БЕЗ СЛЕША ==========
@dp.message()
async def handle_russian_commands(message: Message):
    user_id = message.from_user.id
    text = message.text.lower().strip()
    parts = text.split()
    
    # Проверка на команду "баланс"
    if text == "баланс":
        balance = user_balances.get(user_id, 0)
        await message.reply(f"💰 Ваш баланс: {balance} GRAM")
        return
    
    # Проверка на команду "лог" или "история"
    if text in ["лог", "история"]:
        if not game_history:
            await message.reply("📋 История пуста.")
        else:
            log_text = "📋 Последние выпадения:\n"
            for entry in game_history[-10:]:
                log_text += f"{entry}\n"
            await message.reply(log_text)
        return
    
    # Проверка на команду "помощь" или "команды"
    if text in ["помощь", "команды", "help", "старт"]:
        balance = user_balances.get(user_id, 0)
        await message.reply(
            f"🎰 GOLDEN GRAM ROULETTE\n\n"
            f"Ставки (пиши без слеша):\n"
            f"• 100 красное\n"
            f"• 100 чёрное\n"
            f"• 100 чётное\n"
            f"• 100 нечётное\n\n"
            f"Команды:\n"
            f"• баланс — узнать баланс\n"
            f"• лог — история выпадений\n"
            f"• помощь — это сообщение\n\n"
            f"💰 Твой баланс: {balance} GRAM"
        )
        return
    
    # Проверка на ставку (формат: "100 красное", "50 чёрное", "200 чётное", "150 нечётное")
    if len(parts) == 2:
        try:
            amount = int(parts[0])
        except:
            return  # Не ставка, игнорируем
        
        bet_type = parts[1]
        balance = user_balances.get(user_id, 0)
        
        # Проверяем, что ставка допустима
        allowed_bets = ["красное", "чёрное", "черное", "чётное", "четное", "нечётное", "нечетное"]
        if bet_type not in allowed_bets:
            return  # Неизвестный тип ставки, игнорируем
        
        # Проверка суммы
        if amount <= 0:
            await message.reply("❌ Ставка должна быть больше нуля.")
            return
        if amount > balance:
            await message.reply(f"❌ Недостаточно GRAM. Ваш баланс: {balance}")
            return
        
        # Крутим рулетку
        win_num, win_color, win_parity = spin_roulette()
        
        # Определяем выигрыш
        win = False
        
        # Для красного/чёрного
        if bet_type in ["красное"] and "КРАСНОЕ" in win_color:
            win = True
        elif bet_type in ["чёрное", "черное"] and "ЧЁРНОЕ" in win_color:
            win = True
        # Для чётного/нечётного
        elif bet_type in ["чётное", "четное"] and win_parity == "ЧЁТНОЕ":
            win = True
        elif bet_type in ["нечётное", "нечетное"] and win_parity == "НЕЧЁТНОЕ":
            win = True
        
        # Расчёт выигрыша
        if win:
            winnings = amount * 2
            user_balances[user_id] += amount
            result_text = f"✅ ВЫИГРЫШ! +{winnings} GRAM"
        else:
            user_balances[user_id] -= amount
            result_text = f"❌ ПРОИГРЫШ. -{amount} GRAM"
        
        # Сохраняем в историю
        game_history.append(f"{win_color.split()[0]} {win_num} ({win_parity})")
        if len(game_history) > 10:
            game_history.pop(0)
        
        # Ответ
        await message.reply(
            f"🎲 СТАВКА: {amount} GRAM на {bet_type}\n"
            f"🎯 ВЫПАЛО: {win_num} {win_color} ({win_parity})\n"
            f"{result_text}\n"
            f"💰 БАЛАНС: {user_balances[user_id]} GRAM"
        )

# ========== СТАРЫЕ КОМАНДЫ ЧЕРЕЗ / (НА ВСЯКИЙ СЛУЧАЙ) ==========
@dp.message(Command("start"))
async def start_handler(message: Message):
    user_id = message.from_user.id
    if user_id not in user_balances:
        user_balances[user_id] = 10000
    await message.reply(
        f"🎰 GOLDEN GRAM ROULETTE\n\n"
        f"Ставки (пиши без слеша):\n"
        f"• 100 красное\n"
        f"• 100 чёрное\n"
        f"• 100 чётное\n"
        f"• 100 нечётное\n\n"
        f"Команды:\n"
        f"• баланс\n"
        f"• лог\n"
        f"• помощь\n\n"
        f"💰 Твой баланс: {user_balances[user_id]} GRAM"
    )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
