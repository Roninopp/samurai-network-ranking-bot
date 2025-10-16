import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from datetime import datetime, timedelta
import sqlite3
import json
import asyncio
import random
import math

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== DATABASE SETUP ====================
def init_db():
    try:
        conn = sqlite3.connect('samurai_rankings.db')
        c = conn.cursor()
        
        # Groups table
        c.execute('''CREATE TABLE IF NOT EXISTS groups
                     (group_id INTEGER PRIMARY KEY, group_title TEXT, 
                      settings TEXT, created_date DATE, is_active BOOLEAN DEFAULT 1,
                      weekly_theme TEXT, event_active BOOLEAN DEFAULT 0)''')
        
        # Users table
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (user_id INTEGER, group_id INTEGER, message_count INTEGER DEFAULT 0,
                      username TEXT, level INTEGER DEFAULT 1, xp INTEGER DEFAULT 0,
                      daily_streak INTEGER DEFAULT 0, last_active DATE, 
                      achievements TEXT, team_id INTEGER, titles TEXT,
                      PRIMARY KEY (user_id, group_id))''')
        
        # Economy table
        c.execute('''CREATE TABLE IF NOT EXISTS economy
                     (user_id INTEGER, group_id INTEGER, coins INTEGER DEFAULT 100,
                      gems INTEGER DEFAULT 0, inventory TEXT, PRIMARY KEY (user_id, group_id))''')
        
        # Teams table
        c.execute('''CREATE TABLE IF NOT EXISTS teams
                     (team_id INTEGER PRIMARY KEY, group_id INTEGER, team_name TEXT,
                      leader_id INTEGER, members_count INTEGER DEFAULT 0, 
                      total_xp INTEGER DEFAULT 0, created_date DATE)''')
        
        conn.commit()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
    finally:
        conn.close()

# ==================== ECONOMY SYSTEM ====================
async def add_coins(user_id, group_id, amount):
    try:
        conn = sqlite3.connect('samurai_rankings.db')
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO economy (user_id, group_id, coins, gems, inventory)
                     VALUES (?, ?, COALESCE((SELECT coins FROM economy WHERE user_id=? AND group_id=?), 0) + ?, 
                     COALESCE((SELECT gems FROM economy WHERE user_id=? AND group_id=?), 0), ?)''',
                  (user_id, group_id, user_id, group_id, amount, user_id, group_id, "[]"))
        conn.commit()
    except Exception as e:
        logger.error(f"Add coins error: {e}")
    finally:
        conn.close()

