import asyncio
import logging
import os
import threading
from flask import Flask, jsonify

# Импортируем всё из bot.py
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from dotenv import load_dotenv

# Импортируем ваши модули. Убедитесь, что они в репозитории!
from database import init_db
from handlers import common, profile, project, browse, review, fallback
from middlewares import ContentGuardMiddleware

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

web_app = Flask(__name__)

@web_app.route('/')
def index():
    return "🤖 Бот для поиска команды работает!"

@web_app.route('/health')
def health():
    return jsonify({"status": "ok", "message": "Бот жив!"}), 200

async def bot_main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN не найден. Проверь переменные окружения!")

    await init_db()

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    # Отсекает голосовые, стикеры, файлы и контакты до всех хендлеров
    dp.message.outer_middleware(ContentGuardMiddleware())

    dp.include_router(common.router)
    dp.include_router(profile.router)
    dp.include_router(project.router)
    dp.include_router(browse.router)
    dp.include_router(review.router)
    # fallback обязательно последним: ловит всё, что не подошло ни одному хендлеру
    dp.include_router(fallback.router)

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
    """Запуск бота в отдельном потоке"""
    try:
        print("🤖 Запуск бота...")
        asyncio.run(bot_main())
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")

if __name__ == '__main__':
    print("🚀 Запуск бота и веб-сервера...")
    
    # Запускаем бота в фоновом потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Запускаем веб-сервер Flask
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 Веб-сервер запущен на порту {port}")
    web_app.run(host='0.0.0.0', port=port)