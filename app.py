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
game_history = []  # Храним ТОЛЬКО эмодзи и число: ["🔴 14", "⚫ 22", "🟢 0"]

ADMIN_ID = 6003768110

# ========== АДМИН-ПАНЕЛЬ ==========
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

# ========== РУЛЕТКА: ЧИСЛО И ЦВЕТ ==========
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
    
    # Чётность
    if number == 0:
        parity = "ZERO"
    elif number % 2 == 0:
        parity = "ЧЁТНОЕ"
    else:
        parity = "НЕЧЁТНОЕ"
    
    # Дюжина и колонка
    if 1 <= number <= 12:
        dozen = 1
    elif 13 <= number <= 24:
        dozen = 2
    elif 25 <= number <= 36:
        dozen = 3
    else:
        dozen = 0
    
    if number == 0:
        column = 0
    elif number % 3 == 1:
        column = 1
    elif number % 3 == 2:
        column = 2
    else:
        column = 3
    
    return number, color_emoji, color_name, parity, dozen, column

# ========== ОФОРМЛЕНИЕ БАЛАНСА (КАК НА СКРИНЕ) ==========
def format_balance(user_name: str, balance: int) -> str:
    return f"{user_name}\nБаланс: {balance} GRAM"

# ========== ОФОРМЛЕНИЕ ЛОГА (КАК НА СКРИНЕ) ==========
def format_log():
    if not game_history:
        return "📋 История пуста."
    
    # Берём последние 10 чисел
    last_10 = game_history[-10:]
    
    # Разбиваем на две строки по 5 чисел (как на скрине)
    row1 = " ".join(last_10[:5])
    row2 = " ".join(last_10[5:]) if len(last_10) > 5 else ""
    
    if row2:
        return f"{row1}\n{row2}"
    else:
        return row1

# ========== ПРОВЕРКА ВЫИГРЫША ДЛЯ ВСЕХ ТИПОВ СТАВОК ==========
def check_win(bet_type: str, number: int, color_name: str, parity: str, dozen: int, column: int) -> bool:
    bet = bet_type.lower()
    
    # Простые ставки
    if bet in ["красное"] and color_name == "КРАСНОЕ": return True
    if bet in ["чёрное", "черное"] and color_name == "ЧЁРНОЕ": return True
    if bet in ["чётное", "четное"] and parity == "ЧЁТНОЕ": return True
    if bet in ["нечётное", "нечетное"] and parity == "НЕЧЁТНОЕ": return True
    if bet == "0" and number == 0: return True
    
    # Дюжины
    if bet == "1-12" and dozen == 1: return True
    if bet == "13-24" and dozen == 2: return True
    if bet == "25-36" and dozen == 3: return True
    
    # Колонки (по скрину: 1-я, 2-я, 3-я)
    if bet in ["1-я", "1я", "первая"] and column == 1: return True
    if bet in ["2-я", "2я", "вторая"] and column == 2: return True
    if bet in ["3-я", "3я", "третья"] and column == 3: return True
    
    # Конкретные числа (от 0 до 36)
    if bet.isdigit():
        if int(bet) == number: return True
    
    # Диапазоны вида "1-8", "11-18", "21-28" и т.д.
    if "-" in bet:
        parts = bet.split("-")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            start, end = int(parts[0]), int(parts[1])
            if start <= number <= end:
                return True
    
    return False

