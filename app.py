import asyncio
import logging
import os
from threading import Thread

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from flask import Flask

# --- НАСТРОЙКА ЛОГИРОВАНИЯ ---
logging.basicConfig(level=logging.INFO)

# --- НАСТРОЙКА FLASK (ДЛЯ RENDER) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

# --- НАСТРОЙКА БОТА ---
API_TOKEN = os.getenv("BOT_TOKEN") # Токен берется из переменных окружения на Render

# Если токена нет, код выдаст ошибку, но не упадет
if not API_TOKEN:
    raise ValueError("No BOT_TOKEN found in environment variables")

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# --- ОБРАБОТЧИКИ ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("Привет! Я работаю на Render!")

# --- ЗАПУСК БОТА В ФОНЕ ---
async def bot_main():
    # Важно: бесконечный цикл поллинга
    await dp.start_polling(bot)

def run_bot():
    # Запускаем асинхронную функцию бота в отдельном потоке
    asyncio.run(bot_main())

if __name__ == "__main__":
    # Запускаем бота в отдельном потоке, чтобы не блокировать Flask
    bot_thread = Thread(target=run_bot)
    bot_thread.daemon = True  # Поток закроется, если закроется основной процесс
    bot_thread.start()
    
    # Запускаем Flask-сервер на порту, который даст Render (обычно 10000)
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)