from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from states import PaymentStates, PromoStates, UserStates
from database import db
from handlers.payment_handlers import create_crypto_invoice, get_current_usdt_rate
from datetime import datetime
from aiogram.filters.callback_data import CallbackData

from keyboards import balance_menu, confirm_payment_keyboard

class CategoryCallback(CallbackData, prefix="category"):
    id: int
    action: str

class ProductCallback(CallbackData, prefix="product"):
    id: int
    action: str

router = Router()

# Главное меню (ReplyKeyboard)
def main_menu_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 Магазин"), KeyboardButton(text="💰 Баланс")],
            [KeyboardButton(text="👥 Рефералы"), KeyboardButton(text="🛒 Корзина")],
            [KeyboardButton(text="🏠 Главное меню")]
        ],
        resize_keyboard=True
    )

# Inline клавиатура для магазина
def shop_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📂 Категории", callback_data="show_categories")],
        [InlineKeyboardButton(text="🛒 Моя корзина", callback_data="show_cart")]
    ])

# Клавиатура баланса


# Кнопка "Назад в магазин"
def back_to_shop_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Вернуться в магазин", callback_data="back_to_shop")]
    ])
@router.message(Command("start"))
async def cmd_start(message: Message, command: CommandObject = None, state: FSMContext = None):
    current_state = await state.get_state()
    
    if current_state == PaymentStates.waiting_payment_confirmation:
        await handle_start_during_payment(message, state)
        return
    user_id = message.from_user.id
    is_new_user = db.add_user(user_id)
    bot_info = await message.bot.get_me()
    bot_username = bot_info.username
    
    ref_bonus = 0
    ref_message = ""
    
    if command and command.args and command.args.startswith("ref"):
        try:
            referrer_id = int(command.args[3:])
            
            if referrer_id == user_id:
                ref_message = "\n❌ Нельзя использовать собственную реферальную ссылку!"
                
            elif not is_new_user:
                ref_message = "\n❌ Реферальная ссылка действует только для новых пользователей"
                
            elif db.get_referrer(user_id) is not None:
                ref_message = "\n❌ Вы уже зарегистрированы по реферальной ссылке"
                
            else:
                db.add_referral(referrer_id, user_id)
                ref_bonus = 0
                db.update_balance(user_id, ref_bonus)
                ref_message = f"\n🎁 Получено бонусов за регистрацию: {ref_bonus} RUB"
                db.update_balance(referrer_id, 50)  # 100 RUB за привлечение
                
                try:
                    await message.bot.send_message(
                        referrer_id,
                        f"🎉 Новый реферал зарегистрировался по вашей ссылке!\n"
                        f"👤 ID: {user_id}\n"
                        f"💰 Вы получили 50 RUB за привлечение!\n"
                        f"👥 Всего рефералов: {db.get_referrals_count(referrer_id)}"
                    )
                except:
                    pass
                    
        except ValueError:
            ref_message = "\n❌ Некорректная реферальная ссылка"

    ref_link = f"https://t.me/umbrella_x1_shop_bot?start=ref{user_id}"
    welcome_text = (
        "👋 Добро пожаловать в магазин сервера 7 Days to Die!\n"
        f"{ref_message}\n\n"
        f"👥 Ваша реферальная ссылка:\n{ref_link}\n\n"
        "Приглашайте друзей и получайте:\n"
        "- 50 RUB за каждого привлеченного пользователя\n"
        "- 10% с их пополнений баланса!"
    )
    await message.answer(welcome_text, reply_markup=main_menu_kb())

@router.message(F.text == "🛒 Магазин")
async def shop_menu(message: Message):
    await message.answer(
        "Добро пожаловать в магазин! Выберите действие:",
        reply_markup=shop_keyboard()
    )

