from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from states import BrowseForm
from database import (
    get_next_project_for_role,
    mark_project_seen,
    add_response,
    add_bookmark,
    get_user,
    set_response_status,
    get_project,
)
from handlers.profile import ROLES, build_profile_card
from handlers.project import format_project_card
from handlers.common import ensure_profile, profile_is_complete, fill_profile_kb
from validators import (
    ERR_ROLE_BUTTONS,
    ERR_STACK,
    ERR_FORMAT,
    ERR_MANUAL_FIELD,
    ERR_CARD_BUTTONS,
    ERR_NO_PROFILE,
    valid_stack,
    valid_format,
    valid_manual_field,
)

router = Router()


def entry_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅Выбрать роль", callback_data="browse:pick_role")],
            [InlineKeyboardButton(text="Как это работает❓", callback_data="browse:how")],
        ]
    )


def role_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"🟢{role}", callback_data=f"brole:{role}")]
            for role in ROLES
        ]
    )


def experience_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Junior", callback_data="bexp:Junior")],
            [InlineKeyboardButton(text="Middle", callback_data="bexp:Middle")],
            [InlineKeyboardButton(text="Senior", callback_data="bexp:Senior")],
        ]
    )


def filter_confirm_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅Да, искать под мою роль", callback_data="bfilter:yes")],
            [InlineKeyboardButton(text="🔄 Искать под другую роль", callback_data="bfilter:change")],
        ]
    )


def card_kb(project_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢Откликнуться", callback_data=f"bresp:{project_id}"),
                InlineKeyboardButton(text="🟢В закладки", callback_data=f"bbookmark:{project_id}"),
            ],
            [InlineKeyboardButton(text="🟢Следующий проект", callback_data="bnext")],
            [InlineKeyboardButton(text="🟢Назад в меню", callback_data="bmenu")],
        ]
    )


async def send_next_card(message: Message, user_id: int, role: str, state: FSMContext):
    project = await get_next_project_for_role(user_id, role)
    if not project:
        await state.update_data(current_project_id=None)
        await message.answer("Пока новых проектов под эту роль нет. Загляни позже 🙂")
        return

    await mark_project_seen(user_id, project["project_id"])
    await state.update_data(current_project_id=project["project_id"])
    await message.answer(
        format_project_card(project),
        reply_markup=card_kb(project["project_id"]),
    )


@router.message(F.text == "🔍 Ищу команду")
async def browse_entry(message: Message):
    if not await ensure_profile(message):
        return
    await message.answer("Выбери, что дальше:", reply_markup=entry_kb())


@router.callback_query(F.data == "browse:how")
async def browse_how(callback: CallbackQuery):
    await callback.message.answer(
        "Выбери подходящую для себя роль, после чего бот подберёт нужные для тебя проекты."
    )
    await callback.answer()


@router.callback_query(F.data == "browse:pick_role")
async def browse_pick_role(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BrowseForm.choosing_role)
    await callback.message.answer("Выбери роль:", reply_markup=role_kb())
    await callback.answer()


@router.callback_query(BrowseForm.choosing_role, F.data.startswith("brole:"))
async def browse_role_chosen(callback: CallbackQuery, state: FSMContext):
    role = callback.data.split(":", 1)[1]
    await state.update_data(role=role)
    await state.set_state(BrowseForm.choosing_experience)
    await callback.message.answer("Какой у тебя опыт?", reply_markup=experience_kb())
    await callback.answer()


@router.message(BrowseForm.choosing_role)
async def browse_role_text(message: Message):
    await message.answer(ERR_ROLE_BUTTONS, reply_markup=role_kb())


@router.callback_query(BrowseForm.choosing_experience, F.data.startswith("bexp:"))
async def browse_experience_chosen(callback: CallbackQuery, state: FSMContext):
    experience = callback.data.split(":", 1)[1]
    await state.update_data(experience=experience)
    await state.set_state(BrowseForm.entering_stack)
    await callback.message.answer("Стек технологий / инструменты? (например: Figma, React, Node.js)")
    await callback.answer()


@router.message(BrowseForm.choosing_experience)
async def browse_experience_text(message: Message):
    await message.answer(
        "❗️Пожалуйста, выбери уровень опыта с помощью кнопок ниже",
        reply_markup=experience_kb(),
    )


@router.message(BrowseForm.entering_stack)
async def browse_stack_entered(message: Message, state: FSMContext):
    if not valid_stack(message.text):
        await message.answer(ERR_STACK)
        return
    await state.update_data(stack=message.text.strip())
    await state.set_state(BrowseForm.entering_employment)
    await message.answer("Занятость? (например: Хакатон / Пет-проект / Part-time / Full-time стартап)")


@router.message(BrowseForm.entering_employment)
async def browse_employment_entered(message: Message, state: FSMContext):
    if not valid_format(message.text):
        await message.answer(ERR_FORMAT)
        return
    await state.update_data(employment=message.text.strip())
    await state.set_state(BrowseForm.entering_time)
    await message.answer("Сколько времени ты готов уделять проекту? (например: 5-10 часов в неделю)")


@router.message(BrowseForm.entering_time)
async def browse_time_entered(message: Message, state: FSMContext):
    if not valid_manual_field(message.text):
        await message.answer(ERR_MANUAL_FIELD)
        return
    await state.update_data(time=message.text.strip())
    data = await state.get_data()
    await state.set_state(BrowseForm.confirming_filter)
    await message.answer(
        "Фильтр поиска команд:\n"
        f"Твоя текущая роль: {data['role']}\n"
        "Искать проекты, где открыта эта вакансия?",
        reply_markup=filter_confirm_kb(),
    )


@router.callback_query(BrowseForm.confirming_filter, F.data == "bfilter:change")
async def browse_filter_change(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BrowseForm.choosing_role)
    await callback.message.answer("Выбери роль:", reply_markup=role_k
