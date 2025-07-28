from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, StateFilter
from datetime import datetime
from config import ADMIN_IDS
from states import AddProduct, CreatePromo, AddCategory, ManageCategory, AddSubcategory, EditSubcategory #EditProduct
from database import db
from keyboards import admin_main_menu, admin_promos_menu, admin_promos_list, admin_products_menu, admin_categories_menu, admin_category, admin_podcategory, admin_products_edit, admin_cancel_action, main_menu, admin_skip
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Union

router = Router()

async def check_admin(user_id: int, message: Message) -> bool:
    if user_id not in ADMIN_IDS:
        await message.answer("Доступ запрещён!")
        return False
    return True

@router.message(Command("admin"))
async def admin_command(message: Message):
    if not await check_admin(message.from_user.id, message): 
        return
    await message.answer("Админ-панель:", reply_markup=admin_main_menu())

@router.message(F.text == "🛒 Товары")
@router.callback_query(F.data == "🛒 Товары")
async def admin_products_handler(event: Union[Message, CallbackQuery]):
    user_id = event.from_user.id
    message = event.message if isinstance(event, CallbackQuery) else event
    if not await check_admin(user_id, message):
        return
    if isinstance(event, CallbackQuery):
        await event.answer()
    text = "🛒 Управление товарами:"
    markup = admin_products_menu()
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=markup)
    else:
        await message.answer(text, reply_markup=markup)

@router.message(F.text == "🎫 Промокоды")
async def admin_promos_handler(message: Message):
    if not await check_admin(message.from_user.id, message): 
        return
    await message.answer("🎫 Управление промокодами:", reply_markup=admin_promos_menu())

@router.message(F.text == "Главное меню")
async def back_to_main_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Возвращаемся в главное меню", reply_markup=main_menu())

# Обработчики для промокодов
@router.callback_query(F.data == "create_promo")
async def start_creating_promo(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback.from_user.id, callback.message): 
        return
    
    await state.set_state(CreatePromo.waiting_promo_type)
    builder = InlineKeyboardBuilder()
    builder.button(text="balance", callback_data="promo_type_balance")
    builder.button(text="discount", callback_data="promo_type_discount")
    builder.button(text="❌ Отмена", callback_data="admin_cancel")
    builder.adjust(2)
    
    await callback.message.edit_text("Выберите тип промокода:", reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("promo_type_"))
async def process_promo_type(callback: CallbackQuery, state: FSMContext):
    promo_type = callback.data.split("_")[2]
    await state.update_data(promo_type=promo_type)
    await state.set_state(CreatePromo.waiting_promo_code)
    await callback.message.edit_text("🔑 Введите код промокода:", reply_markup=admin_cancel_action())
    await callback.answer()

@router.message(CreatePromo.waiting_promo_code)
async def process_promo_code(message: Message, state: FSMContext):
    if db.get_promocode(message.text):
        await message.answer(f"❌ Промокод '{message.text}' уже существует! Введите другой:")
        return
    await state.update_data(code=message.text)
    await state.set_state(CreatePromo.waiting_promo_value)
    await message.answer("💰 Введите значение (сумма для balance, процент для discount):")

@router.message(CreatePromo.waiting_promo_value)
async def process_promo_value(message: Message, state: FSMContext):
    try:
        value = float(message.text)
        await state.update_data(value=value)
        await state.set_state(CreatePromo.waiting_promo_expiration)
        await message.answer("📅 Введите дату истечения (ГГММДД) или '0' для бессрочного:")
    except ValueError:
        await message.answer("❌ Введите число")

@router.message(CreatePromo.waiting_promo_expiration)
async def process_promo_expiration(message: Message, state: FSMContext):
    expiration = None
    if message.text != "0" and message.text.isdigit() and len(message.text) == 6:
        yy, mm, dd = message.text[:2], message.text[2:4], message.text[4:6]
        try:
            datetime.strptime(f"20{yy}-{mm}-{dd}", "%Y-%m-%d")
            expiration = f"20{yy}-{mm}-{dd}"
        except ValueError:
            await message.answer("❌ Некорректная дата")
            return
    
    await state.update_data(expiration=expiration)
    await state.set_state(CreatePromo.waiting_promo_max_uses)
    await message.answer("🔢 Введите макс. использование (0 - без ограничений):")

