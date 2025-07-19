from telegram import Update, ChatMemberUpdated
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ChatMemberHandler,
    filters,
)
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import asyncio

# Replace with your values
TOKEN = "7962229937:AAGRgNM6wwqyLM1pPWrwnPHbBIbqn7M6gq0"
GROUP_ID = -1002809457293  # Replace with your group ID

submissions = {}
streaks = {}
last_submission_date = {}
known_users = {}

def today():
    return datetime.now().strftime("%Y-%m-%d")

# ✅ Track new members joining
async def track_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = update.chat_member.new_chat_member
    if member.status in ["member", "administrator"]:
        user = member.user
        known_users[user.id] = user.first_name

# 📷 Handle photo submission
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type not in ["group", "supergroup"]:
        return

    user_id = update.effective_user.id
    name = update.effective_user.first_name
    known_users[user_id] = name
    date = today()
    now = datetime.now().strftime("%H:%M")

    # Create entry for today if not exists
    submissions.setdefault(date, {})

    # ❌ If user already submitted today, do nothing (quietly skip)
    if user_id in submissions[date]:
        return

    # ✅ First valid photo today: record and respond
    submissions[date][user_id] = {"name": name, "time": now}

    prev_date = last_submission_date.get(user_id)
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    if prev_date == yesterday:
        streaks[user_id] = streaks.get(user_id, 0) + 1
    else:
        streaks[user_id] = 1

    last_submission_date[user_id] = date

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"✅ {name}, आपकी आज की फ़ोटो दर्ज कर ली गई है। बहुत अच्छे!"
    )

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Group ID: {update.effective_chat.id}")
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🙏 स्वागत है! कृपया हर दिन अपने आंगनवाड़ी की फ़ोटो इस समूह में भेजें।"
    )

# /report command
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await post_summary(context)
    await asyncio.sleep(1)
    await post_top_streak_awards(context)

# 📊 Summary report
async def post_summary(context_or_bot):
    """Send the daily summary report to the group.

    This helper works both when called from a handler (passing the ``context``)
    and when triggered by the scheduler where only the ``Bot`` instance is
    available.
    """
    bot = getattr(context_or_bot, "bot", context_or_bot)

    date = today()
    today_data = submissions.get(date, {})
    today_ids = set(today_data.keys())
    member_ids = set(known_users.keys())
    pending_ids = member_ids - today_ids

    names_today = [data["name"] for data in today_data.values()]
    names_pending = [known_users.get(uid, f"User {uid}") for uid in pending_ids]

    top_streaks = sorted(
        [(uid, streaks[uid]) for uid in streaks if uid in member_ids],
        key=lambda x: x[1], reverse=True
    )[:5]

    leaderboard = "\n".join([
        f"{i+1}. {known_users.get(uid, 'User')} – {count} दिन"
        for i, (uid, count) in enumerate(top_streaks)
    ])

    summary = f"""
📊 {datetime.now().strftime('%I:%M %p')} समूह रिपोर्ट:

👥 कुल सदस्य: {len(member_ids)}
✅ आज रिपोर्ट भेजी: {len(today_ids)}
⏳ रिपोर्ट नहीं भेजी: {len(pending_ids)}

🏆 लगातार रिपोर्टिंग करने वाले:
{leaderboard if leaderboard else 'अभी कोई डेटा उपलब्ध नहीं है।'}
"""
    await bot.send_message(chat_id=GROUP_ID, text=summary)

# 🎖️ Individual badge awards
async def post_top_streak_awards(context_or_bot):
    """Send individual streak awards.

    Like :func:`post_summary`, this function accepts either a ``context`` or a
    ``Bot`` instance so it can be used by both command handlers and scheduled
    jobs.
    """
    bot = getattr(context_or_bot, "bot", context_or_bot)

    date = today()
    member_ids = set(known_users.keys())
    top_streaks = sorted(
        [(uid, streaks[uid]) for uid in streaks if uid in member_ids],
        key=lambda x: x[1], reverse=True
    )[:5]

    medals = ["🥇", "🥈", "🥉", "🎖️", "🏅"]

    for i, (uid, count) in enumerate(top_streaks):
        name = known_users.get(uid, f"User {uid}")
        msg = f"{medals[i]} *{name}*, आप आज #{i+1} स्थान पर हैं — {count} दिनों की शानदार रिपोर्टिंग के साथ! 🎉👏"
        await bot.send_message(chat_id=GROUP_ID, text=msg, parse_mode="Markdown")
        await asyncio.sleep(1)

# 🕒 Auto scheduling
def schedule_reports(app):
    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    for hour in [10, 14, 18]:
        scheduler.add_job(lambda: asyncio.run(post_summary(app.bot)), 'cron', hour=hour, minute=0)
        scheduler.add_job(lambda: asyncio.run(post_top_streak_awards(app.bot)), 'cron', hour=hour, minute=2)
    scheduler.start()

# 🚀 Main bot launcher
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.GROUPS, handle_photo))
    app.add_handler(ChatMemberHandler(track_new_members, ChatMemberHandler.CHAT_MEMBER))

    schedule_reports(app)
    print("🤖 बॉट चालू है। संदेशों की प्रतीक्षा कर रहा है...")
    app.run_polling()

if __name__ == "__main__":
    main()