@router.message(F.text == "💰 Баланс")
async def show_balance_menu(message: Message):
    balance = db.get_balance(message.from_user.id)
    await message.answer(
        f"💳 Ваш баланс: {balance:.2f} RUB",
        reply_markup=balance_menu()
    )

@router.message(F.text == "🛒 Корзина")
async def show_cart_handler(message: Message):
    await show_cart(message)

# Реализация магазина через Inline кнопки
@router.callback_query(F.data == "show_categories")
async def show_categories(callback: CallbackQuery):
    categories = db.get_all_categories()
    if not categories:
        await callback.message.edit_text("Категории пока не добавлены")
        return
    
    buttons = [
        [InlineKeyboardButton(text=cat['name'], callback_data=CategoryCallback(id=cat['id'], action="view").pack())]
        for cat in categories
    ]
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_shop")])
    
    await callback.message.edit_text("Выберите категорию:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@router.callback_query(CategoryCallback.filter(F.action == "view"))
async def show_category_products(callback: CallbackQuery, callback_data: CategoryCallback):
    category = db.get_category(callback_data.id)
    products = db.get_products_by_category(callback_data.id)
    
    if not products:
        await callback.answer("В этой категории пока нет товаров")
        return
    
    text = f"<b>{category[1]}</b>\n{category[2] or 'Описание отсутствует'}"
    buttons = [
        [InlineKeyboardButton(
            text=f"{p[1]} - {p[3]} руб",
            callback_data=ProductCallback(id=p[0], action="view").pack())]
        for p in products
    ]
    buttons.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="show_categories"),
        InlineKeyboardButton(text="🛒 Корзина", callback_data="show_cart")
    ])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await callback.answer()

