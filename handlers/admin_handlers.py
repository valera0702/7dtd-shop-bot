# -*- coding: utf-8 -*-
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from aiogram.filters import Command
from states import AddProduct, AddCategory, AddSubcategory
from database import db
from keyboards import admin_main_menu, admin_products_menu, admin_categories_menu, admin_subcategories_menu, admin_cancel_action
from callbacks import CategoryCallback, ProductCallback, SubcategoryCallback
from config import ADMIN_IDS

router = Router()



# =================================================================================
# ### 2. ГЛАВНОЕ МЕНЮ АДМИНИСТРАТОРА ###
# =================================================================================

@router.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id in ADMIN_IDS:
        await message.answer("Добро пожаловать в админ-панель!", reply_markup=admin_main_menu())
    else:
        await message.answer("❌ У вас нет прав доступа к этой команде.")

@router.callback_query(F.data == "admin_main_menu")
async def back_to_admin_main_menu(callback: CallbackQuery):
    await callback.message.edit_text("Добро пожаловать в админ-панель!", reply_markup=admin_main_menu())
    await callback.answer()


# =================================================================================
# ### 3. УПРАВЛЕНИЕ ТОВАРАМИ (ПРОСМОТР И НАВИГАЦИЯ) ###
# =================================================================================

@router.callback_query(F.data == "manage_products")
async def manage_products(callback: CallbackQuery):
    await callback.message.edit_text("🛒 Управление товарами", reply_markup=admin_products_menu())
    await callback.answer()
@router.message(F.text == "🛒 Товары")
async def manage_products_text(message: Message):
    await message.answer("🛒 Управление товарами", reply_markup=admin_products_menu())


