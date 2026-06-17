from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import os
from dotenv import load_dotenv
from database import Order , SessionLocal , OrderItem , Product
from telegram.ext import MessageHandler, filters

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

    db = SessionLocal()
    products = db.query(Product).filter(Product.is_available == True).all()
    db.close()

    if not products:
        await query.edit_message_text("محصولی موجود نیست!")
        return

    keyboard = []
    for p in products:
        keyboard.append([InlineKeyboardButton(
            f"{p.name} - {p.price:,} تومان",
            callback_data=f"add_{p.id}"
        )])
    keyboard.append([InlineKeyboardButton("سبد خرید", callback_data="show_cart")])

    await query.edit_message_text("محصولات:", reply_markup=InlineKeyboardMarkup(keyboard))

async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.split("_")[1])

    db = SessionLocal()
    product = db.query(Product).filter(Product.id == product_id).first()
    db.close()

    if not product:
        await query.answer("محصول پیدا نشد!", show_alert=True)
        return

    if "cart" not in context.user_data:
        context.user_data["cart"] = []

    context.user_data["cart"].append({
        "id": product.id,
        "name": product.name,
        "price": product.price
    })

    await query.answer(f"{product.name} به سبد اضافه شد! ✅", show_alert=True)

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
    db.refresh(order)
    order_id = int(order.id)
    db.close()


    context.user_data["cart"] = []

    await query.edit_message_text(
        f"سفارش شماره {order_id} ثبت شد!\n\n"
        f"مبلغ {total:,} تومان رو به شماره کارت زیر واریز کن:\n\n"
        f"6037-XXXX-XXXX-XXXX\n\n"
        f"بعد از واریز، رسید رو بفرست."
    )

async def receive_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("لطفاً عکس رسید رو بفرست.")
        return

    user_id = update.message.from_user.id
    username = update.message.from_user.username

    await update.message.reply_text("رسیدت دریافت شد! منتظر تایید باش. ✅")

    await context.bot.send_message(
        ADMIN_ID,
        f"رسید جدید از @{username}!\n"
        f"شناسه کاربر: {user_id}"
    )

    await context.bot.forward_message(
        chat_id=ADMIN_ID,
        from_chat_id=update.message.chat_id,
        message_id=update.message.message_id
    )

ADMIN_ID = int(os.getenv("ADMIN_ID"))

async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("دسترسی ندارید!")
        return

    db = SessionLocal()
    orders = db.query(Order).filter(Order.is_paid == False).all()
    db.close()

    if not orders:
        await update.message.reply_text("سفارش جدیدی نیست.")
        return

    for order in orders:
        keyboard = [[InlineKeyboardButton(
            "تایید پرداخت",
            callback_data=f"confirm_{order.id}"
        )]]
        await update.message.reply_text(
            f"سفارش #{order.id}\n"
            f"کاربر: @{order.username}\n"
            f"مبلغ: {order.total:,} تومان",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    order_id = int(query.data.split("_")[1])

    db = SessionLocal()
    order = db.query(Order).filter(Order.id == order_id).first()
    order.is_paid = True
    db.commit()
    user_id = order.user_id
    db.close()

    await query.edit_message_text(f"سفارش #{order_id} تایید شد! ✅")
    await context.bot.send_message(user_id, f"سفارش #{order_id} تایید شد! به زودی ارسال میشه. ✅")

async def add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("دسترسی ندارید!")
        return

    try:
        args = context.args
        name = args[0]
        price = int(args[1])

        db = SessionLocal()
        product = Product(name=name, price=price)
        db.add(product)
        db.commit()
        db.close()

        await update.message.reply_text(f"محصول {name} با قیمت {price:,} تومان اضافه شد! ✅")

    except:
        await update.message.reply_text(
            "فرمت اشتباهه!\n"
            "اینطوری بفرست:\n"
            "/add_product نام_محصول قیمت"
        )

async def remove_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("دسترسی ندارید!")
        return

    if not context.args:
        await update.message.reply_text(
            "فرمت اشتباهه!\n"
            "اینطوری بفرست:\n"
            "/remove_product شماره_محصول"
        )
        return

    product_id = int(context.args[0])

    db = SessionLocal()
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        await update.message.reply_text("محصول پیدا نشد!")
        db.close()
        return

    product.is_available = False
    db.commit()
    product_name = product.name
    db.close()

    await update.message.reply_text(f"محصول {product_name} غیرفعال شد! ✅")


async def list_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("دسترسی ندارید!")
        return

    db = SessionLocal()
    products = db.query(Product).all()
    db.close()

    if not products:
        await update.message.reply_text("محصولی نیست!")
        return

    text = "لیست محصولات:\n\n"
    for p in products:
        status = "✅" if p.is_available else "❌"
        text += f"{status} #{p.id} - {p.name} - {p.price:,} تومان\n"

    await update.message.reply_text(text)

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("اینطوری بفرست:\n/search نام_محصول")
        return

    query_text = " ".join(context.args)

    db = SessionLocal()
    products = db.query(Product).filter(
        Product.name.contains(query_text),
        Product.is_available == True
    ).all()
    db.close()

    if not products:
        await update.message.reply_text("محصولی پیدا نشد!")
        return

    keyboard = []
    for p in products:
        keyboard.append([InlineKeyboardButton(
            f"{p.name} - {p.price:,} تومان",
            callback_data=f"add_{p.id}"
        )])

    await update.message.reply_text(
        f"نتایج جستجو برای '{query_text}':",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("دسترسی ندارید!")
        return

    db = SessionLocal()

    total_orders = db.query(Order).count()
    paid_orders = db.query(Order).filter(Order.is_paid == True).count()
    unpaid_orders = db.query(Order).filter(Order.is_paid == False).count()

    total_revenue = db.query(Order).filter(Order.is_paid == True).all()
    revenue = sum(o.total for o in total_revenue)

    total_products = db.query(Product).filter(Product.is_available == True).count()

    db.close()

    await update.message.reply_text(
        f"📊 آمار فروشگاه:\n\n"
        f"کل سفارشات: {total_orders}\n"
        f"پرداخت شده: {paid_orders}\n"
        f"در انتظار پرداخت: {unpaid_orders}\n"
        f"درآمد کل: {revenue:,} تومان\n"
        f"محصولات فعال: {total_products}"
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(show_products, pattern="show_products"))
    app.add_handler(CallbackQueryHandler(add_to_cart, pattern="add_"))
    app.add_handler(CallbackQueryHandler(show_cart, pattern="show_cart"))
    app.add_handler(CallbackQueryHandler(checkout, pattern="checkout"))
    app.add_handler(CommandHandler("orders", admin_orders))
    app.add_handler(CallbackQueryHandler(confirm_payment, pattern="confirm_"))
    app.add_handler(MessageHandler(filters.PHOTO, receive_receipt))
    app.add_handler(CommandHandler("add_product", add_product))
    app.add_handler(CommandHandler("remove_product", remove_product))
    app.add_handler(CommandHandler("list_products", list_products))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("search", search))
    print("ربات شروع به کار کرد!")
    app.run_polling()

if __name__ == "__main__":
    main()


