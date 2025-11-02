import os
import telebot
import json
import pandas as pd
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
import numpy as np
import re

# Load environment variables - Railway will provide BOT_TOKEN
API_TOKEN = os.getenv('8424614083:AAGCufPKRFnQc9TPE7YFejlLIDRqL1tWm10
')

if not API_TOKEN:
    print("❌ BOT_TOKEN not found in environment variables!")
    print("💡 Make sure you set BOT_TOKEN in Railway dashboard")
    exit(1)

bot = telebot.TeleBot(API_TOKEN)

# Data storage
DATA_FILE = 'allowance_data.json'

# Categories
SCHOOL_CATEGORIES = {
    'transport': 0.20,      # Jeep, Grab, Gas
    'lunch': 0.30,          # Canteen, Baon
    'merienda': 0.15,       # Snacks, Coffee
    'school_supplies': 0.10, # Books, Photocopy, Projects
    'load_data': 0.10,      # Internet, Mobile Load
    'savings': 0.15         # Guaranteed savings
}

LIFE_CATEGORIES = {
    'personal_care': 0.15,  # Haircut, Toiletries
    'entertainment': 0.25,  # Movies, Gala, Shopping
    'food_delivery': 0.20,  # GrabFood, FoodPanda
    'hobbies': 0.15,        # Games, Books, Sports
    'emergency': 0.15,      # Unexpected expenses
    'savings': 0.10         # Life savings
}

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def calculate_thresholds(amount, categories):
    thresholds = {}
    for category, percentage in categories.items():
        thresholds[category] = amount * percentage
    return thresholds

def get_school_emoji(category):
    emojis = {
        'transport': '🚗',
        'lunch': '🍔',
        'merienda': '🍎',
        'school_supplies': '📚',
        'load_data': '📱',
        'savings': '💰'
    }
    return emojis.get(category, '📁')

def get_life_emoji(category):
    emojis = {
        'personal_care': '💇',
        'entertainment': '🎬',
        'food_delivery': '🍕',
        'hobbies': '🎮',
        'emergency': '🚨',
        'savings': '💰'
    }
    return emojis.get(category, '📁')

def ai_analyze_patterns(user_data, user_id):
    """AI analysis of spending patterns"""
    if user_id not in user_data or len(user_data[user_id].get('school', {}).get('transactions', [])) < 3:
        return "🤖 AI: Need more data (3+ days) for pattern analysis"
    
    records = user_data[user_id]['school']['transactions']
    df = pd.DataFrame(records)
    
    # Calculate daily savings rate
    df['savings_rate'] = df['total_saved'] / df['allowance']
    
    # Find best/worst days
    best_day = df.loc[df['savings_rate'].idxmax()]
    worst_day = df.loc[df['savings_rate'].idxmin()]
    
    # Detect patterns
    avg_savings_rate = df['savings_rate'].mean()
    
    analysis = f"""
🤖 *AI PATTERN ANALYSIS*

📈 *Overall Performance:*
• Average Savings Rate: {avg_savings_rate:.1%}
• Best Day: {best_day['date']} ({best_day['savings_rate']:.1%} saved)
• Most Challenging: {worst_day['date']} ({worst_day['savings_rate']:.1%} saved)

💡 *Recommendations:*
"""
    
    if avg_savings_rate < 0.1:
        analysis += "• Focus on reducing food delivery costs\n"
        analysis += "• Try public transport instead of ride-hailing\n"
    elif avg_savings_rate > 0.2:
        analysis += "• Excellent budgeting! Consider increasing savings goal\n"
    
    return analysis

def ai_generate_notes(category, spent, threshold):
    """AI generates smart notes for each category"""
    if spent == 0:
        return "🎉 Amazing! No spending in this category!"
    
    percentage = spent / threshold if threshold > 0 else 0
    
    if percentage <= 0.5:
        return "💰 Excellent budgeting! Significant savings!"
    elif percentage <= 0.8:
        return "✅ Good control! Within safe range."
    elif percentage <= 1.0:
        return "⚠️ Close to limit! Be careful with next expenses."
    else:
        overspend = spent - threshold
        tips = {
            'transport': f"🚗 Try jeep/UV next time to save ₱{overspend + 20}",
            'lunch': f"🍱 Meal prep could save ₱{overspend + 30}",
            'merienda': f"🍎 Bring snacks to save ₱{overspend + 15}",
            'school_supplies': f"📚 Plan projects early to avoid rush costs",
            'personal_care': f"💇 Look for student discounts next time",
            'entertainment': f"🎬 Suggest budget-friendly activities",
            'food_delivery': f"🍕 Cook at home to save ₱{overspend + 25}"
        }
        return tips.get(category, f"Review {category} spending habits")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = """
💰 *Smart Allowance Tracker with AI* 💰

*Available Commands:*
/school_log - Log school allowance & expenses
/life_log - Log personal life expenses  
/school_summary - School spending summary
/life_summary - Life expenses summary
/overall_balance - Combined wallet view
/balance - Check wallet balance
/add_money - Add money to wallet
/insights - AI spending analysis

*Examples:*
`/school_log` - Start tracking school allowance
`/life_log` - Track personal expenses
"""
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

@bot.message_handler(commands=['school_log'])
def start_school_logging(message):
    user_id = str(message.from_user.id)
    data = load_data()
    
    if user_id not in data:
        data[user_id] = {'school': {'transactions': []}, 'life': {'transactions': []}, 'wallet': {'current_balance': 0, 'total_savings': 0, 'transactions': []}}
    
    # Check if already logged today
    today = datetime.now().strftime('%Y-%m-%d')
    school_transactions = data[user_id]['school'].get('transactions', [])
    for record in school_transactions:
        if record['date'] == today:
            bot.reply_to(message, "📝 You've already logged school expenses today! Use /school_summary to view.")
            return
    
    msg = bot.reply_to(message, "🏫 *SCHOOL ALLOWANCE TRACKING*\n\n💰 Enter your school allowance for today:", parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_school_allowance)

def process_school_allowance(message):
    try:
        allowance = float(message.text)
        user_id = str(message.from_user.id)
        data = load_data()
        
        # Calculate school-specific thresholds
        thresholds = calculate_thresholds(allowance, SCHOOL_CATEGORIES)
        
        # Create school transaction record
        school_record = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'type': 'school',
            'allowance': allowance,
            'thresholds': thresholds,
            'spent': {},
            'total_saved': 0
        }
        
        data[user_id]['school']['transactions'].append(school_record)
        save_data(data)
        
        # Start asking for school expenses
        transport_threshold = thresholds['transport']
        msg = bot.reply_to(message, f"🚗 *School Transportation:*\nMax: ₱{transport_threshold:,.0f}\nSpent amount:", parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_school_transport, user_id)
        
    except ValueError:
        bot.reply_to(message, "❌ Please enter a valid number for allowance.")