# ========== ГЛАВНЫЙ ОБРАБОТЧИК СООБЩЕНИЙ ==========
@dp.message()
async def handle_message(message: Message):
    user_id = message.from_user.id
    user_name = message.from_user.full_name  # Берём имя из Telegram
    text = message.text.strip()
    parts = text.split()
    
    # ========== КОМАНДА "БАЛАНС" ==========
    if text.lower() == "баланс":
        balance = user_balances.get(user_id, 0)
        await message.reply(format_balance(user_name, balance))
        return
    
    # ========== КОМАНДА "ЛОГ" ==========
    if text.lower() in ["лог", "история"]:
        await message.reply(format_log())
        return
    
    # ========== КОМАНДА "ПОМОЩЬ" ==========
    if text.lower() in ["помощь", "команды", "help", "старт", "/start"]:
        balance = user_balances.get(user_id, 0)
        await message.reply(
            f"{user_name}\n\n"
            f"🎰 GOLDEN GRAM ROULETTE\n\n"
            f"📌 ПРОСТЫЕ СТАВКИ:\n"
            f"• красное\n• чёрное\n• чётное\n• нечётное\n"
            f"• 0 (зеро)\n\n"
            f"📌 ДЮЖИНЫ:\n"
            f"• 1-12\n• 13-24\n• 25-36\n\n"
            f"📌 КОЛОНКИ:\n"
            f"• 1-я • 2-я • 3-я\n\n"
            f"📌 КОНКРЕТНЫЕ ЧИСЛА:\n"
            f"• 1, 14, 36 и т.д.\n\n"
            f"📌 ДИАПАЗОНЫ (Split):\n"
            f"• 1-8, 11-18, 21-28 и др.\n\n"
            f"📌 КОМАНДЫ:\n"
            f"• баланс — проверить счёт\n"
            f"• лог — история чисел\n"
            f"• помощь — это меню\n\n"
            f"💰 Ваш баланс: {balance} GRAM"
        )
        return
    
    # ========== ОБРАБОТКА СТАВКИ (формат: "1000 красное", "500 14", "200 1-12") ==========
    if len(parts) >= 2:
        try:
            amount = int(parts[0])
        except:
            return  # Не ставка, игнорируем
        
        # Всё после суммы — это тип ставки
        bet_type = " ".join(parts[1:]).lower()
        
        balance = user_balances.get(user_id, 0)
        
        if amount <= 0:
            await message.reply("❌ Ставка должна быть больше нуля.")
            return
        if amount > balance:
            await message.reply(format_balance(user_name, balance) + f"\n\n❌ Недостаточно GRAM.")
            return
        
        # Списываем ставку
        user_balances[user_id] -= amount
        
        # Крутим рулетку
        win_num, win_emoji, win_color, win_parity, win_dozen, win_column = spin_roulette()
        
        # Проверяем выигрыш
        win = check_win(bet_type, win_num, win_color, win_parity, win_dozen, win_column)
        
        # Определяем коэффициент
        if bet_type.isdigit() or bet_type == "0":
            multiplier = 36  # Ставка на конкретное число
        elif "-" in bet_type:
            # Split'ы и диапазоны — коэффициент зависит от количества чисел
            parts_range = bet_type.split("-")
            if len(parts_range) == 2 and parts_range[0].isdigit() and parts_range[1].isdigit():
                start, end = int(parts_range[0]), int(parts_range[1])
                count = end - start + 1
                if count == 2:
                    multiplier = 18
                elif count == 3:
                    multiplier = 12
                elif count == 4:
                    multiplier = 9
                elif count == 6:
                    multiplier = 6
                elif count == 12:
                    multiplier = 3
                else:
                    multiplier = 36 // count if count > 0 else 2
            else:
                multiplier = 2
        elif bet_type in ["1-12", "13-24", "25-36", "1-я", "2-я", "3-я", "1я", "2я", "3я", "первая", "вторая", "третья"]:
            multiplier = 3
        else:
            multiplier = 2  # Красное/чёрное/чёт/нечет
        
        # Расчёт выигрыша
        if win:
            winnings = amount * multiplier
            user_balances[user_id] += winnings
            result_line = f"✅ ВЫИГРЫШ! +{winnings} GRAM"
        else:
            winnings = 0
            result_line = f"❌ ПРОИГРЫШ"
        
        # Добавляем в историю (только эмодзи и число)
        game_history.append(f"{win_emoji} {win_num}")
        if len(game_history) > 10:
            game_history.pop(0)
        
        # Формируем ответ
        response = f"{user_name}\n\n"
        response += f"🎲 СТАВКА: {amount} GRAM на {bet_type}\n"
        response += f"🎯 ВЫПАЛО: {win_emoji} {win_num}\n"
        response += f"{result_line}\n\n"
        response += format_balance(user_name, user_balances[user_id])
        
        await message.reply(response)

# ========== ЗАПУСК ==========
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
