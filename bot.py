import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import datetime
import os

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# File path for storing user data (can be modified in prod)
DATA_FILE = os.getenv("DATA_FILE", "data.json")  # Using environment variable
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Store token in an environment variable

# Load JSON data
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"users": [], "link": ""}

# Save JSON data
def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    chat_id = update.message.chat_id
    data = load_data()

    for record in data["users"]:
        if record["whatsapp"] == context.user_data.get("whatsapp"):
            record["chat_id"] = chat_id  # Save chat_id for future notifications
            save_data(data)

            if record["status"] == "verified":
                await update.message.reply_text(
                    f"🎉 Dear {record['name']}, your profile is already verified successfully."
                )
                return
            elif record["status"] == "rejected":
                await update.message.reply_text(
                    f"❌ Dear {record['name']}, your profile is already rejected. Please try again with a different WhatsApp number."
                )
                return

    # If user doesn't have profile, show account creation message
    await update.message.reply_text(
        f"👋 Hi {user.first_name}, please create your account.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Create Account", callback_data="create_account")]]),
    )

# Callback handler for buttons
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "create_account":
        await query.message.reply_text("✏️ Enter your name:")
        context.user_data["state"] = "name"

# Message handler for user input
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    chat_id = update.message.chat_id
    data = load_data()

    if context.user_data.get("state") == "name":
        context.user_data["name"] = user_message
        context.user_data["state"] = "whatsapp"
        await update.message.reply_text("📱 Enter your WhatsApp number:")

    elif context.user_data.get("state") == "whatsapp":
        context.user_data["whatsapp"] = user_message

        # Check for duplicate accounts
        for user in data["users"]:
            if user["whatsapp"] == user_message:
                if user["status"] == "verified":
                    await update.message.reply_text(
                        f"🎉 Dear {user['name']}, your profile is already verified successfully."
                    )
                    return
                elif user["status"] == "rejected":
                    await update.message.reply_text(
                        f"❌ Dear {user['name']}, your profile is already rejected. Please try again with a different WhatsApp number."
                    )
                    return

        # Save new user data
        data["users"].append({
            "name": context.user_data["name"],
            "whatsapp": context.user_data["whatsapp"],
            "chat_id": chat_id,
            "status": "pending",
            "remaining_days": 0,
            "last_verified": str(datetime.date.today())
        })
        save_data(data)

        await update.message.reply_text(
            "✅ Thank you for your time! Your profile will be verified soon. Once verified, we will notify you."
        )
        context.user_data.clear()

# Function to renew membership and notify users
async def renew_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    chat_id = update.message.chat_id

    for user in data["users"]:
        if user.get("chat_id") == chat_id and user["status"] == "verified":
            added_days = 30
            user["remaining_days"] += added_days
            save_data(data)

            await update.message.reply_text(
                f"🌟 Membership Renewed!\n\n"
                f"A big thank-you for your renewal! 💖\n"
                f"Your total days: 🗓️ {user['remaining_days']} days\n"
                f"Your journey with us continues—make it amazing! 🚀"
            )
            return

    await update.message.reply_text("❌ You do not have an active membership to renew. Please contact support.")

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"An error occurred: {context.error}")

# Main function to run the bot
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("renew", renew_membership))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.add_error_handler(error_handler)

    application.run_polling()

if __name__ == "__main__":
    main()
