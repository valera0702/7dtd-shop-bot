from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def admin_main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🛒 Товары")],
        [KeyboardButton(text="🎫 Промокоды")],
        [KeyboardButton(text="Главное меню")]
    ])

def admin_subcategories_menu():

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🗂 Список подкатегорий", callback_data="list_subcategory")
    )
    builder.row(
        InlineKeyboardButton(text="➕ Добавить подкатегорию", callback_data="add_subcategory_generic")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin_main_menu")
    )
    return builder.as_markup()

def admin_promos_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать промокод", callback_data="create_promo")],
        [InlineKeyboardButton(text="📋 Список промокодов", callback_data="list_promos")] #выводит список промокодов инлайн кнопками,
    ])


def admin_promos_list(promo_id=None):
    keyboard = [
        [InlineKeyboardButton(text="🗑️ Удалить промокод", callback_data=f"delete_promo_{promo_id}")],
        [InlineKeyboardButton(text="✏️ Редактировать промокод", callback_data=f"edit_promo_{promo_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="list_promos")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def admin_products_menu():#Открывается после кнопки 🛒 Товары
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить товар", callback_data="add_product")],
        [InlineKeyboardButton(text="📋 Список товаров ", callback_data="list_product")],
    ])
#add_product у продукта должно быть: Категория (или без категории),подкатегория(или без подкатегории), имя, описание, rcon команда

#list_product выводит:
#Список категорий
# Подкатегории в категории
#  Список товаров в подкатегории


def admin_categories_menu():#Под списком категорий добавить кнопку
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить категорию", callback_data="add_category")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="list_product")]
    ])
def admin_category():#При выборе категори добавить 4 кнопки
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать категорию", callback_data="edit_category")],
        [InlineKeyboardButton(text="🗑️ Удалить категорию", callback_data="delete_category")],
        [InlineKeyboardButton(text="➕ Добавить подкатегорию", callback_data="add_podcategory")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="возврат в admin_categories_menu")]

    ])

def admin_podcategory(): #При выборе подкатегории добавить 3 кнопки
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать подкатегорию", callback_data="edit_podcategory")],
        [InlineKeyboardButton(text="🗑️ Удалить подкатегорию", callback_data="delete_podcategory")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="возврат в категорию")]

    ])

def admin_products_edit(product_id):
    keyboard = [
        [InlineKeyboardButton(text="✏️ Редактировать товар", callback_data=f"edit_products_{product_id}")],
        [InlineKeyboardButton(text="🗑️ Удалить товар", callback_data=f"delete_products_{product_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_products_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def admin_cancel_action():
    """Инлайн-клавиатура для отмены действий (используется в инлайн-режиме)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel")]
    ])

def admin_skip():
    """Текстовая клавиатура для отмены действий (используется в обычных сообщениях)"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="пропустить")]],
        resize_keyboard=True
    )













# keyboards.py

def main_menu():
    """Главное меню пользователя"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 Магазин"), KeyboardButton(text="🛒 Корзина")],
            [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="📦 Мои покупки")],
            [KeyboardButton(text="👥 Рефералы")]
        ],
        resize_keyboard=True
    )

def shop_menu():
    """Меню магазина"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📂 Категории", callback_data="show_categories")]
    ])

def back_to_main_menu():
    """Кнопка возврата в главное меню"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🏠 Главное меню")]],
        resize_keyboard=True
    )

def back_to_shop_menu():
    """Кнопка возврата в меню магазина"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_shop")]
    ])

def categories_keyboard():
    """Клавиатура с категориями товаров"""
    categories = db.get_all_categories()
    builder = InlineKeyboardBuilder()
    
    for category in categories:
        builder.button(text=category['name'], callback_data=f"category_{category['id']}")
    
    builder.button(text="🔙 Назад", callback_data="back_to_shop")
    builder.adjust(1)
    return builder.as_markup()

def subcategories_keyboard(category_id):
    """Клавиатура с подкатегориями для категории"""
    subcategories = db.get_subcategories(category_id)
    builder = InlineKeyboardBuilder()
    
    for subcat in subcategories:
        builder.button(text=subcat['name'], callback_data=f"subcategory_{subcat['id']}")
    
    builder.button(text="🔙 Назад", callback_data="show_categories")
    builder.adjust(1)
    return builder.as_markup()

def products_keyboard(subcategory_id):
    """Клавиатура с товарами в подкатегории"""
    products = db.get_products_by_subcategory(subcategory_id)
    builder = InlineKeyboardBuilder()
    
    for product in products:
        builder.button(text=f"{product['name']} - {product['price']} руб", callback_data=f"product_{product['id']}")
    
    builder.button(text="🔙 Назад", callback_data=f"category_{db.get_subcategory(subcategory_id)['category_id']}")
    builder.adjust(1)
    return builder.as_markup()

def product_detail_keyboard(product_id):
    """Клавиатура для детального просмотра товара"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить в корзину", callback_data=f"add_to_cart_{product_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"back_to_products_{product_id}")]
    ])

def balance_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пополнить баланс", callback_data="topup_balance")],
        [InlineKeyboardButton(text="Ввести промокод", callback_data="enter_promo")]
    ])

def confirm_payment_keyboard(pay_url: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить", url=pay_url)],
        [InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data="confirm_payment")],
        [InlineKeyboardButton(text="❌ Отменить оплату", callback_data="cancel_payment")]
    ])

def user_cart_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[ #Вывод списком товаров в корзине inline кнопками
        [InlineKeyboardButton(text="Оформить заказ", callback_data="checkout")],
        [InlineKeyboardButton(text="Очистить корзину", callback_data="clear_cart")],
        [InlineKeyboardButton(text="Назад в магазин", callback_data="back_to_shop")]
    ])

def user_produst_in_cart_keyboard(): #Для редактирования выбранного товара в корзине
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Изменить количество", callback_data="edit_cart")],
        [InlineKeyboardButton(text="Убрать из корзины", callback_data="edit_cart")],
    ])