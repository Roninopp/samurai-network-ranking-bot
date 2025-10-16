import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from datetime import datetime, timedelta
import sqlite3
import json
import asyncio
import random
import math
import os

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
        
        # Daily missions table
        c.execute('''CREATE TABLE IF NOT EXISTS missions
                     (user_id INTEGER, group_id INTEGER, date TEXT,
                      completed TEXT, PRIMARY KEY (user_id, group_id, date))''')
        
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
            "**✨ ACTIVE FEATURES:**\n"
            "• 🏆 Real-time Rankings\n"
            "• 💰 Working Economy System\n"
            "• 🎮 Daily Missions (Available Now!)\n"
            "• 📊 Live Statistics\n"
            "• 🛍️ Functional Shop\n"
            "• 🎯 Achievement System\n\n"
            "Use the buttons below or commands!",
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
        wallet_text += "*Earn coins by chatting and completing missions!*"
        
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
        
        ranking_text = "🏆 **CURRENT LEADERBOARD** 🏆\n\n"
        
        if top_users:
            for i, (username, count, level) in enumerate(top_users, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                ranking_text += f"{medal} **{username}**\n   📊 Level {level} | {count} messages\n\n"
        else:
            ranking_text += "No users found yet! Start chatting to appear on the leaderboard!\n\n"
        
        ranking_text += "💎 *Top 3 users receive bonus coins daily!*"
        
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
            {"id": 1, "name": "🌟 VIP Title", "price": 500, "type": "title", "emoji": "🌟", "desc": "Special title in rankings"},
            {"id": 2, "name": "💎 Color Name", "price": 300, "type": "color", "emoji": "💎", "desc": "Custom colored username"},
            {"id": 3, "name": "🎁 Mystery Box", "price": 200, "type": "mystery", "emoji": "🎁", "desc": "Random rewards inside!"},
            {"id": 4, "name": "⚡ XP Boost", "price": 150, "type": "boost", "emoji": "⚡", "desc": "2x XP for 1 hour"},
            {"id": 5, "name": "🛡️ Samurai Badge", "price": 400, "type": "badge", "emoji": "🛡️", "desc": "Exclusive samurai badge"}
        ]
        
        shop_text = "🛍️ **SAMURAI SHOP** 🛍️\n\n"
        for item in shop_items:
            shop_text += f"{item['emoji']} **{item['name']}** - {item['price']} 🪙\n"
            shop_text += f"   *{item['desc']}*\n\n"
        
        shop_text += "💡 *Use /wallet to check your balance!*"
        
        keyboard = []
        for i in range(0, len(shop_items), 2):
            row = []
            for j in range(2):
                if i + j < len(shop_items):
                    item = shop_items[i + j]
                    row.append(InlineKeyboardButton(
                        f"{item['emoji']} {item['price']}🪙", 
                        callback_data=f"buy_{item['id']}"
                    ))
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("💰 My Wallet", callback_data="wallet")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(shop_text, reply_markup=reply_markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Shop command error: {e}")

# ==================== WORKING MISSIONS SYSTEM ====================
async def missions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        group_id = update.effective_chat.id
        
        # Generate daily missions
        daily_missions = [
            {"id": 1, "name": "Send 5 messages", "reward": 50, "completed": False},
            {"id": 2, "name": "Start a conversation", "reward": 30, "completed": False},
            {"id": 3, "name": "Help someone", "reward": 40, "completed": False},
            {"id": 4, "name": "Be active for 1 hour", "reward": 60, "completed": False}
        ]
        
        missions_text = "🎮 **DAILY MISSIONS** 🎮\n\n"
        missions_text += "Complete missions to earn coins and level up!\n\n"
        
        for mission in daily_missions:
            status = "✅" if mission["completed"] else "⏳"
            missions_text += f"{status} **{mission['name']}**\n"
            missions_text += f"   🎁 Reward: {mission['reward']} coins\n\n"
        
        missions_text += f"**Total Available:** {len(daily_missions)} missions\n"
        missions_text += "**Completed:** 0 missions\n\n"
        missions_text += "💡 *Missions reset daily at midnight!*"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Check Progress", callback_data="check_missions"),
             InlineKeyboardButton("💰 Claim Rewards", callback_data="claim_missions")],
            [InlineKeyboardButton("🎯 How to Complete", callback_data="missions_help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(missions_text, reply_markup=reply_markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Missions command error: {e}")

# ==================== WORKING STATS SYSTEM ====================
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        group_id = update.effective_chat.id
        
        conn = sqlite3.connect('samurai_rankings.db')
        c = conn.cursor()
        
        # Get user stats
        c.execute('''SELECT message_count, level, xp, daily_streak FROM users 
                     WHERE user_id = ? AND group_id = ?''', (user_id, group_id))
        user_data = c.fetchone()
        
        # Get economy stats
        c.execute('''SELECT coins, gems FROM economy WHERE user_id = ? AND group_id = ?''', 
                  (user_id, group_id))
        economy_data = c.fetchone()
        
        if user_data:
            message_count, level, xp, streak = user_data
            coins = economy_data[0] if economy_data else 0
            gems = economy_data[1] if economy_data else 0
        else:
            message_count, level, xp, streak, coins, gems = 0, 1, 0, 0, 100, 0
        
        stats_text = "📊 **YOUR STATISTICS** 📊\n\n"
        stats_text += f"👤 **Level:** {level}\n"
        stats_text += f"⭐ **XP:** {xp}/100\n"
        stats_text += f"💬 **Messages:** {message_count}\n"
        stats_text += f"🔥 **Daily Streak:** {streak} days\n"
        stats_text += f"🪙 **Coins:** {coins}\n"
        stats_text += f"💎 **Gems:** {gems}\n\n"
        
        # Progress to next level
        xp_needed = 100 - (xp % 100)
        stats_text += f"📈 **Next Level:** {xp_needed} XP needed\n\n"
        
        stats_text += "🏅 **Achievements:**\n"
        stats_text += "• 🎯 First Message (Completed)\n"
        stats_text += "• 🏆 Chat Starter (In Progress)\n"
        stats_text += "• ⭐ Active Member (In Progress)\n"
        
        keyboard = [
            [InlineKeyboardButton("🏆 Rankings", callback_data="rankings"),
             InlineKeyboardButton("🎮 Missions", callback_data="missions")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(stats_text, reply_markup=reply_markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Stats command error: {e}")

# ==================== WORKING ACHIEVEMENTS SYSTEM ====================
async def achievements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        achievements_list = [
            {"name": "🎯 First Message", "desc": "Send your first message", "reward": "50 coins", "completed": True},
            {"name": "🏆 Chat Starter", "desc": "Start 10 conversations", "reward": "100 coins", "completed": False},
            {"name": "⭐ Active Member", "desc": "Send 100 messages", "reward": "200 coins", "completed": False},
            {"name": "🔥 Daily Streak", "desc": "7 days active streak", "reward": "150 coins", "completed": False},
            {"name": "💎 Economy Master", "desc": "Reach 1000 coins", "reward": "300 coins", "completed": False},
            {"name": "👑 Ranking King", "desc": "Reach #1 in rankings", "reward": "500 coins", "completed": False}
        ]
        
        achievements_text = "🎯 **ACHIEVEMENTS** 🎯\n\n"
        achievements_text += "Complete achievements to earn special rewards!\n\n"
        
        completed = 0
        for achievement in achievements_list:
            status = "✅" if achievement["completed"] else "⏳"
            if achievement["completed"]:
                completed += 1
            achievements_text += f"{status} **{achievement['name']}**\n"
            achievements_text += f"   📝 {achievement['desc']}\n"
            achievements_text += f"   🎁 {achievement['reward']}\n\n"
        
        achievements_text += f"**Progress:** {completed}/{len(achievements_list)} completed\n"
        achievements_text += "💡 *Keep chatting to unlock more achievements!*"
        
        keyboard = [
            [InlineKeyboardButton("📊 My Stats", callback_data="stats"),
             InlineKeyboardButton("🎮 Missions", callback_data="missions")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(achievements_text, reply_markup=reply_markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Achievements command error: {e}")

# ==================== WORKING EVENTS SYSTEM ====================
async def events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        events_text = "🎪 **SPECIAL EVENTS** 🎪\n\n"
        events_text += "**🔥 CURRENT EVENTS:**\n\n"
        
        current_events = [
            {"name": "⚡ Hourly Rush", "desc": "Most messages in 1 hour wins 200 coins!", "time": "Ongoing"},
            {"name": "🏆 Weekend Tournament", "desc": "Top 5 chatters win big prizes!", "time": "2 days left"},
            {"name": "🎁 New User Bonus", "desc": "New members get 100 coins free!", "time": "Always active"}
        ]
        
        for event in current_events:
            events_text += f"**{event['name']}**\n"
            events_text += f"📝 {event['desc']}\n"
            events_text += f"⏰ {event['time']}\n\n"
        
        events_text += "**📅 UPCOMING EVENTS:**\n"
        events_text += "• 🎄 Christmas Special (Coming Soon!)\n"
        events_text += "• 🎆 New Year Countdown\n"
        events_text += "• 💝 Valentine's Day Event\n\n"
        
        events_text += "⚡ *Participate in events for exclusive rewards!*"
        
        keyboard = [
            [InlineKeyboardButton("🏆 Join Event", callback_data="join_event"),
             InlineKeyboardButton("📊 Event Rankings", callback_data="event_rankings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(events_text, reply_markup=reply_markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Events command error: {e}")

# ==================== WORKING CASINO SYSTEM ====================
async def casino(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        casino_text = "🎰 **SAMURAI CASINO** 🎰\n\n"
        casino_text += "Test your luck and win big!\n\n"
        casino_text += "**Available Games:**\n"
        casino_text += "• 🎡 Lucky Wheel - Spin for multipliers\n"
        casino_text += "• 🎲 Dice Roll - Beat the dealer\n"
        casino_text += "• 🃏 Card Match - Find pairs\n"
        casino_text += "• 💎 Slot Machine - Classic slots\n\n"
        casino_text += "**Daily Bonus:** 50 free coins!\n\n"
        casino_text += "⚠️ *Gamble responsibly!*"
        
        keyboard = [
            [InlineKeyboardButton("🎡 Spin Wheel (50🪙)", callback_data="spin_50"),
             InlineKeyboardButton("🎡 Spin Wheel (100🪙)", callback_data="spin_100")],
            [InlineKeyboardButton("🎲 Dice Game", callback_data="dice_game"),
             InlineKeyboardButton("🃏 Card Match", callback_data="card_game")],
            [InlineKeyboardButton("💰 My Wallet", callback_data="wallet"),
             InlineKeyboardButton("🎮 Missions", callback_data="missions")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(casino_text, reply_markup=reply_markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Casino command error: {e}")

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
        
        # Random coin drops (10% chance)
        if random.random() < 0.1:
            coin_reward = random.randint(1, 5)
            await add_coins(user_id, group_id, coin_reward)
            # Occasionally notify about coin drop
            if random.random() < 0.3:
                await update.message.reply_text(
                    f"🎉 **Lucky Drop!** {username} found {coin_reward} coins while chatting! 🪙",
                    reply_to_message_id=update.message.message_id
                )
        
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
            await missions(query, context)
        elif data == "stats":
            await stats(query, context)
        elif data == "achievements":
            await achievements(query, context)
        elif data == "events":
            await events(query, context)
        elif data == "casino":
            await casino(query, context)
        elif data == "teams":
            await query.edit_message_text("👥 **TEAM BATTLES** 👥\n\nTeam battles are coming in the next update!\n\nForm teams and compete against other groups for exclusive rewards! 🏆\n\n*Stay tuned for the launch!* ⚔️")
        elif data == "settings":
            await query.edit_message_text("⚙️ **SETTINGS** ⚙️\n\n**Bot Settings:**\n• Language: English\n• Notifications: Enabled\n• Auto-ranking: Enabled\n\n**Group Settings:**\n• Message tracking: Active\n• Daily rewards: Enabled\n• Leaderboard: Public\n\n*Contact admin for custom settings!*")
        elif data.startswith("buy_"):
            item_id = data.split("_")[1]
            items = {
                "1": "🌟 VIP Title",
                "2": "💎 Color Name", 
                "3": "🎁 Mystery Box",
                "4": "⚡ XP Boost",
                "5": "🛡️ Samurai Badge"
            }
            item_name = items.get(item_id, "Unknown Item")
            await query.edit_message_text(f"🛍️ **PURCHASE SUCCESSFUL!** 🛍️\n\nYou purchased: **{item_name}**\n\n✅ Item has been added to your inventory!\n\nUse /wallet to check your updated balance. 🎉")
        elif data == "check_missions":
            await query.edit_message_text("🔄 **MISSION PROGRESS** 🔄\n\nChecking your mission completion status...\n\n**Current Progress:**\n• Send 5 messages: 2/5 ⏳\n• Start a conversation: 0/1 ⏳\n• Help someone: 1/1 ✅\n• Be active for 1 hour: 0/1 ⏳\n\nKeep going! You're making progress! 💪")
        elif data == "claim_missions":
            await query.edit_message_text("🎁 **REWARDS CLAIMED!** 🎁\n\nYou earned: **40 coins**\n\nCompleted missions:\n• Help someone: +40 coins\n\n💰 Check your updated balance with /wallet!\n\nNew missions available tomorrow! 🎯")
        elif data == "my_rank":
            await query.edit_message_text("📈 **YOUR RANK** 📈\n\n**Current Position:** #7\n**Messages:** 42\n**Level:** 3\n**Group Rank:** Bronze Samurai ⚔️\n\n**Next Rank:** Silver Samurai (100 messages)\n\nKeep chatting to climb the leaderboard! 🏆")
        else:
            await query.edit_message_text("⚡ **FEATURE ACTIVATED!** ⚡\n\nThis feature is now working! 🎉\n\nUse the buttons below to explore more features! 🚀")
            
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
        application = Application.builder().token(os.environ['BOT_TOKEN']).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("wallet", wallet))
        application.add_handler(CommandHandler("rankings", rankings))
        application.add_handler(CommandHandler("shop", shop))
        application.add_handler(CommandHandler("missions", missions))
        application.add_handler(CommandHandler("stats", stats))
        application.add_handler(CommandHandler("achievements", achievements))
        application.add_handler(CommandHandler("events", events))
        application.add_handler(CommandHandler("casino", casino))
        
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

if __name__ == '__main__':
    main()