@router.callback_query(ProductCallback.filter(F.action == "view"))
async def show_product_details(callback: CallbackQuery, callback_data: ProductCallback):
    product = db.get_product(callback_data.id)
    if not product:
        await callback.answer("Товар не найден")
        return
    
    text = (
        f"<b>{product[1]}</b>\n\n"
        f"<i>{product[2] or 'Описание отсутствует'}</i>\n\n"
        f"💵 Цена: <b>{product[3]} руб</b>\n"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить в корзину", callback_data=ProductCallback(id=product[0], action="add_to_cart").pack())],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data=CategoryCallback(id=product[5], action="view").pack()),
            InlineKeyboardButton(text="🛒 Корзина", callback_data="show_cart")
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@router.callback_query(ProductCallback.filter(F.action == "add_to_cart"))
async def add_to_cart(callback: CallbackQuery, callback_data: ProductCallback):
    db.add_to_cart(callback.from_user.id, callback_data.id)
    product = db.get_product(callback_data.id)
    
    text = (
        f"<b>{product[1]}</b>\n\n"
        f"✅ Товар добавлен в корзину!\n\n"
        f"<i>{product[2] or ''}</i>"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Перейти в корзину", callback_data="show_cart")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=CategoryCallback(id=product[5], action="view").pack())]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

# В основном коде бота - исправленная функция show_cart
async def show_cart(message: Message):
    user_id = message.from_user.id
    cart_items = db.get_cart_items(user_id)
    
    if not cart_items:
        await message.answer("🛒 Ваша корзина пуста", reply_markup=back_to_shop_kb())
        return
    
    total = 0
    text = "<b>🛒 Ваша корзина</b>\n\n"
    for item in cart_items:
        # item[0] - название товара, item[1] - цена, item[2] - количество
        name = item[0]
        price = item[1]
        quantity = item[2]
        item_total = price
        text += f"• {item_total} руб\n"
        total += item_total
    
    text += f"\n<b>Итого: {total} руб</b>"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оформить заказ", callback_data="checkout")],
        [InlineKeyboardButton(text="🧹 Очистить корзину", callback_data="clear_cart")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_shop")]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data == "show_cart")
async def show_cart_callback(callback: CallbackQuery):
    await show_cart(callback.message)

@router.callback_query(F.data == "back_to_shop")
async def back_to_shop(callback: CallbackQuery):
    await show_categories(callback)

@router.callback_query(F.data == "checkout")
async def process_checkout(callback: CallbackQuery):
    user_id = callback.from_user.id
    nickname = db.get_user_nickname(user_id)
    if not nickname:
        await callback.message.edit_text("❌ Для заказа требуется игровой ник\nВведите /register", reply_markup=back_to_shop_kb())
        await callback.answer()
        return
    
    cart_items = db.get_cart_items(user_id)
    total = sum(item[2] * item[3] for item in cart_items)
    balance = db.get_balance(user_id)
    
    if balance < total:
        await callback.message.edit_text(
            f"❌ Недостаточно средств!\nБаланс: {balance} руб\nТребуется: {total} руб",
            reply_markup=back_to_shop_kb()
        )
        await callback.answer()
        return
    
    # Отправка команд на сервер (заглушка)
    for item in cart_items:
        product = db.get_product(item[0])
        print(f"EXECUTE: {product[4].format(nickname=nickname, quantity=item[3])}")
    
    db.update_balance(user_id, -total)
    db.clear_cart(user_id)
    await callback.message.edit_text(
        f"✅ Заказ оформлен!\nИгрок: {nickname}\nСумма: {total} руб",
        reply_markup=back_to_shop_kb()
    )
    await callback.answer()

# Обработчики баланса
@router.callback_query(F.data == "show_balance")
async def show_balance_inline(callback: CallbackQuery):
    balance = db.get_balance(callback.from_user.id)
    await callback.message.edit_text(
        f"💳 Ваш баланс: {balance:.2f} RUB",
        reply_markup=balance_menu()
    )
    await callback.answer()

@router.callback_query(F.data == "topup_balance")
async def request_payment_amount(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("💰 Укажите сумму в рублях:")
    await state.set_state(PaymentStates.waiting_for_amount)
    await callback.answer()

@router.callback_query(F.data == "enter_promo")
async def request_promocode(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PromoStates.waiting_promo_input)
    await callback.message.answer("🔑 Введите промокод:")
    await callback.answer()

# Обработка состояний
@router.message(PaymentStates.waiting_for_amount)
async def process_payment_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text)
        if amount < 1 or amount > 20000:
            await message.answer("Сумма должна быть от 1 до 20 000 RUB")
            return
        
        usdt_rate = await get_current_usdt_rate()
        usdt_amount = amount / usdt_rate
        invoice = await create_crypto_invoice(usdt_amount, message.from_user.id)
        
        if not invoice or not invoice.get('ok'):
            await message.answer("❌ Ошибка при создании счета")
            await state.clear()
            return
        
        pay_url = invoice['result']['pay_url']
        await state.update_data(
            invoice_id=invoice['result']['invoice_id'],
            pay_url=pay_url,
            amount=amount,
            usdt_amount=usdt_amount
        )
        await state.set_state(PaymentStates.waiting_payment_confirmation)
        

        
        await message.answer(
            f"💸 Счет на сумму {amount} RUB создан!\n"
            f"🪙 Эквивалент в USDT: {usdt_amount:.4f}\n\n"
            "После оплаты нажмите 'Подтвердить оплату'",
            reply_markup=confirm_payment_keyboard(pay_url=pay_url)
        )
    except ValueError:
        await message.answer("Пожалуйста, введите число")

@router.message(PromoStates.waiting_promo_input)
async def process_promocode(message: Message, state: FSMContext):
    promo_code = message.text.strip()
    promo_info = db.get_promocode(promo_code)
    
    if not promo_info:
        await message.answer("❌ Промокод не найден")
        await state.clear()
        return
    
    promo_id, _, promo_type, value, expiration, max_uses, used_count = promo_info
    user_id = message.from_user.id
    
    if expiration and datetime.now() > datetime.fromisoformat(expiration):
        await message.answer("⌛️ Промокод просрочен")
        await state.clear()
        return
        
    if used_count >= max_uses:
        await message.answer("🚫 Лимит использований исчерпан")
        await state.clear()
        return
        
    if db.is_promocode_used(user_id, promo_id):
        await message.answer("⚠️ Вы уже использовали этот промокод")
        await state.clear()
        return
        
    if promo_type == "balance":
        db.update_balance(user_id, value)
        db.mark_promocode_used(user_id, promo_id)
        await message.answer(f"🎉 Баланс пополнен на {value} RUB")
    elif promo_type == "discount":
        await state.update_data(discount=value)
        db.mark_promocode_used(user_id, promo_id)
        await message.answer(f"🎉 Получено {value}% скидки на товары")
    
    await state.clear()

@router.message(F.text == "👥 Рефералы")
async def show_referral_info(message: Message):
    user_id = message.from_user.id
    ref_count = db.get_referrals_count(user_id)
    ref_link = f"https://t.me/umbrella_x1_shop_bot?start=ref{user_id}"
    await message.answer(
        "👥 Реферальная система\n\n"
        f"🔗 Ваша ссылка: {ref_link}\n"
        f"👤 Приглашено: {ref_count}\n\n"
        "💎 Бонусы:\n"
        "- 50 RUB за регистрацию\n"
        "- 10% с пополнений"
    )

@router.message(F.text == "🏠 Главное меню")
async def back_to_main(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state == PaymentStates.waiting_payment_confirmation:
        data = await state.get_data()
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=data['pay_url'])],
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_payment")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_payment")]
        ])
        await message.answer(
            "⚠️ Завершите оплату!\n"
            f"Сумма: {data['amount']} RUB",
            reply_markup=keyboard
        )
        return
        
    await state.clear()
    await message.answer("Главное меню:", reply_markup=main_menu_kb())

