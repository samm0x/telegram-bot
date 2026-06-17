# Telegram Shop Bot

A complete Telegram shop bot built with Python.

## Features

- Product catalog
- Shopping cart
- Order management
- Admin panel
- Payment receipt verification
- Sales statistics
- Product search

## Admin Commands

- /orders - View pending orders
- /stats - View sales statistics
- /add_product name price - Add new product
- /remove_product id - Deactivate product
- /list_products - List all products

## User Commands

- /start - Start the bot
- /search product_name - Search products

## Setup

1. Install dependencies:
pip install -r requirements.txt

2. Configure .env:
BOT_TOKEN=your_token
ADMIN_ID=your_telegram_id

3. Run:
python bot.py