@router.message(CreatePromo.waiting_promo_max_uses)
async def process_promo_max_uses(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        max_uses = int(message.text)
        db.add_promocode(
            code=data['code'],
            promo_type=data['promo_type'],
            value=data['value'],
            expiration_date=data['expiration'],
            max_uses=max_uses if max_uses > 0 else 1000000
        )
        await message.answer(f"✅ Промокод {data['code']} создан!", reply_markup=admin_main_menu())
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите целое число")

@router.callback_query(F.data == "list_promos")
async def list_promocodes(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id, callback.message): 
        return
        
    promocodes = db.get_promocodes_list()
    if not promocodes:
        await callback.message.edit_text("❌ Нет активных промокодов", reply_markup=admin_promos_menu())
        return
        
    builder = InlineKeyboardBuilder()
    for promo in promocodes:
        builder.button(text=f"{promo[1]} ({promo[2]})", callback_data=f"promo_detail_{promo[0]}")
    builder.button(text="🔙 Назад", callback_data="back_to_promos_menu")
    builder.adjust(2)
    
    await callback.message.edit_text("📋 Список промокодов:", reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("promo_detail_"))
async def show_promo_detail(callback: CallbackQuery):
    promo_id = int(callback.data.split("_")[2])
    promo = db.get_promocode_by_id(promo_id)
    if not promo:
        await callback.answer("❌ Промокод не найден!", show_alert=True)
        return
        
    text = (
        f"🔑 Промокод: {promo[1]}\n"
        f"📝 Тип: {promo[2]}\n"
        f"💰 Значение: {promo[3]}\n"
        f"📅 Срок действия: {promo[4] or 'Бессрочный'}\n"
        f"🔢 Использовано: {promo[6]}/{promo[5] if promo[5] > 0 else '∞'}\n"
        f"🆔 ID: {promo[0]}"
    )
    
    await callback.message.edit_text(text, reply_markup=admin_promos_list(promo_id))
    await callback.answer()

@router.callback_query(F.data.startswith("delete_promo_"))
async def delete_promocode(callback: CallbackQuery):
    promo_id = int(callback.data.split("_")[2])
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_{promo_id}")],
        [InlineKeyboardButton(text="❌ Нет, отмена", callback_data=f"promo_detail_{promo_id}")]
    ])
    await callback.message.edit_text("⚠️ Вы уверены, что хотите удалить этот промокод?", reply_markup=keyboard)

@router.callback_query(F.data.startswith("confirm_delete_"))
async def confirm_delete_promocode(callback: CallbackQuery):
    promo_id = int(callback.data.split("_")[2])
    db.delete_promocode(promo_id)
    await callback.message.edit_text("✅ Промокод успешно удален!", reply_markup=admin_promos_menu())

@router.callback_query(F.data == "edit_promo")
async def edit_promocode(callback: CallbackQuery):
    # Здесь будет реализация редактирования промокода
    await callback.answer("Редактирование промокодов в разработке", show_alert=True)

@router.callback_query(F.data == "back_to_promos_menu")
async def back_to_promos_menu(callback: CallbackQuery):
    await callback.message.edit_text("🎫 Управление промокодами:", reply_markup=admin_promos_menu())
    await callback.answer()

# Обработчики для товаров
@router.callback_query(F.data == "add_product")
async def start_adding_product(callback: CallbackQuery, state: FSMContext):
    categories = db.get_all_categories()
    
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(text=cat[1], callback_data=f"product_cat_{cat[0]}")
    builder.button(text="Назад", callback_data="🛒 Товары")
    builder.adjust(1)
    
    await state.set_state(AddProduct.category)
    await callback.message.edit_text("📁 Выберите категорию для товара:", reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(AddProduct.category, F.data.startswith("product_cat_"))
async def process_category(callback: CallbackQuery, state: FSMContext):
    cat_id = callback.data.split("_")[2]
    if cat_id == "0":
        cat_id = None
    else:
        cat_id = int(cat_id)
    
    await state.update_data(category_id=cat_id)
    
    if cat_id:
        subcategories = db.get_subcategories(cat_id)
        
        if subcategories:
            builder = InlineKeyboardBuilder()
            for subcat in subcategories:
                # Изменяем формат callback_data
                builder.button(text=subcat[1], callback_data=f"product_subcat_{cat_id}_{subcat[0]}")
            # Изменяем формат для "Без подкатегории"
            builder.button(text="Без подкатегории", callback_data=f"product_subcat_{cat_id}_0")
            builder.button(text="❌ Отмена", callback_data="admin_cancel")
            builder.adjust(1)
            
            await state.set_state(AddProduct.subcategory)
            await callback.message.edit_text("📂 Выберите подкатегорию для товара:", reply_markup=builder.as_markup())
            await callback.answer()
            return
    
    await state.set_state(AddProduct.name)
    await callback.message.edit_text("Введите название товара:", reply_markup=admin_cancel_action())
    await callback.answer()

@router.callback_query(AddProduct.subcategory, F.data.startswith("product_subcat_"))
async def process_subcategory(callback: CallbackQuery, state: FSMContext):
    # Получаем все части callback_data
    parts = callback.data.split("_")
    # parts[0] = "product"
    # parts[1] = "subcat"
    # parts[2] = ID категории
    # parts[3] = ID подкатегории
    
    # Проверяем, что есть достаточно частей
    if len(parts) < 4:
        await callback.answer("Ошибка в данных, попробуйте снова")
        return
    
    cat_id = int(parts[2])
    subcat_id = parts[3]
    
    if subcat_id == "0":
        subcat_id = None
    else:
        subcat_id = int(subcat_id)
    
    # Обновляем состояние с обоими ID
    await state.update_data(
        category_id=cat_id,
        subcategory_id=subcat_id
    )
    
    await state.set_state(AddProduct.name)
    await callback.message.edit_text("Введите название товара:", reply_markup=admin_cancel_action())
    await callback.answer()


@router.message(AddProduct.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AddProduct.description)
    await message.answer("Введите описание товара:")

@router.message(AddProduct.description)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AddProduct.price)
    await message.answer("Введите цену товара:")

