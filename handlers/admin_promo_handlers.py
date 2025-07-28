# handlers/promo_handlers.py

from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from datetime import datetime
from states import CreatePromo
from database import db
from keyboards import admin_main_menu, admin_promos_menu, admin_cancel_action, main_menu
from callbacks import PromoCallback

router = Router()



# === 2. ОБРАБОТКА ВХОДА В РАЗДЕЛ "ПРОМОКОДЫ" ===
@router.message(F.text == "🎫 Промокоды")
async def admin_promos_handler(message: Message):
    await message.answer("🎫 Управление промокодами:", reply_markup=admin_promos_menu())

@router.callback_query(F.data == "manage_promo_codes")
async def back_to_promos_menu(callback: CallbackQuery):
    await callback.message.edit_text("🎫 Управление промокодами:", reply_markup=admin_promos_menu())
    await callback.answer()

# === 3. ПРОЦЕСС СОЗДАНИЯ ПРОМОКОДА (FSM) ===

# Шаг 1: Нажатие кнопки "Создать промокод"
@router.callback_query(F.data == "create_promo")
async def start_creating_promo(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CreatePromo.waiting_promo_type)
    builder = InlineKeyboardBuilder()
    builder.button(text="Баланс", callback_data=PromoCallback(action="select_type", value="balance").pack())
    builder.button(text="Скидка", callback_data=PromoCallback(action="select_type", value="discount").pack())
    builder.button(text="❌ Отмена", callback_data=PromoCallback(action="cancel_creation").pack())
    builder.adjust(2, 1)
    
    await callback.message.edit_text("Выберите тип промокода:", reply_markup=builder.as_markup())
    await callback.answer()

# Хендлер для отмены создания
@router.callback_query(PromoCallback.filter(F.action == "cancel_creation"), CreatePromo.waiting_promo_type)
async def cancel_promo_creation(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Создание промокода отменено.", reply_markup=admin_promos_menu())
    await callback.answer()

# Шаг 2: Выбор типа промокода
@router.callback_query(PromoCallback.filter(F.action == "select_type"))
async def process_promo_type(callback: CallbackQuery, callback_data: PromoCallback, state: FSMContext):
    await state.update_data(promo_type=callback_data.value)
    await state.set_state(CreatePromo.waiting_promo_code)
    await callback.message.edit_text("🔑 Введите код промокода:", reply_markup=admin_cancel_action())
    await callback.answer()

# Шаги 3-7 (логика FSM) остаются почти без изменений, только убираем лишнее
@router.message(CreatePromo.waiting_promo_code)
async def process_promo_code(message: Message, state: FSMContext):
    if db.get_promocode(message.text):
        await message.answer(f"❌ Промокод '{message.text}' уже существует! Введите другой:")
        return
    await state.update_data(code=message.text)
    await state.set_state(CreatePromo.waiting_promo_value)
    await message.answer("💰 Введите значение (сумма для 'Баланс', процент для 'Скидка'):")

@router.message(CreatePromo.waiting_promo_value)
async def process_promo_value(message: Message, state: FSMContext):
    try:
        value = float(message.text)
        await state.update_data(value=value)
        await state.set_state(CreatePromo.waiting_promo_expiration)
        await message.answer("📅 Введите дату истечения в формате ГГММДД (например, 251231) или отправьте '0' для бессрочного:")
    except ValueError:
        await message.answer("❌ Введите корректное число.")

@router.message(CreatePromo.waiting_promo_expiration)
async def process_promo_expiration(message: Message, state: FSMContext):
    expiration = None
    if message.text != "0":
        try:
            expiration_date = datetime.strptime(message.text, "%y%m%d")
            expiration = expiration_date.strftime("%Y-%m-%d")
        except ValueError:
            await message.answer("❌ Некорректный формат даты. Введите ГГММДД или '0'.")
            return
    
    await state.update_data(expiration=expiration)
    await state.set_state(CreatePromo.waiting_promo_max_uses)
    await message.answer("🔢 Введите максимальное количество использований (отправьте '0' для безлимитного):")

@router.message(CreatePromo.waiting_promo_max_uses)
async def process_promo_max_uses(message: Message, state: FSMContext):
    try:
        max_uses = int(message.text)
        data = await state.get_data()
        
        db.add_promocode(
            code=data['code'],
            promo_type=data['promo_type'],
            value=data['value'],
            expiration_date=data.get('expiration'),
            max_uses=max_uses
        )
        await message.answer(f"✅ Промокод '{data['code']}' успешно создан!", reply_markup=admin_promos_menu())
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите целое число.")


# === 4. ПРОСМОТР И УДАЛЕНИЕ ПРОМОКОДОВ ===

@router.callback_query(F.data == "list_promos")
async def list_promocodes(callback: CallbackQuery):
    promocodes = db.get_promocodes_list()
    if not promocodes:
        await callback.message.edit_text("❌ Нет активных промокодов.", reply_markup=admin_promos_menu())
        return
        
    builder = InlineKeyboardBuilder()
    for promo in promocodes:
        # Используем имена полей вместо индексов
        builder.button(
            text=f"{promo['code']} ({promo['type']})", 
            callback_data=PromoCallback(action="view", id=promo['id']).pack()
        )
    builder.button(text="⬅️ Назад", callback_data="manage_promo_codes")
    builder.adjust(2, 1)
    
    await callback.message.edit_text("📋 Список промокодов:", reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(PromoCallback.filter(F.action == "view"))
async def show_promo_detail(callback: CallbackQuery, callback_data: PromoCallback):
    promo = db.get_promocode_by_id(callback_data.id)
    if not promo:
        await callback.answer("❌ Промокод не найден!", show_alert=True)
        return
        
    text = (
        f"🔑 Промокод: <b>{promo['code']}</b>\n"
        f"📝 Тип: {promo['type']}\n"
        f"💰 Значение: {promo['value']}\n"
        f"📅 Срок действия: {promo['expiration_date'] or 'Бессрочный'}\n"
        f"🔢 Использовано: {promo['uses']}/{promo['max_uses'] if promo['max_uses'] > 0 else '∞'}"
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="🗑️ Удалить", callback_data=PromoCallback(action="delete", id=promo['id']).pack())
    builder.button(text="⬅️ Назад к списку", callback_data="list_promos")
    builder.adjust(1)
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(PromoCallback.filter(F.action == "delete"))
async def delete_promocode_prompt(callback: CallbackQuery, callback_data: PromoCallback):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data=PromoCallback(action="confirm_delete", id=callback_data.id).pack())
    builder.button(text="❌ Нет, отмена", callback_data=PromoCallback(action="view", id=callback_data.id).pack())
    await callback.message.edit_text("⚠️ Вы уверены, что хотите удалить этот промокод?", reply_markup=builder.as_markup())

@router.callback_query(PromoCallback.filter(F.action == "confirm_delete"))
async def confirm_delete_promocode(callback: CallbackQuery, callback_data: PromoCallback):
    db.delete_promocode(callback_data.id)
    await callback.message.edit_text("✅ Промокод успешно удален!", reply_markup=admin_promos_menu())

# === 5. ОБРАБОТЧИК ДЛЯ КНОПКИ ГЛАВНОГО МЕНЮ ===
@router.message(F.text == "Главное меню")
async def back_to_main_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Возвращаемся в главное меню.", reply_markup=main_menu())