def process_school_transport(message, user_id):
    try:
        amount = float(message.text)
        data = load_data()
        current_record = data[user_id]['school']['transactions'][-1]
        
        current_record['spent']['transport'] = amount
        save_data(data)
        
        # Next: Lunch
        lunch_threshold = current_record['thresholds']['lunch']
        msg = bot.reply_to(message, f"🍔 *School Lunch:*\nMax: ₱{lunch_threshold:,.0f}\nSpent amount:", parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_school_lunch, user_id)
        
    except ValueError:
        bot.reply_to(message, "❌ Please enter a valid number.")

def process_school_lunch(message, user_id):
    try:
        amount = float(message.text)
        data = load_data()
        current_record = data[user_id]['school']['transactions'][-1]
        
        current_record['spent']['lunch'] = amount
        save_data(data)
        
        # Next: Merienda
        merienda_threshold = current_record['thresholds']['merienda']
        msg = bot.reply_to(message, f"🍎 *School Merienda:*\nMax: ₱{merienda_threshold:,.0f}\nSpent amount:", parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_school_merienda, user_id)
        
    except ValueError:
        bot.reply_to(message, "❌ Please enter a valid number.")

def process_school_merienda(message, user_id):
    try:
        amount = float(message.text)
        data = load_data()
        current_record = data[user_id]['school']['transactions'][-1]
        
        current_record['spent']['merienda'] = amount
        save_data(data)
        
        # Next: School Supplies
        supplies_threshold = current_record['thresholds']['school_supplies']
        msg = bot.reply_to(message, f"📚 *School Supplies:*\nMax: ₱{supplies_threshold:,.0f}\nSpent amount:", parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_school_supplies, user_id)
        
    except ValueError:
        bot.reply_to(message, "❌ Please enter a valid number.")