@router.message(AddProduct.price)
async def process_price(message: Message, state: FSMContext):
    try:
        price = float(message.text)
        await state.update_data(price=price)
        await state.set_state(AddProduct.command_template)
        await message.answer("Введите шаблон команды для сервера (используйте {nickname} и {quantity}):\nПример: give {nickname} apple {quantity}")
    except ValueError:
        await message.answer("❌ Введите число!")

@router.message(AddProduct.command_template)
async def process_command_template(message: Message, state: FSMContext):
    data = await state.get_data()
    db.add_product(
        name=data['name'],
        description=data['description'],
        price=data['price'],
        command_template=message.text,
        category_id=data['category_id'],
        subcategory_id=data.get('subcategory_id')  # может быть None
    )
    await message.answer("✅ Товар успешно добавлен!", reply_markup=admin_main_menu())
    await state.clear()

@router.callback_query(F.data == "list_product")
async def list_products(callback: CallbackQuery):
    categories = db.get_all_categories()
    
    if not categories:
        await callback.message.edit_text("❌ Категории не найдены", reply_markup=admin_products_menu())
        return
        
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(text=cat[1], callback_data=f"category_{cat[0]}")
    builder.button(text="Назад", callback_data="🛒 Товары")
    builder.button(text="➕ Добавить категорию", callback_data="add_category")
    builder.adjust(2)
    
    await callback.message.edit_text("📁 Выберите категорию:", reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("category_"))
async def show_category_products(callback: CallbackQuery):
    category_id = int(callback.data.split("_")[1])
    category = db.get_category(category_id)
    
    if not category:
        await callback.answer("❌ Категория не найдена", show_alert=True)
        return
    
    products = db.get_products_by_category(category_id)
    subcategories = db.get_subcategories(category_id)
    
    builder = InlineKeyboardBuilder()
    
    for subcat in subcategories:
        builder.button(text=f"📂 {subcat[1]}", callback_data=f"subcategory_{subcat[0]}")
    for product in products:
        builder.button(text=f"🛒 {product[1]} - {product[3]} руб", callback_data=f"show_product_{product[0]}")
    
    # Кнопка добавления подкатегории
    builder.button(text="➕ Добавить подкатегорию", callback_data=f"add_subcategory_{category_id}")
    # Кнопка возврата
    builder.button(text="🔙 Назад", callback_data="list_product")
    
    builder.adjust(1)
    
    text = f"📁 Категория: {category[1]}\n\n"
    
    if subcategories:
        text += "Подкатегории:\n"
    
    if products:
        text += "\nТовары без подкатегории:"
    
    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("show_product_"))
async def show_product_details(callback: CallbackQuery):
    try:
        # Получаем ID продукта из callback_data
        product_id = int(callback.data.split("_")[2])
    except (IndexError, ValueError):
        await callback.answer("❌ Ошибка формата данных", show_alert=True)
        return
    
    product = db.get_product(product_id)
    
    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return
    
    text = (
        f"🛒 <b>{product[1]}</b>\n\n"
        f"📝 Описание: {product[2] or 'отсутствует'}\n"
        f"💰 Цена: {product[3]} руб\n"
        f"⚙️ Команда: {product[4]}"
    )
    
    await callback.message.edit_text(text, reply_markup=admin_products_edit(product_id))
    await callback.answer()

@router.callback_query(F.data.startswith("product_"))
async def show_product_details(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    product = db.get_product(product_id)
    
    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return
    
    text = (
        f"🛒 <b>{product[1]}</b>\n\n"
        f"📝 Описание: {product[2] or 'отсутствует'}\n"
        f"💰 Цена: {product[3]} руб\n"
        f"⚙️ Команда: {product[4]}"
    )
    
    await callback.message.edit_text(text, reply_markup=admin_products_edit(product_id))
    await callback.answer()

@router.callback_query(F.data.startswith("add_subcategory_"))
async def start_adding_subcategory(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split("_")[2])
    await state.set_state(AddSubcategory.name)
    await state.update_data(category_id=category_id)
    await callback.message.edit_text("📂 Введите название подкатегории:")
    await callback.answer()

@router.message(AddSubcategory.name)
async def process_subcategory_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AddSubcategory.description)
    await message.answer("📝 Введите описание подкатегории (или 'пропустить'):", reply_markup=admin_skip())

