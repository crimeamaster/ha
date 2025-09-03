import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode
import re

from config import BOT_TOKEN, DATABASE_PATH
from database import Database
from wb_parser import WildberriesParser
from price_monitor import PriceMonitor

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class WildberriesTrackerBot:
    def __init__(self):
        self.db = Database(DATABASE_PATH)
        self.parser = WildberriesParser()
        self.monitor = PriceMonitor(self.db, self.parser)
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        
        # Добавляем пользователя в базу данных
        self.db.add_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        welcome_text = f"""
🛍️ <b>Добро пожаловать в Wildberries Price Tracker!</b>

Привет, {user.first_name}! 👋

Я помогу тебе отслеживать цены товаров на Wildberries и уведомлять о изменениях.

<b>Доступные команды:</b>
/start - Начать работу с ботом
/add - Добавить товар для отслеживания
/list - Показать список отслеживаемых товаров
/remove - Удалить товар из отслеживания
/help - Показать справку

<b>Как добавить товар:</b>
1. Скопируй ссылку на товар с Wildberries
2. Отправь её мне командой /add
3. Или отправь ссылку напрямую

<b>Пример:</b>
<code>/add https://www.wildberries.ru/catalog/12345678/detail.aspx</code>

Начни отслеживать свои любимые товары! 🎯
        """
        
        await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
📖 <b>Справка по использованию бота</b>

<b>Основные команды:</b>
• /start - Начать работу с ботом
• /add [ссылка] - Добавить товар для отслеживания
• /list - Показать список отслеживаемых товаров
• /remove [номер] - Удалить товар из отслеживания
• /help - Показать эту справку

<b>Как добавить товар:</b>
1. Найди товар на Wildberries
2. Скопируй ссылку на товар
3. Отправь команду /add с ссылкой или просто отправь ссылку

<b>Примеры:</b>
<code>/add https://www.wildberries.ru/catalog/12345678/detail.aspx</code>
<code>https://www.wildberries.ru/catalog/87654321/detail.aspx</code>

<b>Уведомления:</b>
• О изменении цены более чем на 5%
• О достижении целевой цены (если установлена)

<b>Поддерживаемые форматы ссылок:</b>
• https://www.wildberries.ru/catalog/12345678/detail.aspx
• https://wildberries.ru/catalog/12345678/detail.aspx
• Любые ссылки с ID товара

