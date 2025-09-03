import requests
import json
import time
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)

class WildberriesParser:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })

    def get_product_info(self, product_id: str) -> Optional[Dict]:
        """
        Получает информацию о товаре по его ID
        """
        try:
            # Парсим ID из URL или используем напрямую
            if '/' in product_id:
                product_id = product_id.split('/')[-1].split('?')[0]
            
            # Убираем все нецифровые символы
            product_id = ''.join(filter(str.isdigit, product_id))
            
            if not product_id:
                return None
            
            url = f"https://card.wb.ru/cards/detail?appType=1&curr=rub&dest=-1257786&regions=80,64,83,4,38,115,30,40,86,75,69,1,31,66,110,48,22,114,111&spp=30&nm={product_id}"
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get('data', {}).get('products'):
                return None
            
            product = data['data']['products'][0]
            
            return {
                'id': product.get('id'),
                'name': product.get('name', 'Неизвестный товар'),
                'price': product.get('priceU', 0) // 100,  # Цена в копейках, переводим в рубли
                'old_price': product.get('priceU', 0) // 100,
                'rating': product.get('reviewRating', 0),
                'feedbacks': product.get('feedbacks', 0),
                'brand': product.get('brand', 'Неизвестный бренд'),
                'url': f"https://www.wildberries.ru/catalog/{product.get('id')}/detail.aspx"
            }
            
        except Exception as e:
            logger.error(f"Ошибка при получении информации о товаре {product_id}: {e}")
            return None

    def search_products(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Поиск товаров по запросу
        """
        try:
            url = f"https://search.wb.ru/exactmatch/ru/common/v4/search"
            params = {
                'appType': 1,
                'curr': 'rub',
                'dest': '-1257786',
                'query': query,
                'resultset': 'catalog',
                'sort': 'popular',
                'spp': 30,
                'suppressSpellcheck': 'false'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get('data', {}).get('products'):
                return []
            
            products = []
            for product in data['data']['products'][:limit]:
                products.append({
                    'id': product.get('id'),
                    'name': product.get('name', 'Неизвестный товар'),
                    'price': product.get('priceU', 0) // 100,
                    'rating': product.get('reviewRating', 0),
                    'feedbacks': product.get('feedbacks', 0),
                    'brand': product.get('brand', 'Неизвестный бренд'),
                    'url': f"https://www.wildberries.ru/catalog/{product.get('id')}/detail.aspx"
                })
            
            return products
            
        except Exception as e:
            logger.error(f"Ошибка при поиске товаров: {e}")
            return []

    def extract_product_id_from_url(self, url: str) -> Optional[str]:
        """
        Извлекает ID товара из URL Wildberries
        """
        try:
            # Различные форматы URL Wildberries
            if 'catalog/' in url:
                parts = url.split('catalog/')[1].split('/')
                if parts:
                    return parts[0]
            elif 'detail.aspx' in url:
                # Извлекаем из параметров
                if 'nm=' in url:
                    import re
                    match = re.search(r'nm=(\d+)', url)
                    if match:
                        return match.group(1)
            
            return None
        except Exception as e:
            logger.error(f"Ошибка при извлечении ID из URL {url}: {e}")
            return None