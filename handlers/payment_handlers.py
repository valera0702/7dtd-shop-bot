import aiohttp
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from config import CRYPTO_PAY_TOKEN
from database import db
import aiohttp
from states import PaymentStates 
from config import REF_BONUS_REGISTRATION, REFERRAL_PERCENT

router = Router()



async def get_current_usdt_rate():
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=rub"
            async with session.get(url) as resp:
                data = await resp.json()
                return data['tether']['rub']
    except:
        return 80.0

async def create_crypto_invoice(amount: float, user_id: int):
    async with aiohttp.ClientSession() as session:
        url = "https://pay.crypt.bot/api/createInvoice"
        headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}
        data = {
            "asset": "USDT",
            "amount": str(amount),
            "paid_btn_name": "openBot",  # Кнопка "Открыть бота" после оплаты
            "paid_btn_url": "https://t.me/umbrella_x1_shop_bot"  # Ссылка на вашего бота
        }
        async with session.post(url, headers=headers, json=data) as resp:
            return await resp.json()



@router.callback_query(F.data == "cancel_payment", PaymentStates.waiting_payment_confirmation)
async def cancel_payment(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Пополнение баланса отменено.")
    await callback.answer()

@router.message(F.text == "❌ Отмена", PaymentStates.waiting_payment_confirmation)
async def cancel_payment_text(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Пополнение баланса отменено.", reply_markup=balance_menu())

@router.callback_query(F.data == "confirm_payment", PaymentStates.waiting_payment_confirmation)
async def confirm_payment(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data = await state.get_data()
    
    if not data.get('invoice_id'):
        await callback.answer("❌ Информация о счете не найдена", show_alert=True)
        return
        
    try:
        # Проверяем статус счета
        response = await crypto_pay.check_invoice(data['invoice_id'])
        
        if not response.get('ok') or not response['result']['items']:
            await callback.answer("❌ Ошибка проверки платежа", show_alert=True)
            return
            
        invoice = response['result']['items'][0]
        
        if invoice['status'] == 'paid':
            # Зачисляем средства
            db.update_balance(user_id, data['amount'])
            new_balance = db.get_balance(user_id)
            
            # Реферальный бонус
            bonus_text = ""
            referrer_id = db.get_referrer(user_id)
            if referrer_id and db.can_get_referral_bonus(referrer_id, user_id, data['invoice_id']):
                ref_count = db.get_referrals_count(referrer_id)
                bonus_percent = referral_system.calculate_bonus(None)
                bonus = round(data['amount'] * bonus_percent, 2)
                
                db.add_referral_bonus(
                    referrer_id=referrer_id,
                    referral_id=user_id,
                    amount=data['amount'],
                    bonus=bonus,
                    invoice_id=data['invoice_id']
                )
                db.update_balance(referrer_id, bonus)

                
                # Уведомляем реферера
                try:
                    await callback.bot.send_message(
                        referrer_id,
                        f"🎉 Ваш реферал пополнил баланс!\n"
                        f"👤 ID: {user_id}\n"
                        f"💸 Сумма: {data['amount']} RUB\n"
                        f"💰 Ваш бонус: {bonus} RUB\n"
                        f"💳 Новый баланс: {db.get_balance(referrer_id)} RUB"
                    )
                except:
                    pass
            
            await callback.message.edit_text(
                f"✅ Оплата подтверждена!\n"
                f"💳 Ваш баланс пополнен на {data['amount']} RUB\n"
                f"💰 Новый баланс: {new_balance} RUB"
                f"{bonus_text}",
                reply_markup=None
            )
            await state.clear()
            return
                
        # Если оплата не подтверждена
        await callback.answer(
            "❌ Оплата не обнаружена. Если вы оплатили, подождите 2-3 минуты",
            show_alert=True
        )
                
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

@router.message(PaymentStates.waiting_payment_confirmation)
async def handle_other_messages(message: Message):
    # Если пользователь прислал что-то кроме команд отмены
    if message.text != "❌ Отмена":
        await message.answer("Пожалуйста, используйте кнопки под сообщением счёта:\n"
                             "- Нажмите '💳 Оплатить' для оплаты\n"
                             "- '✅ Подтвердить оплату' после оплаты\n"
                             "- '❌ Отменить оплату' для отмены")


# В обработчике оформления покупки (добавьте в payment_handlers.py)

@router.message(F.text == "🛒 Корзина")
async def show_cart(message: Message, state: FSMContext):
    user_id = message.from_user.id
    cart_items = db.get_cart_items(user_id)
    
    # Получаем скидку пользователя (если есть)
    user_data = await state.get_data()
    discount = user_data.get('discount', 0)
    
    # Рассчитываем сумму с учетом скидки
    total = sum(item[2] * item[3] for item in cart_items)
    discount_amount = total * discount / 100
    final_total = total - discount_amount
    
    # Формируем сообщение
    cart_text = "🛒 Ваша корзина:\n\n"
    for item in cart_items:
        cart_text += f"{item[1]} - {item[2]} RUB x {item[3]}\n"
    
    cart_text += (
        f"\n💵 Сумма: {total:.2f} RUB\n"
        f"🎁 Скидка: {discount}% ({discount_amount:.2f} RUB)\n"
        f"💳 Итого: {final_total:.2f} RUB"
    )
    
    # ... отправка сообщения ...
