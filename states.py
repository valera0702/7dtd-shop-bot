from aiogram.fsm.state import StatesGroup, State

class CreatePromo(StatesGroup):
    waiting_promo_type = State()
    waiting_promo_code = State()
    waiting_promo_value = State()
    waiting_promo_expiration = State()
    waiting_promo_max_uses = State()

class PromoStates(StatesGroup):
    waiting_promo_input = State()

class PaymentStates(StatesGroup):
    waiting_for_amount = State()
    waiting_payment_confirmation = State()

class AddCategory(StatesGroup):
    name = State()
    description = State()

class ManageCategory(StatesGroup):
    select_category = State()
    edit_name = State()
    edit_description = State()
    edit_options = State()

class AddProduct(StatesGroup):
    name = State()
    description = State()
    price = State()
    subcategory = State()
    category = State()
    command_template = State()

class UserStates(StatesGroup):
    waiting_for_nickname = State()

class AdminStates(StatesGroup):
    add_product = State()
    manage_categories = State()
    create_promo = State()

class UserStates(StatesGroup):
    waiting_for_nickname = State()
    cart = State()
    checkout = State()
    payment = State()
    promo = State()

class AddSubcategory(StatesGroup):
    name = State()
    description = State()

class EditSubcategory(StatesGroup):
    name = State()
    description = State()

#class EditProduct(StatesGroup):
