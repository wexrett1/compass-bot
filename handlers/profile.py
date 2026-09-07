from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)

from states import ProfileForm
from database import upsert_user, get_user, get_reviews_for_user
from validators import (
    ERR_FULL_NAME,
    ERR_UNIVERSITY,
    ERR_ROLE_BUTTONS,
    ERR_STACK,
    ERR_FORMAT,
    ERR_SOCIALS,
    ERR_PHONE,
    ERR_STATUS_BUTTONS,
    valid_full_name,
    valid_university,
    valid_stack,
    valid_format,
    valid_socials,
    valid_phone,
    valid_manual_field,
)

router = Router()

ROLES = [
    "Тимлид",
    "Бэкендер",
    "Фронтендер",
    "Мобайл-дев",
    "Дизайнер",
    "Тестировщик",
    "Другое",
]

ASK_FULL_NAME = "Как тебя зовут? Укажи Фамилию и Имя:"
ASK_UNIVERSITY = "В каком вузе учишься и на каком курсе? (например: УрФУ,  курсе)"
ASK_ROLE = "Выбери свою роль:"
ASK_ROLE_CUSTOM = "Напиши свою роль:"
ASK_STACK = "Какой стек/навыки используешь? (например: Python, aiogram, Docker)"
ASK_FORMAT = "В каком формате готов участвовать? (например: Хакатон, Пет-проект, Full-time стартап)"
ASK_STATUS = "Какой у тебя статус поиска?"
ASK_SOCIALS = "Скинь ссылки на свои соц сети (Telegram, VK, GitHub):"
ASK_PHONE = "Укажи номер телефона для связи (например: +7 999 111 22 33):"
ASK_PROJECTS = "Расскажи о своих проектах (или напиши «нет»):"


def role_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"🟢{role}", callback_data=f"role:{role}")]
            for role in ROLES
        ]
    )


def status_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🟢В активном поиске команды", callback_data="status:active")],
            [InlineKeyboardButton(text="🔴Приостановить поиск", callback_data="status:paused")],
        ]
    )


def _field(user, name, default="не указано"):
    try:
        value = user[name]
    except (KeyError, IndexError):
        return default
    return value if value else default


def format_profile_card(user, review_count: int = 0) -> str:
    status_text = "🟢 В активном поиске" if user["is_active"] else "🔴 Приостановлен"
    projects_raw = _field(user, "projects", "")
    projects = projects_raw if projects_raw and projects_raw.lower() != "нет" else "не указано"
    reviews_line = f"{review_count} отзыв(ов) — посмотреть: /reviews" if review_count else "пока нет"
    return (
        "👤 Твоя карточка соискателя:\n"
        f"• ФИО: {_field(user, 'full_name')}\n"
        f"• Вуз: {_field(user, 'university')}\n"
        f"• Роль: {_field(user, 'role')}\n"
        f"• Стек: {_field(user, 'stack')}\n"
        f"• Формат: {_field(user, 'format')}\n"
        f"• Статус: {status_text}\n"
        f"• Мои соц сети: {_field(user, 'socials')}\n"
        f"• Номер телефона: {_field(user, 'phone')}\n"
        f"• Мои проекты: {projects}\n"
        f"• Отзывы: {reviews_line}\n"
        "• Закладки: посмотреть можно командой /bookmarks"
    )


async def build_profile_card(user) -> str:
    reviews = await get_reviews_for_user(user["user_id"])
    return format_profile_card(user, review_count=len(reviews))


async def start_profile_form(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(ProfileForm.entering_full_name)
    await message.answer(ASK_FULL_NAME)


@router.message(Command("profile"))
async def cmd_profile(message: Message, state: FSMContext):
    await start_profile_form(message, state)


@router.message(F.text == "🔴 Редактировать профиль")
async def edit_profile_button(message: Message, state: FSMContext):
    await start_profile_form(message, state)


@router.callback_query(F.data == "profile:start")
async def start_profile_from_button(callback: CallbackQuery, state: FSMContext):
    await start_profile_form(callback.message, state)
    await callback.answer()


@router.message(F.text == "👤 Мой профиль")
async def show_profile_button(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("У тебя ещё нет анкеты. Создай её: /profile")
        return
    await message.answer(await build_profile_card(user))