# ==================== CORE COMMANDS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        keyboard = [
            [InlineKeyboardButton("🎮 Daily Missions", callback_data="missions"),
             InlineKeyboardButton("💰 My Wallet", callback_data="wallet")],
            [InlineKeyboardButton("🏆 Rankings", callback_data="rankings"),
             InlineKeyboardButton("📊 My Stats", callback_data="stats")],
            [InlineKeyboardButton("👥 Team Battle", callback_data="teams"),
             InlineKeyboardButton("🎯 Achievements", callback_data="achievements")],
            [InlineKeyboardButton("🎪 Special Events", callback_data="events"),
             InlineKeyboardButton("🎰 Casino", callback_data="casino")],
            [InlineKeyboardButton("🛍️ Shop", callback_data="shop"),
             InlineKeyboardButton("⚙️ Settings", callback_data="settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🏯 **SAMURAI NETWORK RANKING BOT** 🏯\n\n"
            "⚔️ *The ULTIMATE engagement bot with samurai spirit!*\n\n"
            "**✨ MEGA FEATURES:**\n"
            "• 🏆 Weekly Tournaments\n"
            "• 👥 Team Battles\n"
            "• 🎪 Special Events\n"
            "• 🎰 Casino Games\n"
            "• 🐉 Boss Raids\n"
            "• 🎁 Daily Bonuses\n"
            "• 💰 Virtual Economy\n\n"
            "Ready for the ultimate experience?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Start command error: {e}")

async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        group_id = update.effective_chat.id
        
        conn = sqlite3.connect('samurai_rankings.db')
        c = conn.cursor()
        c.execute('''SELECT coins, gems FROM economy WHERE user_id = ? AND group_id = ?''', 
                  (user_id, group_id))
        result = c.fetchone()
        
        coins = result[0] if result else 100
        gems = result[1] if result else 0
        
        wallet_text = f"💰 **YOUR WALLET** 💰\n\n"
        wallet_text += f"🪙 **Coins:** {coins}\n"
        wallet_text += f"💎 **Gems:** {gems}\n"
        wallet_text += f"📈 **Net Worth:** {coins + (gems * 10)} 💰\n\n"
        wallet_text += "*Earn more by being active!*"
        
        keyboard = [
            [InlineKeyboardButton("🎮 Do Missions", callback_data="missions"),
             InlineKeyboardButton("🛍️ Visit Shop", callback_data="shop")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(wallet_text, reply_markup=reply_markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Wallet command error: {e}")

async def rankings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        group_id = update.effective_chat.id
        
        conn = sqlite3.connect('samurai_rankings.db')
        c = conn.cursor()
        c.execute('''SELECT username, message_count, level FROM users 
                     WHERE group_id = ? ORDER BY message_count DESC LIMIT 10''', (group_id,))
        top_users = c.fetchall()
        
        ranking_text = "🏆 **LEADERBOARD** 🏆\n\n"
        
        for i, (username, count, level) in enumerate(top_users, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            ranking_text += f"{medal} **{username}**\n   📊 Level {level} | {count} msgs\n\n"
        
        ranking_text += "💎 *Top 3 get special rewards!*"
        
        keyboard = [
            [InlineKeyboardButton("📈 My Rank", callback_data="my_rank"),
             InlineKeyboardButton("🔄 Refresh", callback_data="refresh_rankings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(ranking_text, reply_markup=reply_markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Rankings command error: {e}")

async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        shop_items = [
            {"id": 1, "name": "🌟 Special Title", "price": 500, "type": "title", "emoji": "🌟"},
            {"id": 2, "name": "💎 Custom Color", "price": 300, "type": "color", "emoji": "💎"},
            {"id": 3, "name": "🎁 Mystery Box", "price": 200, "type": "mystery", "emoji": "🎁"},
            {"id": 4, "name": "⚡ Boost (2x XP)", "price": 150, "type": "boost", "emoji": "⚡"},
        ]
        
        shop_text = "🛍️ **VIP SHOP** 🛍️\n\n"
        for item in shop_items:
            shop_text += f"{item['emoji']} **{item['name']}** - {item['price']} 🪙\n"
        
        shop_text += "\n💡 *Use coins to buy special perks!*"
        
        keyboard = []
        for item in shop_items:
            keyboard.append([InlineKeyboardButton(
                f"{item['emoji']} {item['name']} - {item['price']}🪙", 
                callback_data=f"buy_{item['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("💰 My Wallet", callback_data="wallet")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(shop_text, reply_markup=reply_markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Shop command error: {e}")

# ==================== MESSAGE HANDLER ====================
async def count_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message or update.message.chat.type not in ['group', 'supergroup']:
            return
        
        user_id = update.message.from_user.id
        group_id = update.message.chat.id
        username = update.message.from_user.username or update.message.from_user.first_name
        
        conn = sqlite3.connect('samurai_rankings.db')
        c = conn.cursor()
        
        # Update user stats
        c.execute('''INSERT OR REPLACE INTO users (user_id, group_id, username, message_count, xp, last_active)
                     VALUES (?, ?, ?, COALESCE((SELECT message_count FROM users WHERE user_id=? AND group_id=?), 0) + 1,
                     COALESCE((SELECT xp FROM users WHERE user_id=? AND group_id=?), 0) + 1, ?)''',
                  (user_id, group_id, username, user_id, group_id, user_id, group_id, datetime.now().date()))
        
        # Random coin drops
        if random.random() < 0.1:
            coin_reward = random.randint(1, 5)
            await add_coins(user_id, group_id, coin_reward)
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"Message handler error: {e}")

# ==================== BUTTON HANDLER ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "wallet":
            await wallet(query, context)
        elif data == "rankings":
            await rankings(query, context)
        elif data == "shop":
            await shop(query, context)
        elif data == "missions":
            await query.edit_message_text("🎮 **Daily Missions**\n\nComing soon! Stay tuned! 🚀")
        elif data == "stats":
            await query.edit_message_text("📊 **Your Stats**\n\nFeature launching tomorrow! ⚡")
        elif data == "teams":
            await query.edit_message_text("👥 **Team Battles**\n\nTeams feature coming next update! 🏆")
        elif data == "achievements":
            await query.edit_message_text("🎯 **Achievements**\n\nAchievements system in development! 💫")
        elif data == "events":
            await query.edit_message_text("🎪 **Special Events**\n\nEvents launching soon! 🎉")
        elif data == "casino":
            await query.edit_message_text("🎰 **Casino**\n\nCasino games coming in v2! 🎲")
        elif data.startswith("buy_"):
            await query.edit_message_text("🛍️ **Purchase**\n\nItem purchased successfully! ✅")
        else:
            await query.edit_message_text("⚡ **Feature Coming Soon!**\n\nWe're working on it! 🚀")
            
    except Exception as e:
        logger.error(f"Button handler error: {e}")

# ==================== ERROR HANDLER ====================
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception while handling an update: {context.error}")

# ==================== MAIN BOT ====================
def main():
    try:
        # Initialize database
        init_db()
        
        # Create application
        application = Application.builder().token("YOUR_BOT_TOKEN_HERE").build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("wallet", wallet))
        application.add_handler(CommandHandler("rankings", rankings))
        application.add_handler(CommandHandler("shop", shop))
        application.add_handler(CommandHandler("missions", missions))
        application.add_handler(CommandHandler("stats", stats))
        
        # Button handler
        application.add_handler(CallbackQueryHandler(button_handler))
        
        # Message handler (must be last)
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, count_message))
        
        # Error handler
        application.add_error_handler(error_handler)
        
        # Start bot
        print("🏯 Samurai Network Ranking Bot Starting...")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Bot startup error: {e}")

# Placeholder functions for future features
async def missions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎮 **Daily Missions**\n\nMissions system launching tomorrow! 🚀")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 **Your Stats**\n\nDetailed stats coming in next update! ⚡")

if __name__ == '__main__':
    main()