@router.callback_query(F.data == "list_product")
async def list_products(callback: CallbackQuery):
    categories = db.get_all_categories()
    if not categories:
        await callback.message.edit_text("❌ Категории не найдены", reply_markup=admin_products_menu())
        return

    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(
            text=cat['name'],
            callback_data=CategoryCallback(id=cat['id'], action="view_products_in_cat").pack()
        )
    builder.button(text="Назад", callback_data="manage_products")
    builder.adjust(2, 1)
    await callback.message.edit_text("📁 Выберите категорию для просмотра:", reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(CategoryCallback.filter(F.action == "view_products_in_cat"))
async def view_products_in_category(callback: CallbackQuery, callback_data: CategoryCallback):
    category_id = callback_data.id
    subcategories = db.get_subcategories(category_id)
    products = db.get_products_by_category(category_id)
    category_name = db.get_category_name(category_id)
    
    title = f"Управление категорией «{category_name}»:" if category_name else "Управление категорией:"
    builder = InlineKeyboardBuilder()

    if not subcategories and not products:
        title += "\n\nℹ️ В этой категории пока пусто."
    else:
        for subcat in subcategories:
            builder.button(
                text=f"📂 {subcat['name']}",
                callback_data=SubcategoryCallback(id=subcat['id'], action="view_products_in_subcat").pack()
            )
        for prod in products:
            builder.button(
                text=prod['name'],
                callback_data=ProductCallback(id=prod['id'], action="manage").pack()
            )

    builder.row(
        InlineKeyboardButton(text="➕ Добавить товар", callback_data="add_product"),
        InlineKeyboardButton(text="➕ Добавить подкатегорию", callback_data=CategoryCallback(id=category_id, action="add_sub_here").pack())
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Изменить категорию", callback_data=f"edit_category_{category_id}"),
        InlineKeyboardButton(text="🗑️ Удалить категорию", callback_data=f"delete_category_{category_id}")
    )
    builder.row(InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="list_product"))
    builder.adjust(1, 2, 1)

    await callback.message.edit_text(title, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(SubcategoryCallback.filter(F.action == "view_products_in_subcat"))
async def view_products_in_subcategory(callback: CallbackQuery, callback_data: SubcategoryCallback):
    subcategory_id = callback_data.id
    products = db.get_products_by_subcategory(subcategory_id)
    subcategory_info = db.get_subcategory_info(subcategory_id)

    if not subcategory_info:
        await callback.answer("❌ Подкатегория не найдена.", show_alert=True)
        return

    title = f"Товары в подкатегории «{subcategory_info['name']}»:"
    builder = InlineKeyboardBuilder()

    if not products:
        title += "\n\nℹ️ Здесь пока нет товаров."
    else:
        for prod in products:
            builder.button(
                text=prod['name'],
                callback_data=ProductCallback(id=prod['id'], action="manage").pack()
            )
    
    builder.button(
        text="⬅️ Назад в категорию", 
        callback_data=CategoryCallback(id=subcategory_info['category_id'], action="view_products_in_cat").pack()
    )
    builder.adjust(1)
    await callback.message.edit_text(title, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(ProductCallback.filter(F.action == "manage"))
async def show_product_details(callback: CallbackQuery, callback_data: ProductCallback):
    product_id = callback_data.id
    product = db.get_product(product_id)
    
    if not product:
        await callback.answer("❌ Товар не найден.", show_alert=True)
        await callback.message.edit_text("Товар был удален.", reply_markup=None)
        return
        
    price_line = f"💰 Цена: {product['price']} RUB"
    if product['count'] > 1:
        price_line += f" (за {product['count']} шт.)"

    quality_line = ""
    if product['quality'] > 1:
        quality_line = f"⭐ Качество: {product['quality']}\n"
        
    text = (
        f"Управление товаром: <b>{product['name']}</b>\n\n"
        f"📝 Описание: {product['description']}\n"
        f"{price_line}\n"
        f"{quality_line}"
        f"⚙️ Команда: {product['rcon_command']}"
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="🗑️ Удалить", callback_data=f"delete_product_{product_id}")
    builder.button(text="✏️ Изменить", callback_data=f"edit_product_{product_id}")

    if product['subcategory_id']:
        builder.button(
            text="⬅️ Назад к подкатегории",
            callback_data=SubcategoryCallback(id=product['subcategory_id'], action="view_products_in_subcat").pack()
        )
    else:
        builder.button(
            text="⬅️ Назад к категории",
            callback_data=CategoryCallback(id=product['category_id'], action="view_products_in_cat").pack()
        )
    builder.adjust(2, 1)
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


# =================================================================================
# ### 4. УПРАВЛЕНИЕ ТОВАРАМИ (ПРОЦЕСС ДОБАВЛЕНИЯ - FSM) ###
# =================================================================================

# Шаг 1: Нажатие кнопки "Добавить товар"
@router.callback_query(F.data == "add_product")
async def start_adding_product(callback: CallbackQuery, state: FSMContext):
    categories = db.get_all_categories()
    if not categories:
        await callback.message.edit_text("Сначала добавьте категории", reply_markup=admin_products_menu())
        return

    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(text=cat['name'], callback_data=CategoryCallback(id=cat['id'], action="add_product_to_cat").pack())
    builder.button(text="Назад", callback_data="manage_products")
    builder.adjust(2)

    await callback.message.edit_text("📁 Выберите категорию для товара:", reply_markup=builder.as_markup())
    await state.set_state(AddProduct.choosing_category)
    await callback.answer()

# Шаг 2: Выбор категории
@router.callback_query(CategoryCallback.filter(F.action == "add_product_to_cat"), AddProduct.choosing_category)
async def process_category(callback: CallbackQuery, callback_data: CategoryCallback, state: FSMContext):
    cat_id = callback_data.id
    await state.update_data(category_id=cat_id)
    subcategories = db.get_subcategories(cat_id)
    
    if subcategories:
        builder = InlineKeyboardBuilder()
        for subcat in subcategories:
            builder.button(
                text=subcat['name'],
                callback_data=SubcategoryCallback(id=subcat['id'], action="select_for_product").pack()
            )
        builder.button(text="Назад", callback_data="add_product")
        builder.adjust(2)
        await callback.message.edit_text("Выберите подкатегорию:", reply_markup=builder.as_markup())
        await state.set_state(AddProduct.choosing_subcategory)
    else:
        await callback.message.edit_text("В этой категории нет подкатегорий. Введите название товара:")
        await state.set_state(AddProduct.entering_name)
    await callback.answer()

# Шаг 3: Выбор подкатегории
@router.callback_query(SubcategoryCallback.filter(F.action == "select_for_product"), AddProduct.choosing_subcategory)
async def process_subcategory_choice(callback: CallbackQuery, callback_data: SubcategoryCallback, state: FSMContext):
    await state.update_data(subcategory_id=callback_data.id)
    await callback.message.edit_text("Введите название товара:")
    await state.set_state(AddProduct.entering_name)
    await callback.answer()

# Шаг 4: Ввод названия
@router.message(AddProduct.entering_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    skip_keyboard = InlineKeyboardBuilder()
    skip_keyboard.button(text="➡️ Пропустить", callback_data="skip_description")
    await message.answer(
        "📝 Введите описание для товара (или нажмите 'Пропустить'):",
        reply_markup=skip_keyboard.as_markup()
    )
    await state.set_state(AddProduct.entering_description)

# Шаг 5.1: Пропуск описания
@router.callback_query(F.data == "skip_description", AddProduct.entering_description)
async def skip_description_handler(callback: CallbackQuery, state: FSMContext):
    await state.update_data(description="")
    await callback.message.edit_text("💰 Введите цену товара (например, 150.50):")
    await state.set_state(AddProduct.entering_price)
    await callback.answer()

# Шаг 5.2: Ввод описания
@router.message(AddProduct.entering_description)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("💰 Введите цену товара (например, 150.50):")
    await state.set_state(AddProduct.entering_price)

# Шаг 6: Ввод цены
@router.message(AddProduct.entering_price)
async def process_price(message: Message, state: FSMContext):
    try:
        price = float(message.text)
        if price <= 0:
            await message.answer("Цена должна быть положительным числом.")
            return
        await state.update_data(price=price)
        await message.answer("⚙️ Введите RCON-команду для выдачи товара:")
        await state.set_state(AddProduct.rcon_command)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число для цены.")

# Шаг 7: Ввод RCON-команды
@router.message(AddProduct.rcon_command)
async def process_rcon_command(message: Message, state: FSMContext):
    await state.update_data(rcon_command=message.text)
    await message.answer("🔢 Введите количество товара в одной покупке (например, 100). Введите 1 для поштучных.")
    await state.set_state(AddProduct.entering_count)

# Шаг 8: Ввод количества
@router.message(AddProduct.entering_count)
async def process_count(message: Message, state: FSMContext):
    try:
        count = int(message.text)
        if count <= 0:
            await message.answer("Количество должно быть положительным числом.")
            return
        await state.update_data(count=count)
        await message.answer("⭐ Введите качество товара (от 1 до 6). Введите 1, если качество не применяется.")
        await state.set_state(AddProduct.entering_quality)
    except ValueError:
        await message.answer("Пожалуйста, введите целое число.")

# Шаг 9: Ввод качества (ФИНАЛ)
@router.message(AddProduct.entering_quality)
async def process_quality(message: Message, state: FSMContext):
    try:
        quality = int(message.text)
        if not 1 <= quality <= 6:
            await message.answer("Качество должно быть числом от 1 до 6.")
            return
        await state.update_data(quality=quality)
        data = await state.get_data()
        db.add_product(
            name=data['name'],
            description=data['description'],
            price=data['price'],
            count=data['count'],
            quality=data['quality'],
            rcon_command=data.get('rcon_command'),
            category_id=data['category_id'],
            subcategory_id=data.get('subcategory_id')
        )
        await message.answer("✅ Товар успешно добавлен!", reply_markup=admin_products_menu())
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите целое число от 1 до 6.")


# =================================================================================
# ### 5. УПРАВЛЕНИЕ КАТЕГОРИЯМИ ###
# =================================================================================
# (Здесь будет ваш код для добавления/удаления категорий)


# =================================================================================
# ### 6. УПРАВЛЕНИЕ ПОДКАТЕГОРИЯМИ ###
# =================================================================================

# Контекстное добавление подкатегории (кнопка внутри категории)
@router.callback_query(CategoryCallback.filter(F.action == "add_sub_here"))
async def start_adding_subcategory_here(callback: CallbackQuery, callback_data: CategoryCallback, state: FSMContext):
    category_id = callback_data.id
    await state.update_data(category_id=category_id)
    await callback.message.edit_text("📝 Введите название для новой подкатегории:")
    await state.set_state(AddSubcategory.entering_name)
    await callback.answer()

@router.message(AddSubcategory.entering_name)
async def process_subcategory_name_here(message: Message, state: FSMContext):
    data = await state.get_data()
    category_id = data.get('category_id')
    subcategory_name = message.text
    if category_id:
        db.add_subcategory(name=subcategory_name, category_id=category_id)
        await message.answer(f"✅ Подкатегория '{subcategory_name}' успешно добавлена!", reply_markup=admin_main_menu())
    else:
        await message.answer("❌ Произошла ошибка, ID категории не найден.")
    await state.clear()