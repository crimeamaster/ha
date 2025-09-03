import sqlite3
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Инициализация базы данных"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Таблица пользователей
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Таблица отслеживаемых товаров
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tracked_products (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        product_id TEXT,
                        product_name TEXT,
                        current_price INTEGER,
                        target_price INTEGER,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Таблица истории цен
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS price_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        product_id TEXT,
                        price INTEGER,
                        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Таблица уведомлений
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS notifications (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        product_id TEXT,
                        old_price INTEGER,
                        new_price INTEGER,
                        change_percent REAL,
                        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                conn.commit()
                logger.info("База данных инициализирована успешно")
                
        except Exception as e:
            logger.error(f"Ошибка при инициализации базы данных: {e}")

    def add_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Добавление пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, username, first_name, last_name))
                conn.commit()
        except Exception as e:
            logger.error(f"Ошибка при добавлении пользователя: {e}")

    def add_tracked_product(self, user_id: int, product_id: str, product_name: str, 
                          current_price: int, target_price: int = None) -> bool:
        """Добавление товара для отслеживания"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Проверяем, не отслеживается ли уже этот товар
                cursor.execute('''
                    SELECT id FROM tracked_products 
                    WHERE user_id = ? AND product_id = ? AND is_active = 1
                ''', (user_id, product_id))
                
                if cursor.fetchone():
                    return False
                
                cursor.execute('''
                    INSERT INTO tracked_products 
                    (user_id, product_id, product_name, current_price, target_price)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, product_id, product_name, current_price, target_price))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Ошибка при добавлении товара для отслеживания: {e}")
            return False

    def get_user_tracked_products(self, user_id: int) -> List[Dict]:
        """Получение списка отслеживаемых товаров пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, product_id, product_name, current_price, target_price, created_at
                    FROM tracked_products 
                    WHERE user_id = ? AND is_active = 1
                    ORDER BY created_at DESC
                ''', (user_id,))
                
                products = []
                for row in cursor.fetchall():
                    products.append({
                        'id': row[0],
                        'product_id': row[1],
                        'product_name': row[2],
                        'current_price': row[3],
                        'target_price': row[4],
                        'created_at': row[5]
                    })
                
                return products
                
        except Exception as e:
            logger.error(f"Ошибка при получении отслеживаемых товаров: {e}")
            return []

    def update_product_price(self, product_id: str, new_price: int) -> bool:
        """Обновление цены товара"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Обновляем цену в таблице отслеживаемых товаров
                cursor.execute('''
                    UPDATE tracked_products 
                    SET current_price = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE product_id = ? AND is_active = 1
                ''', (new_price, product_id))
                
                # Добавляем запись в историю цен
                cursor.execute('''
                    INSERT INTO price_history (product_id, price)
                    VALUES (?, ?)
                ''', (product_id, new_price))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Ошибка при обновлении цены товара: {e}")
            return False

    def get_price_change_notifications(self, product_id: str, old_price: int, new_price: int) -> List[Dict]:
        """Получение пользователей для уведомления об изменении цены"""
        try:
            change_percent = ((new_price - old_price) / old_price) * 100
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT DISTINCT user_id, target_price
                    FROM tracked_products 
                    WHERE product_id = ? AND is_active = 1
                ''', (product_id,))
                
                notifications = []
                for row in cursor.fetchall():
                    user_id, target_price = row
                    
                    # Уведомляем если:
                    # 1. Цена изменилась более чем на 5%
                    # 2. Цена достигла целевой цены
                    should_notify = (
                        abs(change_percent) >= 5 or 
                        (target_price and new_price <= target_price)
                    )
                    
                    if should_notify:
                        notifications.append({
                            'user_id': user_id,
                            'old_price': old_price,
                            'new_price': new_price,
                            'change_percent': change_percent,
                            'target_price': target_price
                        })
                
                return notifications
                
        except Exception as e:
            logger.error(f"Ошибка при получении уведомлений: {e}")
            return []

    def record_notification(self, user_id: int, product_id: str, old_price: int, 
                          new_price: int, change_percent: float):
        """Запись отправленного уведомления"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO notifications 
                    (user_id, product_id, old_price, new_price, change_percent)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, product_id, old_price, new_price, change_percent))
                conn.commit()
        except Exception as e:
            logger.error(f"Ошибка при записи уведомления: {e}")

    def remove_tracked_product(self, user_id: int, product_id: str) -> bool:
        """Удаление товара из отслеживания"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE tracked_products 
                    SET is_active = 0 
                    WHERE user_id = ? AND product_id = ?
                ''', (user_id, product_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Ошибка при удалении товара из отслеживания: {e}")
            return False

    def get_all_tracked_products(self) -> List[Dict]:
        """Получение всех активных отслеживаемых товаров"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT DISTINCT product_id, product_name, current_price
                    FROM tracked_products 
                    WHERE is_active = 1
                ''')
                
                products = []
                for row in cursor.fetchall():
                    products.append({
                        'product_id': row[0],
                        'product_name': row[1],
                        'current_price': row[2]
                    })
                
                return products
                
        except Exception as e:
            logger.error(f"Ошибка при получении всех отслеживаемых товаров: {e}")
            return []