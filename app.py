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

# Данные
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
    if
