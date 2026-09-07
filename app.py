import asyncio
import logging
import os
from threading import Thread

from flask import Flask, jsonify

# Импортируем ваш главный файл бота
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from dotenv import load_dotenv

from database import init_db
from handlers import common, profile, project, browse, review, fallback
from middlewares import ContentGuardMiddleware

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask приложение
app = Flask(__name__)

@app.route('/')
def index():
    return "Бот работает!"

@app.route('/health')
def health():
    return jsonify({"status": "ok"}), 200

# Настройка бота
token = os.getenv("BOT_TOKEN")
if not token:
    raise RuntimeError("BOT_TOKEN не найден. Проверьте переменные окружения!")

bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# Подключаем роутеры и мидлвари
dp.message.outer_middleware(ContentGuardMiddleware())

dp.include_router(common.router)
dp.include_router(profile.router)
dp.include_router(project.router)
dp.include_router(browse.router)
dp.include_router(review.router)
dp.include_router(fallback.router)

# Запуск бота
async def bot_main():
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
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])


def run_flask():
    """Запускаем Flask в отдельном потоке"""
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    # Запускаем Flask в фоновом потоке (чтобы asyncio остался в главном)
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Запускаем бота В ГЛАВНОМ ПОТОКЕ (asyncio.run разрешен только здесь)
    try:
        asyncio.run(bot_main())
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
