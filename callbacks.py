from aiogram.filters.callback_data import CallbackData

class CategoryCallback(CallbackData, prefix="category"):
    action: str
    id: int

class ProductCallback(CallbackData, prefix="product"):
    action: str
    id: int

class SubcategoryCallback(CallbackData, prefix="subcat"):
    action: str
    id: int


class PromoCallback(CallbackData, prefix="promo"):
    action: str
    id: int = None
    value: str = None