def process_school_supplies(message, user_id):
    try:
        amount = float(message.text)
        data = load_data()
        current_record = data[user_id]['school']['transactions'][-1]
        
        current_record['spent']['school_supplies'] = amount
        save_data(data)
        
        # Next: Load/Data
        load_threshold = current_record['thresholds']['load_data']
        msg = bot.reply_to(message, f"📱 *Load/Data:*\nMax: ₱{load_threshold:,.0f}\nSpent amount:", parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_school_load, user_id)
        
    except ValueError:
        bot.reply_to(message, "❌ Please enter a valid number.")

def process_school_load(message, user_id):
    try:
        amount = float(message.text)
        data = load_data()
        current_record = data[user_id]['school']['transactions'][-1]
        
        current_record['spent']['load_data'] = amount
        
        # Calculate total saved
        total_saved = 0
        for category, threshold in current_record['thresholds'].items():
            if category == 'savings':
                total_saved += threshold  # Guaranteed savings
            else:
                spent = current_record['spent'].get(category, 0)
                total_saved += (threshold - spent)
        
        current_record['total_saved'] = total_saved
        save_data(data)
        
        # Show final summary
        show_school_summary_message(message, user_id)
        
    except ValueError:
        bot.reply_to(message, "❌ Please enter a valid number.")

def show_school_summary_message(message, user_id):
    data = load_data()
    current_record = data[user_id]['school']['transactions'][-1]
    
    summary = f"""
🏫 *SCHOOL ALLOWANCE SUMMARY - {current_record['date']}*

💵 Allowance: ₱{current_record['allowance']:,.0f}
💰 Total Saved: ₱{current_record['total_saved']:,.0f}

*Category Breakdown:*
"""
    
    for category, threshold in current_record['thresholds'].items():
        if category != 'savings':
            spent = current_record['spent'].get(category, 0)
            saved = threshold - spent
            notes = ai_generate_notes(category, spent, threshold)
            
            summary += f"\n{get_school_emoji(category)} {category.replace('_', ' ').title()}:"
            summary += f"\n  Budget: ₱{threshold:,.0f} | Spent: ₱{spent:,.0f}"
            summary += f"\n  Saved: ₱{saved:,.0f}"
            summary += f"\n  💡 {notes}\n"
    
    # Add guaranteed savings
    savings_threshold = current_record['thresholds']['savings']
    summary += f"\n💰 *Guaranteed Savings:* ₱{savings_threshold:,.0f}"
    
    bot.reply_to(message, summary, parse_mode='Markdown')
    
    # Add AI insights if enough data
    if len(data[user_id]['school']['transactions']) >= 3:
        insights = ai_analyze_patterns(data, user_id)
        bot.send_message(message.chat.id, insights, parse_mode='Markdown')

@bot.message_handler(commands=['school_summary'])
def show_school_summary(message):
    user_id = str(message.from_user.id)
    data = load_data()
    
    if user_id not in data or not data[user_id]['school'].get('transactions'):
        bot.reply_to(message, "📚 No school records found. Use /school_log to start tracking.")
        return
    
    show_school_summary_message(message, user_id)

@bot.message_handler(commands=['life_log'])
def start_life_logging(message):
    user_id = str(message.from_user.id)
    data = load_data()
    
    if user_id not in data:
        data[user_id] = {'school': {'transactions': []}, 'life': {'transactions': []}, 'wallet': {'current_balance': 0, 'total_savings': 0, 'transactions': []}}
    
    life_categories_text = "🏠 *LIFE EXPENSES TRACKING*\n\n"
    life_categories_text += "💵 Enter your life budget for today:"
    
    msg = bot.reply_to(message, life_categories_text, parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_life_budget)

def process_life_budget(message):
    try:
        budget = float(message.text)
        user_id = str(message.from_user.id)
        data = load_data()
        
        # Calculate life-specific thresholds
        thresholds = calculate_thresholds(budget, LIFE_CATEGORIES)
        
        # Create life transaction record
        life_record = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'type': 'life',
            'budget': budget,
            'thresholds': thresholds,
            'spent': {},
            'total_saved': 0
        }
        
        data[user_id]['life']['transactions'].append(life_record)
        save_data(data)
        
        # Start life expenses logging
        msg = bot.reply_to(message, "💇 *Personal Care* (haircut, toiletries):\nEnter amount spent:", parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_life_personal_care, user_id)
        
    except ValueError:
        bot.reply_to(message, "❌ Please enter a valid number for budget.")

