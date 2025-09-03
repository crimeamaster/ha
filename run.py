#!/usr/bin/env python3
"""
Скрипт для запуска Wildberries Price Tracker Bot
"""

import os
import sys
import logging
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

def check_requirements():
    """Проверка наличия необходимых файлов и переменных"""
    required_files = ['bot.py', 'config.py', 'database.py', 'wb_parser.py', 'price_monitor.py']
    
    for file in required_files:
        if not os.path.exists(file):
            print(f"❌ Отсутствует файл: {file}")
            return False
    
    # Проверяем наличие .env файла
    if not os.path.exists('.env'):
        print("⚠️  Файл .env не найден. Создайте его на основе .env.example")
        print("   Скопируйте .env.example в .env и добавьте ваш BOT_TOKEN")
        return False
    
    # Проверяем BOT_TOKEN
    from dotenv import load_dotenv
    load_dotenv()
    
    if not os.getenv('BOT_TOKEN'):
        print("❌ BOT_TOKEN не установлен в файле .env")
        return False
    
    return True

def main():
    """Основная функция запуска"""
    print("🛍️  Wildberries Price Tracker Bot")
    print("=" * 40)
    
    # Проверяем требования
    if not check_requirements():
        print("\n❌ Не все требования выполнены. Проверьте настройки.")
        sys.exit(1)
    
    print("✅ Все требования выполнены")
    print("🚀 Запускаем бота...")
    
    try:
        from bot import WildberriesTrackerBot
        bot = WildberriesTrackerBot()
        bot.run()
    except KeyboardInterrupt:
        print("\n⏹️  Бот остановлен пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка при запуске бота: {e}")
        logging.exception("Ошибка при запуске бота")
        sys.exit(1)

if __name__ == "__main__":
    main()