Если у тебя есть вопросы, просто напиши мне! 😊
        """
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

    async def add_product(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавление товара для отслеживания"""
        user_id = update.effective_user.id
        
        # Получаем ссылку из команды или сообщения
        if context.args:
            url = ' '.join(context.args)
        else:
            # Если команда без аргументов, просим отправить ссылку
            await update.message.reply_text(
                "📎 Отправь мне ссылку на товар с Wildberries или используй команду:\n"
                "<code>/add https://www.wildberries.ru/catalog/12345678/detail.aspx</code>",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Извлекаем ID товара из ссылки
        product_id = self.parser.extract_product_id_from_url(url)
        if not product_id:
            await update.message.reply_text(
                "❌ Не удалось извлечь ID товара из ссылки.\n"
                "Убедись, что ссылка ведет на товар с Wildberries."
            )
            return
        
        # Проверяем, не отслеживается ли уже этот товар
        tracked_products = self.db.get_user_tracked_products(user_id)
        for product in tracked_products:
            if product['product_id'] == product_id:
                await update.message.reply_text(
                    "⚠️ Этот товар уже отслеживается!"
                )
                return
        
        # Получаем информацию о товаре
        await update.message.reply_text("🔍 Получаю информацию о товаре...")
        
        product_info = self.parser.get_product_info(product_id)
        if not product_info:
            await update.message.reply_text(
                "❌ Не удалось получить информацию о товаре.\n"
                "Проверь правильность ссылки и попробуй еще раз."
            )
            return
        
        # Добавляем товар в базу данных
        success = self.db.add_tracked_product(
            user_id=user_id,
            product_id=product_id,
            product_name=product_info['name'],
            current_price=product_info['price']
        )
        
        if success:
            # Создаем клавиатуру для установки целевой цены
            keyboard = [
                [InlineKeyboardButton("🎯 Установить целевую цену", callback_data=f"set_target_{product_id}")],
                [InlineKeyboardButton("✅ Готово", callback_data="done")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message_text = f"""
✅ <b>Товар добавлен для отслеживания!</b>

📦 <b>Название:</b> {product_info['name']}
🏷️ <b>Бренд:</b> {product_info['brand']}
💰 <b>Текущая цена:</b> {product_info['price']:,} ₽
⭐ <b>Рейтинг:</b> {product_info['rating']}
💬 <b>Отзывы:</b> {product_info['feedbacks']}

🔗 <a href="{product_info['url']}">Открыть товар</a>

Теперь ты будешь получать уведомления об изменении цены!
            """
            
            await update.message.reply_text(
                message_text, 
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
        else:
            await update.message.reply_text("❌ Ошибка при добавлении товара.")

    async def list_products(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список отслеживаемых товаров"""
        user_id = update.effective_user.id
        products = self.db.get_user_tracked_products(user_id)
        
        if not products:
            await update.message.reply_text(
                "📝 У тебя пока нет отслеживаемых товаров.\n"
                "Используй команду /add для добавления товара."
            )
            return
        
        message_text = "📋 <b>Твои отслеживаемые товары:</b>\n\n"
        
        for i, product in enumerate(products, 1):
            target_price_text = ""
            if product['target_price']:
                target_price_text = f"\n🎯 Целевая цена: {product['target_price']:,} ₽"
            
            message_text += f"""
<b>{i}.</b> {product['product_name'][:50]}{'...' if len(product['product_name']) > 50 else ''}
💰 Цена: {product['current_price']:,} ₽{target_price_text}
🆔 ID: <code>{product['product_id']}</code>
📅 Добавлен: {product['created_at'][:10]}

"""
        
        # Создаем клавиатуру для удаления товаров
        keyboard = []
        for i, product in enumerate(products, 1):
            keyboard.append([InlineKeyboardButton(
                f"🗑️ Удалить {i}", 
                callback_data=f"remove_{product['product_id']}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        
        await update.message.reply_text(
            message_text, 
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )

    async def remove_product(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Удаление товара из отслеживания"""
        user_id = update.effective_user.id
        
        if not context.args:
            await update.message.reply_text(
                "❌ Укажи номер товара для удаления.\n"
                "Используй команду /list чтобы увидеть номера товаров."
            )
            return
        
        try:
            product_number = int(context.args[0])
            products = self.db.get_user_tracked_products(user_id)
            
            if 1 <= product_number <= len(products):
                product = products[product_number - 1]
                success = self.db.remove_tracked_product(user_id, product['product_id'])
                
                if success:
                    await update.message.reply_text(
                        f"✅ Товар '{product['product_name'][:50]}...' удален из отслеживания."
                    )
                else:
                    await update.message.reply_text("❌ Ошибка при удалении товара.")
            else:
                await update.message.reply_text(
                    f"❌ Неверный номер товара. Доступны номера от 1 до {len(products)}."
                )
        except ValueError:
            await update.message.reply_text("❌ Номер товара должен быть числом.")

    async def handle_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка URL сообщений"""
        url = update.message.text
        
        # Проверяем, является ли сообщение ссылкой на Wildberries
        if 'wildberries.ru' in url and 'catalog' in url:
            # Добавляем товар
            context.args = [url]
            await self.add_product(update, context)
        else:
            await update.message.reply_text(
                "❌ Это не похоже на ссылку на товар с Wildberries.\n"
                "Отправь правильную ссылку или используй команду /add."
            )

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий на кнопки"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("set_target_"):
            product_id = data.split("_")[2]
            # Здесь можно добавить логику для установки целевой цены
            await query.edit_message_text(
                "🎯 Функция установки целевой цены будет добавлена в следующей версии!"
            )
        
        elif data.startswith("remove_"):
            product_id = data.split("_")[1]
            user_id = query.from_user.id
            
            success = self.db.remove_tracked_product(user_id, product_id)
            if success:
                await query.edit_message_text("✅ Товар удален из отслеживания!")
            else:
                await query.edit_message_text("❌ Ошибка при удалении товара.")
        
        elif data == "done":
            await query.edit_message_text("✅ Готово! Товар добавлен для отслеживания.")

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        logger.error(f"Ошибка при обработке обновления: {context.error}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Произошла ошибка. Попробуй еще раз или обратись к администратору."
            )

    def run(self):
        """Запуск бота"""
        # Создаем приложение
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Добавляем обработчики
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("add", self.add_product))
        application.add_handler(CommandHandler("list", self.list_products))
        application.add_handler(CommandHandler("remove", self.remove_product))
        application.add_handler(CallbackQueryHandler(self.button_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_url))
        
        # Добавляем обработчик ошибок
        application.add_error_handler(self.error_handler)
        
        # Запускаем мониторинг цен
        asyncio.create_task(self.monitor.start_monitoring())
        
        logger.info("Бот запущен!")
        
        # Запускаем бота
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    bot = WildberriesTrackerBot()
    bot.run()