def process_life_personal_care(message, user_id):
    try:
        amount = float(message.text)
        data = load_data()
        current_record = data[user_id]['life']['transactions'][-1]
        
        current_record['spent']['personal_care'] = amount
        save_data(data)
        
        # Next category
        msg = bot.reply_to(message, "🎬 *Entertainment* (movies, gala, shopping):\nEnter amount spent:", parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_life_entertainment, user_id)
        
    except ValueError:
        bot.reply_to(message, "❌ Please enter a valid number.")

def process_life_entertainment(message, user_id):
    try:
        amount = float(message.text)
        data = load_data()
        current_record = data[user_id]['life']['transactions'][-1]
        
        current_record['spent']['entertainment'] = amount
        save_data(data)
        
        # Next category
        msg = bot.reply_to(message, "🍕 *Food Delivery* (GrabFood, FoodPanda):\nEnter amount spent:", parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_life_food_delivery, user_id)
        
    except ValueError:
        bot.reply_to(message, "❌ Please enter a valid number.")

def process_life_food_delivery(message, user_id):
    try:
        amount = float(message.text)
        data = load_data()
        current_record = data[user_id]['life']['transactions'][-1]
        
        current_record['spent']['food_delivery'] = amount
        save_data(data)
        
        # Next category
        msg = bot.reply_to(message, "🎮 *Hobbies* (games, books, sports):\nEnter amount spent:", parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_life_hobbies, user_id)
        
    except ValueError:
        bot.reply_to(message, "❌ Please enter a valid number.")

def process_life_hobbies(message, user_id):
    try:
        amount = float(message.text)
        data = load_data()
        current_record = data[user_id]['life']['transactions'][-1]
        
        current_record['spent']['hobbies'] = amount
        
        # Calculate total saved
        total_saved = 0
        for category, threshold in current_record['thresholds'].items():
            if category == 'savings':
                total_saved += threshold  # Guaranteed savings
            else:
                spent = current_record['spent'].get(category, 0)
                total_saved += (threshold - spent)
        
        current_record['total_saved'] = total_saved
        save_data(data)
        
        # Show final summary
        show_life_summary_message(message, user_id)
        
    except ValueError:
        bot.reply_to(message, "❌ Please enter a valid number.")

def show_life_summary_message(message, user_id):
    data = load_data()
    current_record = data[user_id]['life']['transactions'][-1]
    
    summary = f"""
🏠 *LIFE EXPENSES SUMMARY - {current_record['date']}*

💵 Budget: ₱{current_record['budget']:,.0f}
💰 Total Saved: ₱{current_record['total_saved']:,.0f}

*Category Breakdown:*
"""
    
    for category, threshold in current_record['thresholds'].items():
        if category != 'savings':
            spent = current_record['spent'].get(category, 0)
            saved = threshold - spent
            notes = ai_generate_notes(category, spent, threshold)
            
            summary += f"\n{get_life_emoji(category)} {category.replace('_', ' ').title()}:"
            summary += f"\n  Budget: ₱{threshold:,.0f} | Spent: ₱{spent:,.0f}"
            summary += f"\n  Saved: ₱{saved:,.0f}"
            summary += f"\n  💡 {notes}\n"
    
    # Add guaranteed savings
    savings_threshold = current_record['thresholds']['savings']
    summary += f"\n💰 *Guaranteed Savings:* ₱{savings_threshold:,.0f}"
    
    bot.reply_to(message, summary, parse_mode='Markdown')

@bot.message_handler(commands=['life_summary'])
def show_life_summary(message):
    user_id = str(message.from_user.id)
    data = load_data()
    
    if user_id not in data or not data[user_id]['life'].get('transactions'):
        bot.reply_to(message, "🏠 No life expenses found. Use /life_log to start tracking.")
        return
    
    show_life_summary_message(message, user_id)

