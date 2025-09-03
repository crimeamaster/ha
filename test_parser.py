#!/usr/bin/env python3
"""
Скрипт для тестирования парсера Wildberries
"""

import sys
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from wb_parser import WildberriesParser

def test_parser():
    """Тестирование парсера"""
    print("🔍 Тестирование парсера Wildberries")
    print("=" * 40)
    
    parser = WildberriesParser()
    
    # Тестовые URL (замените на реальные)
    test_urls = [
        "https://www.wildberries.ru/catalog/12345678/detail.aspx",
        "https://wildberries.ru/catalog/87654321/detail.aspx"
    ]
    
    for url in test_urls:
        print(f"\n📎 Тестируем URL: {url}")
        
        # Извлекаем ID
        product_id = parser.extract_product_id_from_url(url)
        print(f"🆔 Извлеченный ID: {product_id}")
        
        if product_id:
            # Получаем информацию о товаре
            print("🔍 Получаем информацию о товаре...")
            product_info = parser.get_product_info(product_id)
            
            if product_info:
                print("✅ Товар найден!")
                print(f"📦 Название: {product_info['name']}")
                print(f"🏷️ Бренд: {product_info['brand']}")
                print(f"💰 Цена: {product_info['price']:,} ₽")
                print(f"⭐ Рейтинг: {product_info['rating']}")
                print(f"💬 Отзывы: {product_info['feedbacks']}")
                print(f"🔗 URL: {product_info['url']}")
            else:
                print("❌ Товар не найден или ошибка при получении данных")
        else:
            print("❌ Не удалось извлечь ID из URL")
    
    # Тестируем поиск
    print(f"\n🔍 Тестируем поиск товаров...")
    search_query = "iPhone"
    products = parser.search_products(search_query, limit=3)
    
    if products:
        print(f"✅ Найдено {len(products)} товаров по запросу '{search_query}':")
        for i, product in enumerate(products, 1):
            print(f"\n{i}. {product['name'][:50]}...")
            print(f"   💰 Цена: {product['price']:,} ₽")
            print(f"   🏷️ Бренд: {product['brand']}")
    else:
        print(f"❌ Товары по запросу '{search_query}' не найдены")

if __name__ == "__main__":
    test_parser()