# Регистрация игрового ника
@router.message(Command("register"))
async def start_registration(message: Message, state: FSMContext):
    await state.set_state(UserStates.waiting_for_nickname)
    await message.answer("Введите ваш игровой ник:")

@router.message(UserStates.waiting_for_nickname)
async def process_nickname(message: Message, state: FSMContext):
    nickname = message.text.strip()
    if not nickname.isprintable() or len(nickname) < 3 or len(nickname) > 20:
        await message.answer("❌ Некорректный ник (3-20 символов)")
        return
    
    db.update_user_nickname(message.from_user.id, nickname)
    await state.clear()
    await message.answer(f"✅ Ник {nickname} сохранён!")

# user_handlers.py

# Главное меню
@router.message(F.text == "🛒 Магазин")
async def shop_menu_handler(message: Message):
    await message.answer("Добро пожаловать в магазин! Выберите категорию:", reply_markup=shop_menu())

# Обработка кнопки "Категории"
@router.callback_query(F.data == "show_categories")
async def show_categories_handler(callback: CallbackQuery):
    await callback.message.edit_text("Выберите категорию:", reply_markup=categories_keyboard())
    await callback.answer()

# Просмотр категории
@router.callback_query(F.data.startswith("category_"))
async def show_category_handler(callback: CallbackQuery):
    category_id = int(callback.data.split("_")[1])
    category = db.get_category(category_id)
    
    if not category:
        await callback.answer("❌ Категория не найдена", show_alert=True)
        return
    
    # Проверяем есть ли подкатегории
    subcategories = db.get_subcategories(category_id)
    
    if subcategories:
        await callback.message.edit_text(
            f"📁 Категория: {category['name']}\n\nВыберите подкатегорию:",
            reply_markup=subcategories_keyboard(category_id)
        )
    else:
        # Если подкатегорий нет, сразу показываем товары
        await show_subcategory_handler(callback, category_id)
    
    await callback.answer()

