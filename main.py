import asyncio
import sys
import os
import logging
from config import BOT_TOKEN
from pathlib import Path
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from middlewares import AdminMiddleware
from aiogram.fsm.strategy import FSMStrategy


from handlers.admin_promo_handlers import router as promo_router
from handlers.user_handlers import router as user_router
from handlers.admin_handlers import router as admin_router
from handlers.payment_handlers import router as payment_router

async def main():
    storage = MemoryStorage()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=storage, fsm_strategy=FSMStrategy.CHAT)
    
    admin_router.message.middleware(AdminMiddleware())
    admin_router.callback_query.middleware(AdminMiddleware())
    promo_router.message.middleware(AdminMiddleware())
    promo_router.callback_query.middleware(AdminMiddleware())
    # Подключаем роутеры напрямую
    dp.include_router(user_router)
    dp.include_router(admin_router)
    dp.include_router(payment_router)
    dp.include_router(promo_router) 
    
    await bot.delete_webhook(drop_pending_updates=True)
    print("Бот запущен! Нажмите Ctrl+C для остановки")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())