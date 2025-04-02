import sqlite3
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler
from datetime import datetime
import asyncio

ASK_CITY, ASK_FIRST_NAME, ASK_LAST_NAME, ASK_EMAIL, ASK_AGE = range(5)

conn = sqlite3.connect("users.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, city TEXT, access_granted INTEGER)")
conn.commit()

access_granted_users = set()  # کاربرانی که دسترسی دارند

async def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id in access_granted_users:
        await update.message.reply_text("🔒 شما دسترسی به بات را تنها یکبار داشتید. دسترسی به بات به پایان رسید.")
        return
    if update.message.chat.type != "private":
        return
    await update.message.reply_text("🏙 لطفاً نام شهر خود را وارد کنید:")
    return ASK_CITY

async def ask_city(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    city = update.message.text.strip()

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO users (user_id, city) VALUES (?, ?)", (user_id, city))
    conn.commit()

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {city} (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            email TEXT,
            age INTEGER,
            join_date TEXT
        )
    """)
    conn.commit()
    conn.close()

    context.user_data["city"] = city
    await update.message.reply_text("👤 نام کوچک خود را وارد کنید:")
    return ASK_FIRST_NAME

async def ask_first_name(update: Update, context: CallbackContext):
    context.user_data["first_name"] = update.message.text.strip()
    await update.message.reply_text("👥 نام خانوادگی خود را وارد کنید:")
    return ASK_LAST_NAME

async def ask_last_name(update: Update, context: CallbackContext):
    context.user_data["last_name"] = update.message.text.strip()
    await update.message.reply_text("📧 ایمیل خود را وارد کنید:")
    return ASK_EMAIL

async def ask_email(update: Update, context: CallbackContext):
    context.user_data["email"] = update.message.text.strip()
    await update.message.reply_text("🔢 سن خود را وارد کنید:")
    return ASK_AGE

async def ask_age(update: Update, context: CallbackContext):
    try:
        age = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید.")
        return ASK_AGE

    context.user_data["age"] = age
    user_id = update.message.from_user.id
    city = context.user_data["city"]
    first_name = context.user_data["first_name"]
    last_name = context.user_data["last_name"]
    email = context.user_data["email"]
    join_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute(
        f"INSERT INTO {city} (user_id, first_name, last_name, email, age, join_date) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, first_name, last_name, email, age, join_date))
    conn.commit()
    conn.close()

    # ارسال لینک به کاربر
    link_message = await update.message.reply_text("✅ ثبت‌نام شما با موفقیت انجام شد!\n\n" +
                                                   "برای دسترسی به گروه، از این لینک استفاده کنید: \n" +
                                                   "https://t.me/+IGQM933rzHowMjlk")

    access_granted_users.add(user_id)

    # بعد از 10 ثانیه لینک حذف می‌شود
    await asyncio.sleep(10)
    await link_message.delete()

    # پیام عدم دسترسی پس از حذف لینک
    await update.message.reply_text("🔒 شما دسترسی به بات را تنها یکبار داشتید. دسترسی به بات به پایان رسید.")

    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text("❌ عملیات لغو شد.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def handle_repeated_message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if update.message.chat.type != "private":
        return
    if user_id in access_granted_users:
        await update.message.reply_text("🔒 شما دسترسی به بات را تنها یکبار داشتید. دسترسی به بات به پایان رسید.")
    else:
        await update.message.reply_text("🚫 دسترسی شما به بات فعلاً غیرفعال است.")

def main():
    app = Application.builder().token("7429950938:AAEdd4bjzS9WBr7FBFT43JX-1PqrWZ7W8sI").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_city)],
            ASK_FIRST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_first_name)],
            ASK_LAST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_last_name)],
            ASK_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_email)],
            ASK_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_age)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_repeated_message))

    print("🚀 ربات ثبت‌نام با محدودیت دسترسی فعال شد!")
    app.run_polling()

if __name__ == "__main__":
    main()