# Просмотр подкатегории
@router.callback_query(F.data.startswith("subcategory_"))
async def show_subcategory_handler(callback: CallbackQuery, category_id: int):
    try:
        subcategory_id = int(callback.data.split("_")[1])
    except:
        # Если вызвано из категории без подкатегорий
        category_id = int(callback.data.split("_")[1])
        products = db.get_products_by_category(category_id)
        subcategory = {"name": db.get_category(category_id)['name']}
    else:
        subcategory = db.get_subcategory(subcategory_id)
        if not subcategory:
            await callback.answer("❌ Подкатегория не найдена", show_alert=True)
            return
        
        products = db.get_products_by_subcategory(subcategory_id)
    
    if not products:
        await callback.message.edit_text(
            f"📂 {subcategory['name']}\n\nТовары отсутствуют",
            reply_markup=back_to_shop_menu()
        )
        return
    
    builder = InlineKeyboardBuilder()
    for product in products:
        builder.button(text=f"{product['name']} - {product['price']} руб", callback_data=f"product_{product['id']}")
    
    builder.button(text="🔙 Назад", callback_data="show_categories")
    builder.adjust(1)
    
    await callback.message.edit_text(
        f"📂 {subcategory['name']}\n\nВыберите товар:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

# Просмотр товара
@router.callback_query(ProductCallback.filter(F.action == "view"))
async def show_product_handler(callback: CallbackQuery, callback_data: ProductCallback):
    product_id = callback_data.id
    product = db.get_product(product_id)

    if not product:
        await callback.answer("❌ Товар не найден или был удален.", show_alert=True)
        await callback.message.edit_text("К сожалению, этот товар больше не доступен.")
        return

    price_line = f"💰 Цена: {product['price']} RUB"
    if product['count'] > 1:
        price_line += f" (за {product['count']} шт.)"
    quality_line = ""
    if product['quality'] > 1:
        quality_line = f"⭐ Качество: {product['quality']}\n"
        
    text = (
        f"🛒 <b>{product['name']}</b>\n\n"
        f"📝 Описание: {product['description']}\n"
        f"{quality_line}"
        f"{price_line}"
    )
    builder = InlineKeyboardBuilder()
    builder.button(
        text="💳 Купить",
        callback_data=ProductCallback(id=product_id, action="buy").pack()
    )
    if product['subcategory_id']:
        builder.button(
            text="⬅️ Назад к списку",
            callback_data=SubcategoryCallback(id=product['subcategory_id'], action="view").pack()
        )
    else:
        builder.button(
            text="⬅️ Назад к списку",
            callback_data=CategoryCallback(id=product['category_id'], action="view").pack()
        )
    builder.adjust(1)
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# Добавление товара в корзину
@router.callback_query(F.data.startswith("add_to_cart_"))
async def add_to_cart_handler(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[3])
    user_id = callback.from_user.id
    
    # Добавляем товар в корзину
    db.add_to_cart(user_id, product_id)
    
    await callback.answer(f"✅ Товар добавлен в корзину!", show_alert=True)
    
    # Возвращаемся к списку товаров
    product = db.get_product(product_id)
    if product and product['subcategory_id']:
        await show_subcategory_handler(callback, subcategory_id=product['subcategory_id'])
    else:
        await show_category_handler(callback, category_id=product['category_id'])

# Навигация назад
@router.callback_query(F.data == "back_to_shop")
async def back_to_shop_handler(callback: CallbackQuery):
    await callback.message.edit_text("Добро пожаловать в магазин! Выберите категорию:", reply_markup=shop_menu())
    await callback.answer()

@router.callback_query(F.data.startswith("back_to_products_"))
async def back_to_products_handler(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[3])
    product = db.get_product(product_id)
    
    if product and product['subcategory_id']:
        await show_subcategory_handler(callback, subcategory_id=product['subcategory_id'])
    elif product:
        await show_category_handler(callback, category_id=product['category_id'])
    else:
        await back_to_shop_handler(callback)