

from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

# Получаем список админов из нашего главного файла
from config import ADMIN_IDS

class AdminMiddleware(BaseMiddleware):
    """
    Проверяет, является ли пользователь администратором.
    Применяется только к роутеру администратора.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем объект пользователя, который вызвал событие
        user: User = data.get('event_from_user')
        
        # Если пользователя нет или его ID нет в списке админов,
        # просто прекращаем обработку события.
        if not user or user.id not in ADMIN_IDS:
            return
            
        # Если пользователь админ - продолжаем и вызываем нужный хендлер
        return await handler(event, data)