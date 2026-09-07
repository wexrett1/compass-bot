import asyncio
import logging
import os
from threading import Thread

from flask import Flask

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

# Импортируйте ваши модули. Убедитесь, что они лежат в репозитории!
from database import init_db
from handlers import common, profile, project, browse, review, fallback
from middlewares import ContentGuardMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================
# НАСТРОЙКА FLASK (ДЛЯ RENDER)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

# ==========================================
# НАСТРОЙКА БОТА (ВСЕ ИЗ ВАШЕГО bot.py)
# ==========================================

# Токен берем из переменных окружения (на Render вы добавите BOT_TOKEN)
API_TOKEN = os.getenv("BOT_TOKEN")
if not API_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден. Проверь переменные окружения!")

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# Подключаем мидлварю
dp.message.outer_middleware(ContentGuardMiddleware())

# Подключаем роутеры
dp.include_router(common.router)
dp.include_router(profile.router)
dp.include_router(project.router)
dp.include_router(browse.router)
dp.include_router(review.router)
dp.include_router(fallback.router)

# ==========================================
# ЗАПУСК БОТА В ФОНЕ
# ==========================================

async def bot_main():
    # Запускаем базу данных
    await init_db()

    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота / главное меню"),
        BotCommand(command="profile", description="Создать или изменить анкету"),
        BotCommand(command="bookmarks", description="Посмотреть закладки"),
        BotCommand(command="reviews", description="Посмотреть отзывы о себе"),
        BotCommand(command="pause", description="Скрыть свою анкету"),
        BotCommand(command="resume", description="Снова показывать анкету"),
        BotCommand(command="cancel", description="Прервать текущий шаг"),
        BotCommand(command="help", description="Список команд"),
    ])

    logger.info("Бот запускается...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

def run_bot():
    # Запускаем асинхронную функцию в отдельном потоке (так как Flask блокирует основной)
    asyncio.run(bot_main())

if __name__ == "__main__":
    # Запускаем бота в фоне
    bot_thread = Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Запускаем Flask, чтобы Render видел порт
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)