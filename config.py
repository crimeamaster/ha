import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Database
DATABASE_PATH = 'wb_tracker.db'

# Wildberries API
WB_API_BASE = 'https://card.wb.ru/cards/detail'
WB_SEARCH_BASE = 'https://search.wb.ru/exactmatch/ru/common/v4/search'

# Polling interval (in minutes)
POLLING_INTERVAL = 30

# Price change threshold (percentage)
PRICE_CHANGE_THRESHOLD = 5