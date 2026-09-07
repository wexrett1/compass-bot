from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from states import ProjectForm
from database import create_project, get_user_projects, get_bookmarks
from handlers.profile import ROLES
from handlers.common import ensure_profile
from validators import (
    ERR_PROJECT_TITLE,
    ERR_PROJECT_DESCRIPTION,
    ERR_PROJECT_DESCRIPTION_LONG,
    ERR_PROJECT_ROLES_BUTTONS,
    ERR_MANUAL_FIELD,
    valid_project_title,
    project_description_issue,
    valid_manual_field,
)

router = Router()

ASK_TITLE = "Название проекта:"
ASK_DESCRIPTION = "Краткое описание проекта (1-3 предложения):"
ASK_ROLES = "Кто требуется в проект? Выбери одну или несколько ролей:"
ASK_TOPIC = "Тематика проекта (например: EdTech, AI, Финтех, Геймдев):"
ASK_STAGE = "На какой стадии проект? (например: Идея / Прототип / Готовимся к хакатону):"
ASK_FORMAT = "Формат участия? (например: Пет-проект 5-10 ч/нед / Спринт на выходные):"


def project_entry_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать проект", callback_data="proj:new")],
            [InlineKeyboardButton(text="📋 Мои опубликованные проекты", callback_data="proj:mine")],
        ]
    )


def roles_kb(selected: list[str]):
    buttons = []
    for role in ROLES:
        prefix = "✅ " if role in selected else "🟢"
        buttons.append([InlineKeyboardButton(text=f"{prefix}{role}", callback_data=f"prole:{role}")])
    buttons.append([InlineKeyboardButton(text="Готово, сохранить роли ➡️", callback_data="prole_done")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def format_project_card(project) -> str:
    return (
        f"Название: {project['title']}\n"
        f"Тематика: {project['topic']}\n"
        f"Стадия: {project['stage']}\n"
        f"Формат: {project['format']}\n"
        f"Кого ищут: {project['roles']}\n"
        f"О проекте: {project['description']}"
    )


@router.message(F.text == "📢 Ищу человека в проект")
async def project_menu(message: Message):
    if not await ensure_profile(message):
        return
    projects = await get_user_projects(message.from_user.id)
    if projects:
        text = "Твои проекты уже опубликованы. Можно создать ещё один или посмотреть текущие."
    else:
        text = "У тебя пока нет активных проектов. Создай карточку, чтобы участники могли откликаться."
    await message.answer(text, reply_markup=project_entry_kb())