@bot.message_handler(commands=['overall_balance'])
def show_overall_balance(message):
    user_id = str(message.from_user.id)
    data = load_data()
    
    if user_id not in data:
        bot.reply_to(message, "📊 No records found. Use /school_log or /life_log to start tracking.")
        return
    
    overall_text = "📊 *OVERALL FINANCIAL OVERVIEW*\n\n"
    
    # School Section
    if data[user_id]['school'].get('transactions'):
        school_data = data[user_id]['school']['transactions'][-1]
        school_saved = school_data.get('total_saved', 0)
        overall_text += f"🏫 *School Allowance:*\n"
        overall_text += f"   Allowance: ₱{school_data['allowance']:,.0f}\n"
        overall_text += f"   Saved: ₱{school_saved:,.0f}\n\n"
    else:
        overall_text += "🏫 *School:* No data yet\n\n"
    
    # Life Section  
    if data[user_id]['life'].get('transactions'):
        life_data = data[user_id]['life']['transactions'][-1]
        life_saved = life_data.get('total_saved', 0)
        overall_text += f"🏠 *Life Expenses:*\n"
        overall_text += f"   Budget: ₱{life_data['budget']:,.0f}\n"
        overall_text += f"   Saved: ₱{life_saved:,.0f}\n\n"
    else:
        overall_text += "🏠 *Life:* No data yet\n\n"
    
    # Totals
    total_allowance = school_data.get('allowance', 0) + life_data.get('budget', 0)
    total_saved = school_saved + life_saved
    
    overall_text += f"💰 *TOTALS:*\n"
    overall_text += f"   Total Money: ₱{total_allowance:,.0f}\n"
    overall_text += f"   Total Saved: ₱{total_saved:,.0f}\n"
    overall_text += f"   Savings Rate: {(total_saved/total_allowance*100) if total_allowance > 0 else 0:.1f}%"
    
    bot.reply_to(message, overall_text, parse_mode='Markdown')

@bot.message_handler(commands=['insights'])
def show_ai_insights(message):
    user_id = str(message.from_user.id)
    data = load_data()
    
    if user_id not in data or len(data[user_id]['school'].get('transactions', [])) < 2:
        bot.reply_to(message, "📊 Need at least 2 days of school data for AI insights.")
        return
    
    insights = ai_analyze_patterns(data, user_id)
    bot.reply_to(message, insights, parse_mode='Markdown')

@bot.message_handler(commands=['balance'])
def check_wallet_balance(message):
    user_id = str(message.from_user.id)
    data = load_data()
    
    if user_id not in data:
        data[user_id] = {'school': {'transactions': []}, 'life': {'transactions': []}, 'wallet': {'current_balance': 0, 'total_savings': 0, 'transactions': []}}
        save_data(data)
    
    wallet = data[user_id]['wallet']
    
    balance_text = f"""
💼 *DIGITAL WALLET*

💰 *Current Balance:* ₱{wallet['current_balance']:,.2f}
🎯 *Total Savings:* ₱{wallet['total_savings']:,.2f}

💡 Use /add_money to add funds or /transfer to move to savings.
"""
    bot.reply_to(message, balance_text, parse_mode='Markdown')

@bot.message_handler(commands=['add_money'])
def add_money_to_wallet(message):
    try:
        amount = float(message.text.split()[1])
        user_id = str(message.from_user.id)
        data = load_data()
        
        if user_id not in data:
            data[user_id] = {'school': {'transactions': []}, 'life': {'transactions': []}, 'wallet': {'current_balance': 0, 'total_savings': 0, 'transactions': []}}
        
        data[user_id]['wallet']['current_balance'] += amount
        
        # Add transaction record
        if 'transactions' not in data[user_id]['wallet']:
            data[user_id]['wallet']['transactions'] = []
            
        transaction = {
            'date': datetime.now().isoformat(),
            'type': 'deposit',
            'amount': amount,
            'balance_after': data[user_id]['wallet']['current_balance']
        }
        data[user_id]['wallet']['transactions'].append(transaction)
        
        save_data(data)
        
        response = f"""
✅ *Money Added to Wallet!*

💵 Amount: ₱{amount:,.2f}
💰 New Balance: ₱{data[user_id]['wallet']['current_balance']:,.2f}
"""
        bot.reply_to(message, response, parse_mode='Markdown')
        
    except (IndexError, ValueError):
        bot.reply_to(message, "❌ Usage: `/add_money 1000`", parse_mode='Markdown')

if __name__ == "__main__":
    print("🚀 Smart Allowance Bot starting on Railway...")
    print("✅ Bot Token Loaded Successfully")
    print("🤖 Bot is now running 24/7!")
    
    try:
        bot.polling(none_stop=True, interval=0, timeout=20)
    except Exception as e:
        print(f"❌ Bot error: {e}")
        print("🔄 Restarting...")
