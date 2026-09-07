from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery


class ContentGuardMiddleware(BaseMiddleware):
    """
    Отсекает голосовые, стикеры, файлы и контакты.
    НО: всегда пропускает CallbackQuery (кнопки) и текстовые сообщения.
    """

    async def __call__(self, handler, event, data):
        # 1. ВСЕГДА пропускаем callback_query (нажатия на кнопки)
        if isinstance(event, CallbackQuery):
            return await handler(event, data)

        # 2. Если это сообщение (Message):
        if isinstance(event, Message):
            # Отсекаем нежелательный контент
            if event.content_type in [
                "voice",
                "video_note",
                "sticker",
                "photo",
                "video",
                "audio",
                "document",
                "contact",
                "location",
                "venue",
            ]:
                # Например, бот пишет: "Этот формат не поддерживается"
                await event.answer("❗️ Этот формат сообщений не поддерживается. Напишите текстом.")
                return

        # 3. Без 조건 — пропускаем остальное
        return await handler(event, data)