@router.message(AddSubcategory.description)
async def process_subcategory_description(message: Message, state: FSMContext):
    data = await state.get_data()
    description = "" if message.text == "пропустить" else message.text
    db.add_subcategory(data['name'], data['category_id'], description)
    await message.answer(f"✅ Подкатегория '{data['name']}' успешно добавлена!", reply_markup=admin_main_menu())
    await state.clear()

@router.callback_query(F.data.startswith("edit_products_"))
async def edit_product_handler(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[2])
    # Здесь будет реализация редактирования товара
    await callback.answer("Редактирование товара в разработке", show_alert=True)

@router.callback_query(F.data.startswith("delete_products_"))
async def delete_product_handler(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[2])
    db.delete_product(product_id)
    await callback.message.edit_text("✅ Товар успешно удален!", reply_markup=admin_products_menu())
    await callback.answer()

# Обработчики для категорий
@router.callback_query(F.data == "add_category")
async def start_adding_category(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddCategory.name)
    await callback.message.edit_text("📁 Введите название категории:", reply_markup=admin_cancel_action())
    await callback.answer()

@router.message(AddCategory.name)
async def process_category_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AddCategory.description)
    await message.answer("📝 Введите описание категории (или '-' прочерк):")

@router.callback_query(F.data.startswith("subcategory_"))
async def show_subcategory(callback: CallbackQuery):
    subcategory_id = int(callback.data.split("_")[1])
    subcategory = db.get_subcategory(subcategory_id)
    
    if not subcategory:
        await callback.answer("❌ Подкатегория не найдена", show_alert=True)
        return
    
    # Получаем товары именно этой подкатегории
    products = db.get_products_by_subcategory(subcategory_id)
    
    builder = InlineKeyboardBuilder()
    
    # Кнопки для товаров подкатегории
    for product in products:
        builder.button(text=f"🛒 {product[1]} - {product[3]} руб", callback_data=f"show_product_{product[0]}")
    
    builder.button(text="✏️ Редактировать подкатегорию", callback_data=f"edit_subcategory_{subcategory_id}")
    builder.button(text="🗑️ Удалить подкатегорию", callback_data=f"delete_subcategory_{subcategory_id}")
    builder.button(text="🔙 Назад", callback_data=f"category_{subcategory['category_id']}")
    builder.adjust(1)
    
    await callback.message.edit_text(
        f"📂 Подкатегория: {subcategory[1]}\n\n"
        f"{subcategory[2] or 'Описание отсутствует'}\n\n"
        f"Товары ({len(products)}):",
        reply_markup=builder.as_markup()
    )
    await callback.answer()



@router.callback_query(F.data.startswith("delete_subcategory_"))
async def delete_subcategory_handler(callback: CallbackQuery):
    try:
        # Извлекаем ID подкатегории из callback_data
        subcategory_id = int(callback.data.split("_")[2])
    except (IndexError, ValueError):
        await callback.answer("❌ Ошибка формата данных", show_alert=True)
        return
    
    # Получаем информацию о подкатегории
    subcategory = db.get_subcategory(subcategory_id)
    
    if not subcategory:
        await callback.answer("❌ Подкатегория не найдена", show_alert=True)
        return
    
    # Перемещаем товары в родительскую категорию
    db.move_products_to_category(subcategory_id, subcategory['category_id'])
    
    # Удаляем подкатегорию
    db.delete_subcategory(subcategory_id)
    
    # Отправляем сообщение об успехе
    await callback.message.edit_text(
        f"✅ Подкатегория удалена! Товары перемещены в категорию.",
        reply_markup=admin_categories_menu()
    )
    await callback.answer()


@router.message(AddCategory.description)
async def process_category_description(message: Message, state: FSMContext):
    data = await state.get_data()
    description = "" if message.text == "-" else message.text
    db.add_category(data['name'], description)
    await message.answer(f"✅ Категория '{data['name']}' успешно добавлена!", reply_markup=admin_categories_menu())
    await state.clear()

@router.callback_query(F.data == "admin_cancel")
async def admin_cancel_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Действие отменено", reply_markup=admin_main_menu())
    await callback.answer()

@router.callback_query(F.data == "back_to_products_menu")
async def back_to_products_menu(callback: CallbackQuery):
    await callback.message.edit_text("🛒 Управление товарами:", reply_markup=admin_products_menu())
    await callback.answer()