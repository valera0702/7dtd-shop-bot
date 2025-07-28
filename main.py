import asyncio
import sys
import os
from config import BOT_TOKEN
from pathlib import Path
from aiogram import Bot, Dispatcher

from aiogram.fsm.storage.memory import MemoryStorage





from handlers.user_handlers import router as user_router
from handlers.admin_handlers import router as admin_router
from handlers.payment_handlers import router as payment_router

async def main():
    storage = MemoryStorage()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=storage)
    
    # Подключаем роутеры напрямую
    dp.include_router(user_router)
    dp.include_router(admin_router)
    dp.include_router(payment_router)
    
    await bot.delete_webhook(drop_pending_updates=True)
    print("Бот запущен! Нажмите Ctrl+C для остановки")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nБот остановлен")
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()