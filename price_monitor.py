import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict
from telegram import Bot
from telegram.error import TelegramError

from config import BOT_TOKEN, POLLING_INTERVAL, PRICE_CHANGE_THRESHOLD
from database import Database
from wb_parser import WildberriesParser

logger = logging.getLogger(__name__)

class PriceMonitor:
    def __init__(self, db: Database, parser: WildberriesParser):
        self.db = db
        self.parser = parser
        self.bot = Bot(token=BOT_TOKEN)
        self.is_running = False

    async def start_monitoring(self):
        """Запуск мониторинга цен"""
        self.is_running = True
        logger.info("Мониторинг цен запущен")
        
        while self.is_running:
            try:
                await self.check_prices()
                await asyncio.sleep(POLLING_INTERVAL * 60)  # Конвертируем минуты в секунды
            except Exception as e:
                logger.error(f"Ошибка в мониторинге цен: {e}")
                await asyncio.sleep(60)  # Ждем минуту перед повтором

    def stop_monitoring(self):
        """Остановка мониторинга цен"""
        self.is_running = False
        logger.info("Мониторинг цен остановлен")

    async def check_prices(self):
        """Проверка цен всех отслеживаемых товаров"""
        try:
            tracked_products = self.db.get_all_tracked_products()
            
            if not tracked_products:
                logger.info("Нет товаров для отслеживания")
                return
            
            logger.info(f"Проверяем цены для {len(tracked_products)} товаров")
            
            for product in tracked_products:
                try:
                    await self.check_single_product(product)
                    # Небольшая задержка между запросами
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"Ошибка при проверке товара {product['product_id']}: {e}")
                    
        except Exception as e:
            logger.error(f"Ошибка при проверке цен: {e}")

    async def check_single_product(self, product: Dict):
        """Проверка цены одного товара"""
        product_id = product['product_id']
        old_price = product['current_price']
        
        # Получаем актуальную информацию о товаре
        product_info = self.parser.get_product_info(product_id)
        
        if not product_info:
            logger.warning(f"Не удалось получить информацию о товаре {product_id}")
            return
        
        new_price = product_info['price']
        
        # Если цена изменилась
        if new_price != old_price:
            logger.info(f"Цена товара {product_id} изменилась: {old_price} -> {new_price}")
            
            # Обновляем цену в базе данных
            self.db.update_product_price(product_id, new_price)
            
            # Получаем пользователей для уведомления
            notifications = self.db.get_price_change_notifications(
                product_id, old_price, new_price
            )
            
            # Отправляем уведомления
            for notification in notifications:
                await self.send_price_notification(notification, product_info)
                
                # Записываем отправленное уведомление
                self.db.record_notification(
                    user_id=notification['user_id'],
                    product_id=product_id,
                    old_price=old_price,
                    new_price=new_price,
                    change_percent=notification['change_percent']
                )

    async def send_price_notification(self, notification: Dict, product_info: Dict):
        """Отправка уведомления об изменении цены"""
        try:
            user_id = notification['user_id']
            old_price = notification['old_price']
            new_price = notification['new_price']
            change_percent = notification['change_percent']
            target_price = notification.get('target_price')
            
            # Определяем тип изменения
            if new_price < old_price:
                change_emoji = "📉"
                change_text = "снизилась"
                change_color = "🟢"
            else:
                change_emoji = "📈"
                change_text = "выросла"
                change_color = "🔴"
            
            # Формируем сообщение
            message_text = f"""
{change_emoji} <b>Изменение цены!</b>

📦 <b>Товар:</b> {product_info['name'][:100]}{'...' if len(product_info['name']) > 100 else ''}
🏷️ <b>Бренд:</b> {product_info['brand']}

💰 <b>Цена {change_text}:</b>
{change_color} Было: {old_price:,} ₽
{change_color} Стало: {new_price:,} ₽

📊 <b>Изменение:</b> {change_percent:+.1f}%
            """
            
            # Добавляем информацию о целевой цене, если она достигнута
            if target_price and new_price <= target_price:
                message_text += f"\n\n🎯 <b>Целевая цена достигнута!</b>\nЦелевая цена: {target_price:,} ₽"
            
            message_text += f"\n\n🔗 <a href=\"{product_info['url']}\">Открыть товар</a>"
            
            # Отправляем сообщение
            await self.bot.send_message(
                chat_id=user_id,
                text=message_text,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            
            logger.info(f"Уведомление отправлено пользователю {user_id} о товаре {product_info['id']}")
            
        except TelegramError as e:
            logger.error(f"Ошибка при отправке уведомления пользователю {notification['user_id']}: {e}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при отправке уведомления: {e}")

    async def send_daily_summary(self):
        """Отправка ежедневной сводки (опционально)"""
        try:
            # Здесь можно добавить логику для ежедневной сводки
            # Например, статистику по отслеживаемым товарам
            pass
        except Exception as e:
            logger.error(f"Ошибка при отправке ежедневной сводки: {e}")

    async def cleanup_old_data(self):
        """Очистка старых данных (опционально)"""
        try:
            # Здесь можно добавить логику для очистки старых записей
            # Например, удаление истории цен старше 30 дней
            pass
        except Exception as e:
            logger.error(f"Ошибка при очистке старых данных: {e}")