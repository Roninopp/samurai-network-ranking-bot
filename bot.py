import os
import logging
import sqlite3
import asyncio
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Use environment variable for security
BOT_TOKEN = os.getenv('BOT_TOKEN', 'your_bot_token_here')

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Database setup
class Database:
    def __init__(self):
        self.connection = sqlite3.connect('game_bot.db', check_same_thread=False, timeout=10)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.connection.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                coins INTEGER DEFAULT 100,
                gems INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                battles_won INTEGER DEFAULT 0,
                battles_lost INTEGER DEFAULT 0,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS battles (
                battle_id INTEGER PRIMARY KEY AUTOINCREMENT,
                player1_id INTEGER,
                player2_id INTEGER,
                battle_type TEXT,
                bet_amount INTEGER,
                winner_id INTEGER,
                battle_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.connection.commit()

db = Database()

# Safe database execution
def safe_db_execute(func):
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                await asyncio.sleep(0.1)
                return await func(*args, **kwargs)
            logger.error(f"Database error in {func.__name__}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            return None
    return wrapper

# User management
@safe_db_execute
async def get_user(user_id, username=None):
    cursor = db.connection.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    
    if not user:
        cursor.execute(
            'INSERT INTO users (user_id, username, coins) VALUES (?, ?, 100)',
            (user_id, username)
        )
        db.connection.commit()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
    
    return user

@safe_db_execute
async def update_coins(user_id, amount):
    cursor = db.connection.cursor()
    cursor.execute('UPDATE users SET coins = coins + ? WHERE user_id = ?', (amount, user_id))
    db.connection.commit()
    return True

@safe_db_execute
async def get_rankings():
    cursor = db.connection.cursor()
    cursor.execute('''
        SELECT user_id, username, coins, level, battles_won 
        FROM users 
        ORDER BY coins DESC, battles_won DESC 
        LIMIT 10
    ''')
    return cursor.fetchall()

# Keyboard layouts
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Daily Missions", callback_data="missions"),
         InlineKeyboardButton("💰 My Wallet", callback_data="wallet")],
        [InlineKeyboardButton("🏆 Rankings", callback_data="rankings"),
         InlineKeyboardButton("📊 My Stats", callback_data="stats")],
        [InlineKeyboardButton("⚔️ Battle Mode", callback_data="battle_mode"),
         InlineKeyboardButton("🎖️ Achievements", callback_data="achievements")],
        [InlineKeyboardButton("🎰 Casino", callback_data="casino"),
         InlineKeyboardButton("🛍️ Shop", callback_data="shop")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings")]
    ])

def back_button(target_menu="main"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=target_menu)]])

def battle_mode_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤺 PVP Duel", callback_data="pvp_duel")],
        [InlineKeyboardButton("👥 Team Battle", callback_data="team_battle")],
        [InlineKeyboardButton("🏆 Tournament", callback_data="tournament")],
        [InlineKeyboardButton("📜 Battle History", callback_data="battle_history")],
        [InlineKeyboardButton("🔙 Back", callback_data="main")]
    ])

def pvp_game_type_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✂️ Rock Paper Scissors", callback_data="battle_rps")],
        [InlineKeyboardButton("🎲 Dice Battle", callback_data="battle_dice")],
        [InlineKeyboardButton("📊 Stats Combat", callback_data="battle_stats")],
        [InlineKeyboardButton("⚡ Quick Draw", callback_data="battle_quick")],
        [InlineKeyboardButton("🔙 Back", callback_data="battle_mode")]
    ])

def bet_amount_keyboard(game_type):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("10 Coins", callback_data=f"bet_{game_type}_10"),
         InlineKeyboardButton("25 Coins", callback_data=f"bet_{game_type}_25")],
        [InlineKeyboardButton("50 Coins", callback_data=f"bet_{game_type}_50"),
         InlineKeyboardButton("100 Coins", callback_data=f"bet_{game_type}_100")],
        [InlineKeyboardButton("🔙 Back", callback_data="pvp_duel")]
    ])

