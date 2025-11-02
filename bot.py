import os
import telebot
import json
import pandas as pd
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
import numpy as np
import re

# Load environment variables - Railway will provide BOT_TOKEN
API_TOKEN = os.getenv('8424614083:AAGCufPKRFnQc9TPE7YFejlLIDRqL1tWm10')

if not API_TOKEN:
    print("❌ BOT_TOKEN not found!")
    print("💡 Set BOT_TOKEN in Railway dashboard Variables")
    exit(1)

bot = telebot.TeleBot(API_TOKEN)

# Your data storage functions
def load_data():
    data_file = 'allowance_data.json'
    if os.path.exists(data_file):
        with open(data_file, 'r') as f:
            return json.load(f)
    return {}

def save_data(data):
    data_file = 'allowance_data.json'
    with open(data_file, 'w') as f:
        json.dump(data, f, indent=2)

# Your existing bot handlers and functions
# ... [PASTE ALL YOUR EXISTING CODE HERE] ...

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "🤖 Smart Allowance Bot is running on Railway!")

# Add more of your command handlers...

if __name__ == "__main__":
    print("🚀 Bot starting on Railway...")
    bot.polling(none_stop=True)
