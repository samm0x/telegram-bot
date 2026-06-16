from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import os
from dotenv import load_dotenv
from database import Order , SessionLocal , OrderItem
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

products = [
    {"id": 1, "name": "قهوه اسپرسو", "price": 45000},
    {"id": 2, "name": "کاپوچینو", "price": 55000},
    {"id": 3, "name": "لته", "price": 60000},
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("مشاهده محصولات", callback_data="show_products")],
        [InlineKeyboardButton("سبد خرید", callback_data="show_cart")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("به فروشگاه خوش اومدی!", reply_markup=reply_markup)

async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = []
    for p in products:
        keyboard.append([InlineKeyboardButton(
            f"{p['name']} - {p['price']:,} تومان",
            callback_data=f"add_{p['id']}"
        )])
    keyboard.append([InlineKeyboardButton("سبد خرید", callback_data="show_cart")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("محصولات:", reply_markup=reply_markup)

async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.split("_")[1])
    product = next(p for p in products if p["id"] == product_id)

    if "cart" not in context.user_data:
        context.user_data["cart"] = []

    context.user_data["cart"].append(product)
    await query.answer(f"{product['name']} به سبد اضافه شد!", show_alert=True)

async def show_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cart = context.user_data.get("cart", [])

    if not cart:
        await query.edit_message_text("سبد خریدت خالیه!")
        return

    total = sum(p["price"] for p in cart)
    text = "سبد خرید:\n\n"
    for p in cart:
        text += f"- {p['name']}: {p['price']:,} تومان\n"
    text += f"\nجمع کل: {total:,} تومان"

    keyboard = [
        [InlineKeyboardButton("پرداخت", callback_data="checkout")],
        [InlineKeyboardButton("ادامه خرید", callback_data="show_products")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cart = context.user_data.get("cart", [])
    if not cart:
        await query.edit_message_text("سبد خریدت خالیه!")
        return

    total = sum(p["price"] for p in cart)

    db = SessionLocal()
    order = Order(
        user_id=query.from_user.id,
        username=query.from_user.username,
        total=total
    )
    db.add(order)
    db.flush()

    for p in cart:
        item = OrderItem(order_id=order.id, product_name=p["name"], price=p["price"])
        db.add(item)

    db.commit()
    db.close()

    context.user_data["cart"] = []

    await query.edit_message_text(
        f"سفارش شماره {order.id} ثبت شد!\n\n"
        f"مبلغ {total:,} تومان رو به شماره کارت زیر واریز کن:\n\n"
        f"6037-XXXX-XXXX-XXXX\n\n"
        f"بعد از واریز، رسید رو بفرست."
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(show_products, pattern="show_products"))
    app.add_handler(CallbackQueryHandler(add_to_cart, pattern="add_"))
    app.add_handler(CallbackQueryHandler(show_cart, pattern="show_cart"))
    app.add_handler(CallbackQueryHandler(checkout, pattern="checkout"))
    print("ربات شروع به کار کرد!")
    app.run_polling()

if __name__ == "__main__":
    main()