def rps_keyboard(battle_id, bet_amount):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🪨 Rock", callback_data=f"rps_{battle_id}_{bet_amount}_rock")],
        [InlineKeyboardButton("📄 Paper", callback_data=f"rps_{battle_id}_{bet_amount}_paper")],
        [InlineKeyboardButton("✂️ Scissors", callback_data=f"rps_{battle_id}_{bet_amount}_scissors")],
        [InlineKeyboardButton("🔙 Back", callback_data="battle_rps")]
    ])

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await get_user(user.id, user.username)
    
    welcome_text = (
        "🤖 *SAMURAI NETWORK RANKING BOT*\n\n"
        "⚡ *The ULTIMATE engagement bot with samurai spirit!*\n\n"
        "🎯 *ACTIVE FEATURES:*\n"
        "• Real-time Rankings\n"
        "• Working Economy System\n"
        "• Daily Missions\n"
        "• Live Statistics\n"
        "• Functional Shop\n"
        "• Achievement System\n"
        "• ⚔️ *NEW Battle Mode!*\n\n"
        "Use the buttons below or commands!"
    )
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=main_menu_keyboard(),
        parse_mode='Markdown'
    )

async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = await get_user(user.id, user.username)
    
    if not user_data:
        await update.message.reply_text("❌ Error loading wallet. Please try again.")
        return
    
    wallet_text = (
        "💼 *YOUR WALLET*\n\n"
        f"💰 *Coins:* {user_data[2]}\n"
        f"💎 *Gems:* {user_data[3]}\n"
        f"📈 *Net Worth:* {user_data[2] + (user_data[3] * 100)}\n\n"
        "Earn coins by chatting and completing missions!"
    )
    
    if update.message:
        await update.message.reply_text(wallet_text, reply_markup=back_button(), parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(wallet_text, reply_markup=back_button(), parse_mode='Markdown')

# Fixed rankings function
async def show_rankings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        rankings = await get_rankings()
        
        if not rankings:
            rankings_text = "📊 *Rankings*\n\nNo users found yet! Start chatting to appear on the leaderboard!"
        else:
            rankings_text = "🏆 *TOP PLAYERS RANKINGS*\n\n"
            for idx, (user_id, username, coins, level, battles_won) in enumerate(rankings, 1):
                name = f"@{username}" if username else f"User{user_id}"
                rankings_text += f"{idx}. {name} - {coins} coins (Level {level})\n"
        
        if update.message:
            await update.message.reply_text(rankings_text, reply_markup=back_button(), parse_mode='Markdown')
        else:
            await update.callback_query.edit_message_text(rankings_text, reply_markup=back_button(), parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Rankings error: {e}")
        error_text = "📊 *Rankings*\n\nLeaderboard is currently updating. Please try again!"
        if update.message:
            await update.message.reply_text(error_text, reply_markup=back_button(), parse_mode='Markdown')
        else:
            await update.callback_query.edit_message_text(error_text, reply_markup=back_button(), parse_mode='Markdown')

# Battle system functions
async def battle_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    battle_text = (
        "⚔️ *BATTLE MODE*\n\n"
        "Choose your battle type:\n\n"
        "• 🤺 *PVP Duel* - 1v1 battles with betting\n"
        "• 👥 *Team Battle* - Group competitions\n"
        "• 🏆 *Tournament* - Championship brackets\n"
        "• 📜 *Battle History* - Your past battles"
    )
    
    query = update.callback_query
    await query.edit_message_text(battle_text, reply_markup=battle_mode_keyboard(), parse_mode='Markdown')

async def pvp_duel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    duel_text = (
        "🤺 *PVP DUEL*\n\n"
        "Challenge other players in various battle types:\n\n"
        "• ✂️ *Rock Paper Scissors* - Classic game with bets\n"
        "• 🎲 *Dice Battle* - Highest roll wins\n"
        "• 📊 *Stats Combat* - Based on your level & coins\n"
        "• ⚡ *Quick Draw* - Fast reaction game"
    )
    
    query = update.callback_query
    await query.edit_message_text(duel_text, reply_markup=pvp_game_type_keyboard(), parse_mode='Markdown')

async def start_battle_rps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.callback_query.from_user
    user_data = await get_user(user.id, user.username)
    
    if user_data[2] < 10:
        await update.callback_query.edit_message_text(
            "❌ You need at least 10 coins to battle!\nEarn coins by chatting or completing missions.",
            reply_markup=back_button("battle_mode")
        )
        return
    
    battle_text = (
        "✂️ *ROCK PAPER SCISSORS BATTLE*\n\n"
        "Choose your bet amount:\n\n"
        "Win double your bet if you win the battle!\n"
        f"Your current balance: {user_data[2]} coins"
    )
    
    query = update.callback_query
    await query.edit_message_text(battle_text, reply_markup=bet_amount_keyboard("rps"), parse_mode='Markdown')

# Rock Paper Scissors game
async def handle_rps_battle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    data = query.data
    
    if data.startswith('bet_rps_'):
        bet_amount = int(data.split('_')[2])
        user_data = await get_user(user.id, user.username)
        
        if user_data[2] < bet_amount:
            await query.edit_message_text(
                f"❌ You don't have enough coins!\nNeed: {bet_amount}, Have: {user_data[2]}",
                reply_markup=back_button("battle_rps")
            )
            return
        
        battle_id = f"rps_{user.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        battle_text = (
            f"✂️ *ROCK PAPER SCISSORS BATTLE*\n\n"
            f"💰 *Bet Amount:* {bet_amount} coins\n"
            f"💼 *Your Balance:* {user_data[2]} coins\n\n"
            f"Choose your move:"
        )
        
        await query.edit_message_text(battle_text, reply_markup=rps_keyboard(battle_id, bet_amount), parse_mode='Markdown')
    
    elif data.startswith('rps_'):
        parts = data.split('_')
        if len(parts) >= 5:
            user_id = parts[1]
            bet_amount = int(parts[3])
            user_move = parts[4]
            
            user_data = await get_user(user.id, user.username)
            
            if user_data[2] < bet_amount:
                await query.edit_message_text(
                    "❌ Not enough coins for this bet!",
                    reply_markup=back_button("battle_mode")
                )
                return
            
            await update_coins(user.id, -bet_amount)
            
            opponent_moves = ['rock', 'paper', 'scissors']
            opponent_move = random.choice(opponent_moves)
            
            result = determine_rps_winner(user_move, opponent_move)
            
            if result == "win":
                reward = bet_amount * 2
                result_text = "🎉 *YOU WIN!*"
                await update_coins(user.id, reward)
                final_reward = reward - bet_amount
            elif result == "lose":
                reward = 0
                result_text = "😞 *You lose...*"
                final_reward = -bet_amount
            else:
                reward = bet_amount
                result_text = "🤝 *It's a tie!*"
                await update_coins(user.id, reward)
                final_reward = 0
            
            user_data = await get_user(user.id, user.username)
            
            battle_result_text = (
                f"✂️ *BATTLE RESULTS*\n\n"
                f"Your move: {get_emoji_move(user_move)}\n"
                f"Opponent move: {get_emoji_move(opponent_move)}\n\n"
                f"{result_text}\n"
                f"💰 *Net Change:* {final_reward} coins\n"
                f"💼 *New Balance:* {user_data[2]} coins"
            )
            
            await query.edit_message_text(battle_result_text, reply_markup=back_button("battle_mode"), parse_mode='Markdown')

def get_emoji_move(move):
    moves = {'rock': '🪨 Rock', 'paper': '📄 Paper', 'scissors': '✂️ Scissors'}
    return moves.get(move, move)

def determine_rps_winner(player_move, opponent_move):
    if player_move == opponent_move:
        return "tie"
    elif (player_move == 'rock' and opponent_move == 'scissors') or \
         (player_move == 'scissors' and opponent_move == 'paper') or \
         (player_move == 'paper' and opponent_move == 'rock'):
        return "win"
    else:
        return "lose"

# Dice battle game
async def start_battle_dice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.callback_query.from_user
    user_data = await get_user(user.id, user.username)
    
    if user_data[2] < 10:
        await update.callback_query.edit_message_text(
            "❌ You need at least 10 coins to battle!",
            reply_markup=back_button("battle_mode")
        )
        return
    
    dice_text = (
        "🎲 *DICE BATTLE*\n\n"
        "Choose your bet amount:\n\n"
        "Highest roll wins double your bet!\n"
        f"Your current balance: {user_data[2]} coins"
    )
    
    query = update.callback_query
    await query.edit_message_text(dice_text, reply_markup=bet_amount_keyboard("dice"), parse_mode='Markdown')

async def handle_dice_battle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    data = query.data
    
    if data.startswith('bet_dice_'):
        bet_amount = int(data.split('_')[2])
        user_data = await get_user(user.id, user.username)
        
        if user_data[2] < bet_amount:
            await query.edit_message_text(
                f"❌ Not enough coins! Need: {bet_amount}, Have: {user_data[2]}",
                reply_markup=back_button("battle_dice")
            )
            return
        
        await update_coins(user.id, -bet_amount)
        
        player_roll = random.randint(1, 6)
        opponent_roll = random.randint(1, 6)
        
        if player_roll > opponent_roll:
            result = "🎉 *YOU WIN!*"
            reward = bet_amount * 2
            await update_coins(user.id, reward)
            net_gain = reward - bet_amount
        elif player_roll < opponent_roll:
            result = "😞 *You lose...*"
            net_gain = -bet_amount
        else:
            result = "🤝 *It's a tie!*"
            await update_coins(user.id, bet_amount)
            net_gain = 0
        
        user_data = await get_user(user.id, user.username)
        
        dice_text = (
            "🎲 *DICE BATTLE RESULTS*\n\n"
            f"**You rolled:** {player_roll}\n"
            f"**Opponent rolled:** {opponent_roll}\n\n"
            f"{result}\n"
            f"💰 *Net Change:* {net_gain} coins\n"
            f"💼 *New Balance:* {user_data[2]} coins"
        )
        
        await query.edit_message_text(dice_text, reply_markup=back_button("battle_mode"), parse_mode='Markdown')

# Stats combat
async def start_battle_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.callback_query.from_user
    user_data = await get_user(user.id, user.username)
    
    if user_data[2] < 10:
        await update.callback_query.edit_message_text(
            "❌ You need at least 10 coins to battle!",
            reply_markup=back_button("battle_mode")
        )
        return
    
    stats_text = (
        "📊 *STATS COMBAT*\n\n"
        "Choose your bet amount:\n\n"
        "Combat power = (Coins/10) + (Level×5)\n"
        "Higher power wins!\n"
        f"Your current balance: {user_data[2]} coins"
    )
    
    query = update.callback_query
    await query.edit_message_text(stats_text, reply_markup=bet_amount_keyboard("stats"), parse_mode='Markdown')

async def handle_stats_battle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    data = query.data
    
    if data.startswith('bet_stats_'):
        bet_amount = int(data.split('_')[2])
        user_data = await get_user(user.id, user.username)
        
        if user_data[2] < bet_amount:
            await query.edit_message_text(
                f"❌ Not enough coins! Need: {bet_amount}, Have: {user_data[2]}",
                reply_markup=back_button("battle_stats")
            )
            return
        
        await update_coins(user.id, -bet_amount)
        
        user_power = user_data[2] // 10 + user_data[4] * 5
        opponent_power = random.randint(50, 150)
        
        if user_power > opponent_power:
            result = "🎉 *VICTORY!*"
            reward = bet_amount * 2
            await update_coins(user.id, reward)
            net_gain = reward - bet_amount
        elif user_power < opponent_power:
            result = "😞 *Defeat...*"
            net_gain = -bet_amount
        else:
            result = "🤝 *Draw!*"
            await update_coins(user.id, bet_amount)
            net_gain = 0
        
        user_data = await get_user(user.id, user.username)
        
        stats_text = (
            "📊 *STATS COMBAT RESULTS*\n\n"
            f"**Your Combat Power:** {user_power}\n"
            f"**Opponent Power:** {opponent_power}\n\n"
            f"{result}\n"
            f"💰 *Net Change:* {net_gain} coins\n"
            f"💼 *New Balance:* {user_data[2]} coins\n\n"
            f"💪 Based on your level and wealth!"
        )
        
        await query.edit_message_text(stats_text, reply_markup=back_button("battle_mode"), parse_mode='Markdown')

# SIMPLIFIED FIXED callback handler - NO LAMBDA ERRORS
async def handle_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    await query.answer()
    
    # Handle different button clicks
    if data == 'main':
        await query.edit_message_text(
            "🤖 *SAMURAI NETWORK - Main Menu*", 
            reply_markup=main_menu_keyboard(),
            parse_mode='Markdown'
        )
    elif data == 'wallet':
        await wallet(update, context)
    elif data == 'rankings':
        await show_rankings(update, context)
    elif data == 'stats':
        await query.edit_message_text(
            "📊 *Your Stats*\n\nFeature coming soon!", 
            reply_markup=back_button(),
            parse_mode='Markdown'
        )
    elif data == 'battle_mode':
        await battle_mode(update, context)
    elif data == 'pvp_duel':
        await pvp_duel(update, context)
    elif data == 'battle_rps':
        await start_battle_rps(update, context)
    elif data == 'battle_dice':
        await start_battle_dice(update, context)
    elif data == 'battle_stats':
        await start_battle_stats(update, context)
    elif data == 'team_battle':
        await query.edit_message_text(
            "👥 *Team Battle*\n\nTeam features coming soon!", 
            reply_markup=back_button("battle_mode"),
            parse_mode='Markdown'
        )
    elif data == 'tournament':
        await query.edit_message_text(
            "🏆 *Tournament*\n\nTournament mode launching soon!", 
            reply_markup=back_button("battle_mode"),
            parse_mode='Markdown'
        )
    elif data == 'battle_history':
        await query.edit_message_text(
            "📜 *Battle History*\n\nYour battle records will appear here!", 
            reply_markup=back_button("battle_mode"),
            parse_mode='Markdown'
        )
    elif data == 'shop':
        await query.edit_message_text(
            "🛍️ *Shop*\n\nAwesome items coming soon!", 
            reply_markup=back_button(),
            parse_mode='Markdown'
        )
    elif data == 'casino':
        await query.edit_message_text(
            "🎰 *Casino*\n\nTry your luck at various games!", 
            reply_markup=back_button(),
            parse_mode='Markdown'
        )
    elif data == 'missions':
        await query.edit_message_text(
            "🎯 *Daily Missions*\n\nComplete missions to earn rewards!", 
            reply_markup=back_button(),
            parse_mode='Markdown'
        )
    elif data == 'achievements':
        await query.edit_message_text(
            "🎖️ *Achievements*\n\nUnlock achievements for special rewards!", 
            reply_markup=back_button(),
            parse_mode='Markdown'
        )
    elif data == 'settings':
        await query.edit_message_text(
            "⚙️ *Settings*\n\nConfigure your preferences!", 
            reply_markup=back_button(),
            parse_mode='Markdown'
        )
    elif data == 'battle_quick':
        await query.edit_message_text(
            "⚡ *Quick Draw*\n\nQuick draw battles coming soon!", 
            reply_markup=back_button("pvp_duel"),
            parse_mode='Markdown'
        )
    elif data.startswith('rps_'):
        await handle_rps_battle(update, context)
    elif data.startswith('bet_dice_'):
        await handle_dice_battle(update, context)
    elif data.startswith('bet_stats_'):
        await handle_stats_battle(update, context)

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception while handling an update: {context.error}")
    try:
        if update and update.callback_query:
            await update.callback_query.edit_message_text(
                "❌ An error occurred. Please try again!",
                reply_markup=back_button()
            )
    except Exception as e:
        logger.error(f"Error in error handler: {e}")

def main():
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("wallet", wallet))
    application.add_handler(CommandHandler("rankings", show_rankings))
    application.add_handler(CallbackQueryHandler(handle_button_click))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    print("🤖 Bot is running with enhanced battle system...")
    
    # Run with better error handling
    try:
        application.run_polling()
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        print(f"❌ Bot crashed: {e}")

if __name__ == '__main__':
    main()
