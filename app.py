import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatMemberStatus, ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, CallbackQuery, Message

from config import config
from db import Database
from keyboards import (
    ADMIN_BTN,
    DAILY_BTN,
    GIVEAWAYS_BTN,
    HELP_BTN,
    LEADERBOARD_BTN,
    PROFILE_BTN,
    REFERRAL_BTN,
    TASKS_BTN,
    WITHDRAW_BTN,
    admin_panel_keyboard,
    admin_withdraw_action_keyboard,
    force_join_keyboard,
    giveaway_keyboard,
    leaderboard_keyboard,
    main_menu,
    task_keyboard,
    withdrawal_methods_keyboard,
)
from states import AddChannelStates, AddTaskStates, BroadcastStates, GiveawayStates, WithdrawalStates

logging.basicConfig(level=logging.INFO)
router = Router()
db = Database(config.db_path)


HELP_TEXT = f"""
<b>{config.bot_name}</b> እንኳን ደህና መጡ

ይህ ቦት የሚከተሉትን ባህሪያት ይዟል፦
• ፎርስ ጆይን ቻናሎች
• የቀን ቦነስ እና ስትሪክ
• 5 የቴሌግራም ተግባሮች ከማረጋገጫ ጋር
• ሪፈራል እና የግብዣ ስርዓት
• ጊቭአዌይ መሳተፍ
• የወጪ ጥያቄ (TeleBirr / CBE Birr / ባንክ)
• ሊደርቦርድ

ዋና ትዕዛዞች፦
/start - መጀመር
/help - እገዛ
/profile - ፕሮፋይል
/tasks - ተግባሮች
/daily - ዕለታዊ ቦነስ
/invite - ሪፈራል ሊንክ
/leaderboard - ደረጃ ሰሌዳ
/giveaways - ጊቭአዌይ
/withdraw - ገንዘብ ማውጣት

አስተዳዳሪ ትዕዛዞች፦
/admin - አስተዳዳሪ ፓነል
"""


def is_admin(user_id: int) -> bool:
    return user_id in config.admin_ids


async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="ቦቱን ጀምር"),
        BotCommand(command="help", description="እገዛ እና መረጃ"),
        BotCommand(command="profile", description="ፕሮፋይል እና ስታትስ"),
        BotCommand(command="tasks", description="ተግባሮችን እይ"),
        BotCommand(command="daily", description="የዕለታዊ ቦነስ ውሰድ"),
        BotCommand(command="invite", description="ሪፈራል ሊንክ አግኝ"),
        BotCommand(command="leaderboard", description="ደረጃ ሰሌዳ"),
        BotCommand(command="giveaways", description="ጊቭአዌይ እይ"),
        BotCommand(command="withdraw", description="የወጪ ጥያቄ ላክ"),
        BotCommand(command="admin", description="አስተዳዳሪ ፓነል"),
    ]
    await bot.set_my_commands(commands)


async def resolve_bot_username(bot: Bot) -> str:
    if config.bot_username:
        return config.bot_username.lstrip("@")
    me = await bot.get_me()
    return me.username


async def member_joined(bot: Bot, chat_ref: str, user_id: int) -> bool:
    try:
        if chat_ref.startswith("-100"):
            target = int(chat_ref)
        elif chat_ref.startswith("@"):
            target = chat_ref
        else:
            target = f"@{chat_ref}"
        member = await bot.get_chat_member(target, user_id)
        return member.status in {
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR,
            ChatMemberStatus.RESTRICTED,
        }
    except Exception:
        return False


async def get_missing_force_channels(bot: Bot, user_id: int) -> list[dict]:
    channels = db.get_force_join_channels()
    missing = []
    for channel in channels:
        if not await member_joined(bot, str(channel["username"]), user_id):
            missing.append(channel)
    return missing


async def ensure_force_join(target: Message | CallbackQuery, bot: Bot, user_id: int) -> bool:
    missing = await get_missing_force_channels(bot, user_id)
    if not missing:
        return True
    text = (
        "<b>በመጀመሪያ እባክዎ የሚከተሉትን ቻናሎች ይቀላቀሉ።</b>\n\n"
        "ከተቀላቀሉ በኋላ ‘ድጋሚ ማረጋገጥ’ ይጫኑ።"
    )
    markup = force_join_keyboard(missing)
    if isinstance(target, CallbackQuery):
        await target.message.answer(text, reply_markup=markup)
        await target.answer("መጀመሪያ ፎርስ ጆይን ያጠናቅቁ።", show_alert=True)
    else:
        await target.answer(text, reply_markup=markup)
    return False


async def notify_admins(bot: Bot, text: str, reply_markup=None):
    for admin_id in config.admin_ids:
        try:
            await bot.send_message(admin_id, text, reply_markup=reply_markup)
        except Exception:
            continue


@router.message(CommandStart())
async def start_handler(message: Message, bot: Bot):
    ref_code = None
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) > 1:
        ref_code = parts[1].strip()

    user, created = db.create_or_get_user(message.from_user, ref_code)
    if not await ensure_force_join(message, bot, message.from_user.id):
        return

    welcome = [
        f"<b>{config.bot_name}</b> ላይ እንኳን ደህና መጡ {message.from_user.full_name}!",
        "",
        "🎁 ቦነስ ይውሰዱ፣ 📣 ተግባሮችን ያጠናቅቁ፣ 👥 ጓደኞችን ይጋብዙ እና 💸 ገንዘብ ያውጡ።",
    ]
    if created and ref_code:
        welcome.append(f"\n✅ በሪፈራል ሊንክ ተመዝግበዋል።")
    await message.answer("\n".join(welcome), reply_markup=main_menu(is_admin(message.from_user.id)))


@router.message(Command("help"))
@router.message(F.text == HELP_BTN)
async def help_handler(message: Message):
    await message.answer(HELP_TEXT, reply_markup=main_menu(is_admin(message.from_user.id)))


@router.callback_query(F.data == "force_recheck")
async def force_recheck_handler(callback: CallbackQuery, bot: Bot):
    if await ensure_force_join(callback, bot, callback.from_user.id):
        await callback.message.answer(
            "✅ ሁሉንም የግዴታ ቻናሎች ተቀላቅለዋል።",
            reply_markup=main_menu(is_admin(callback.from_user.id)),
        )
        await callback.answer("ተሳክቷል")


@router.message(Command("profile"))
@router.message(F.text == PROFILE_BTN)
async def profile_handler(message: Message, bot: Bot):
    if not await ensure_force_join(message, bot, message.from_user.id):
        return
    user = db.get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("/start በመጠቀም በመጀመሪያ ይጀምሩ።")
        return
    text = f"""
<b>👤 የተጠቃሚ ፕሮፋይል</b>

🆔 መለያ: <code>{user['telegram_id']}</code>
👤 ስም: {user['full_name']}
💰 ባላንስ: <b>{user['balance']} ብር</b>
📈 ጠቅላላ ገቢ: {user['total_earned']} ብር
💸 ጠቅላላ ወጪ: {user['total_withdrawn']} ብር
👥 ሪፈራል: {user['referral_count']}
✅ የተጠናቀቁ ተግባሮች: {user['tasks_completed']}
🎉 የተሳተፉባቸው ጊቭአዌዮች: {user['giveaways_joined']}
🔥 የቀን ስትሪክ: {user['daily_streak']}
📅 የመጨረሻ ቦነስ: {user['last_bonus_date'] or 'አልወሰዱም'}
🔗 ሪፈራል ኮድ: <code>{user['referral_code']}</code>
"""
    await message.answer(text)


@router.message(Command("daily"))
@router.message(F.text == DAILY_BTN)
async def daily_handler(message: Message, bot: Bot):
    if not await ensure_force_join(message, bot, message.from_user.id):
        return
    user = db.get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("/start በመጠቀም ይጀምሩ።")
        return
    success, reward, streak = db.claim_daily_bonus(user["id"])
    if not success:
        await message.answer("⏳ ዛሬ የዕለታዊ ቦነስ አስቀድመው ወስደዋል።")
        return
    await message.answer(
        f"🎁 <b>የዛሬ ቦነስ ተጨምሯል!</b>\n\n+{reward} ብር\n🔥 አሁን ያሉት ስትሪክ: {streak} ቀን"
    )


@router.message(Command("invite"))
@router.message(F.text == REFERRAL_BTN)
async def invite_handler(message: Message, bot: Bot):
    if not await ensure_force_join(message, bot, message.from_user.id):
        return
    user = db.get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("/start በመጠቀም ይጀምሩ።")
        return
    username = await resolve_bot_username(bot)
    link = f"https://t.me/{username}?start={user['referral_code']}"
    text = f"""
<b>👥 ሪፈራል ስርዓት</b>

ጓደኞችዎን በዚህ ሊንክ ይጋብዙ፦
{link}

🎁 አንድ ተጠቃሚ ሲመዘገብ የሚያገኙት: <b>{config.referral_bonus} ብር</b>
👥 ጠቅላላ ሪፈራሎች: <b>{user['referral_count']}</b>
🔑 ኮድ: <code>{user['referral_code']}</code>
"""
    await message.answer(text)


@router.message(Command("leaderboard"))
@router.message(F.text == LEADERBOARD_BTN)
async def leaderboard_handler(message: Message, bot: Bot):
    if not await ensure_force_join(message, bot, message.from_user.id):
        return
    await message.answer("🏆 የሊደርቦርድ ምድብ ይምረጡ፦", reply_markup=leaderboard_keyboard())


@router.callback_query(F.data.startswith("lb:"))
async def leaderboard_callback(callback: CallbackQuery):
    category = callback.data.split(":", 1)[1]
    title_map = {
        "balance": "💰 በባላንስ ላይ ከፍተኛ",
        "referrals": "👥 በሪፈራል ላይ ከፍተኛ",
        "streak": "🔥 በስትሪክ ላይ ከፍተኛ",
        "tasks": "✅ በተግባር ላይ ከፍተኛ",
    }
    rows = db.get_leaderboard(category)
    if not rows:
        await callback.message.answer("ለአሁን የሚታይ መረጃ የለም።")
        await callback.answer()
        return
    lines = [f"<b>{title_map.get(category, '🏆 ሊደርቦርድ')}</b>"]
    for idx, row in enumerate(rows, start=1):
        name = row['full_name'] or row['username'] or 'ተጠቃሚ'
        lines.append(f"{idx}. {name} — <b>{row['score']}</b>")
    await callback.message.answer("\n".join(lines))
    await callback.answer()


@router.message(Command("tasks"))
@router.message(F.text == TASKS_BTN)
async def tasks_handler(message: Message, bot: Bot):
    if not await ensure_force_join(message, bot, message.from_user.id):
        return
    user = db.get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("/start በመጠቀም ይጀምሩ።")
        return
    tasks = db.get_active_tasks()
    if not tasks:
        await message.answer("ለአሁን ንቁ ተግባሮች አልተጨመሩም።")
        return
    await message.answer(f"📣 <b>ንቁ ተግባሮች ({len(tasks)})</b>")
    for task in tasks:
        done = db.has_completed_task(user["id"], task["id"])
        status = "✅ ተጠናቋል" if done else "⏳ በመጠባበቅ ላይ"
        text = f"""
<b>{task['title']}</b>
ቻናል: {task['channel_title']}
ሽልማት: <b>{task['reward_points']} ብር</b>
ሁኔታ: {status}

{task['description'] or 'ቻናሉን ተቀላቀሉ እና ማረጋገጫ ይጫኑ።'}
"""
        await message.answer(text, reply_markup=task_keyboard(task))


@router.callback_query(F.data.startswith("verify_task:"))
async def verify_task_handler(callback: CallbackQuery, bot: Bot):
    if not await ensure_force_join(callback, bot, callback.from_user.id):
        return
    user = db.get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("/start በመጀመሪያ ይጀምሩ።", show_alert=True)
        return
    task_id = int(callback.data.split(":", 1)[1])
    task = db.get_task(task_id)
    if not task:
        await callback.answer("ተግባሩ አልተገኘም።", show_alert=True)
        return
    if not await member_joined(bot, str(task["username"]), callback.from_user.id):
        await callback.answer("እባክዎ መጀመሪያ ቻናሉን ይቀላቀሉ።", show_alert=True)
        return
    success, reward = db.complete_task(user["id"], task_id)
    if not success:
        await callback.answer("ይህን ተግባር አስቀድመው ጨርሰዋል።", show_alert=True)
        return
    await callback.message.answer(f"✅ <b>{task['title']}</b> ተረጋግጧል።\n+{reward} ብር ተጨምሯል።")
    await callback.answer("ተሳክቷል")


@router.message(Command("giveaways"))
@router.message(F.text == GIVEAWAYS_BTN)
async def giveaways_handler(message: Message, bot: Bot):
    if not await ensure_force_join(message, bot, message.from_user.id):
        return
    giveaways = db.get_active_giveaways()
    if not giveaways:
        await message.answer("ለአሁን ንቁ ጊቭአዌይ የለም።")
        return
    await message.answer("🎉 <b>ንቁ ጊቭአዌዮች</b>")
    for item in giveaways:
        text = f"""
<b>{item['title']}</b>
🎁 ሽልማት: {item['reward_text']}
👥 ተሳታፊዎች: {item['total_entries']}
🏆 አሸናፊዎች: {item['winner_count']}
⏰ የሚያበቃበት: {item['end_at']}

{item['description'] or ''}
"""
        await message.answer(text, reply_markup=giveaway_keyboard(item["id"]))


@router.callback_query(F.data.startswith("join_giveaway:"))
async def join_giveaway_handler(callback: CallbackQuery, bot: Bot):
    if not await ensure_force_join(callback, bot, callback.from_user.id):
        return
    user = db.get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("/start በመጀመሪያ ይጀምሩ።", show_alert=True)
        return
    giveaway_id = int(callback.data.split(":", 1)[1])
    ok = db.join_giveaway(giveaway_id, user["id"])
    if not ok:
        await callback.answer("ይህን ጊቭአዌይ አስቀድመው ተቀላቅለዋል።", show_alert=True)
        return
    await callback.message.answer("🎉 በተሳካ ሁኔታ ወደ ጊቭአዌዩ ገብተዋል።")
    await callback.answer("ተሳትፎ ተመዝግቧል")


@router.message(Command("withdraw"))
@router.message(F.text == WITHDRAW_BTN)
async def withdraw_handler(message: Message, bot: Bot):
    if not await ensure_force_join(message, bot, message.from_user.id):
        return
    user = db.get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("/start በመጠቀም ይጀምሩ።")
        return
    text = f"""
<b>💸 የገንዘብ ማውጫ</b>

ያለዎት ባላንስ: <b>{user['balance']} ብር</b>
አነስተኛ ማውጫ: <b>{config.min_withdrawal} ብር</b>

እባክዎ የመክፈያ መንገድ ይምረጡ።
"""
    await message.answer(text, reply_markup=withdrawal_methods_keyboard())


@router.callback_query(F.data.startswith("withdraw:"))
async def withdraw_method_handler(callback: CallbackQuery, state: FSMContext):
    method_key = callback.data.split(":", 1)[1]
    method_names = {
        "telebirr": "TeleBirr",
        "cbe_birr": "CBE Birr",
        "bank_transfer": "Bank Transfer",
    }
    await state.update_data(method=method_names.get(method_key, method_key))
    await state.set_state(WithdrawalStates.amount)
    await callback.message.answer("የማውጣት መጠን በብር ያስገቡ፦")
    await callback.answer()


@router.message(WithdrawalStates.amount)
async def withdraw_amount_state(message: Message, state: FSMContext):
    try:
        amount = int(message.text.strip())
    except Exception:
        await message.answer("እባክዎ ትክክለኛ ቁጥር ያስገቡ።")
        return
    await state.update_data(amount=amount)
    await state.set_state(WithdrawalStates.details)
    await message.answer(
        "የመቀበያ መረጃ ያስገቡ።\n"
        "ለምሳሌ፦ ሙሉ ስም + ስልክ ቁጥር / የባንክ ሂሳብ ቁጥር / መረጃ ዝርዝር"
    )


@router.message(WithdrawalStates.details)
async def withdraw_details_state(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user = db.get_user_by_telegram_id(message.from_user.id)
    if not user:
        await state.clear()
        await message.answer("/start በመጠቀም ይጀምሩ።")
        return
    try:
        withdrawal_id = db.create_withdrawal(user["id"], data["method"], int(data["amount"]), message.text.strip())
    except ValueError as exc:
        await message.answer(f"❌ {exc}")
        await state.clear()
        return

    await message.answer(
        f"✅ የወጪ ጥያቄዎ ተመዝግቧል።\nመለያ ቁጥር: <code>#{withdrawal_id}</code>\n"
        f"መንገድ: {data['method']}\nመጠን: {data['amount']} ብር"
    )
    await notify_admins(
        bot,
        f"💸 <b>አዲስ የወጪ ጥያቄ</b>\n\n#ID: {withdrawal_id}\n👤 ተጠቃሚ: {user['full_name']}\n💰 መጠን: {data['amount']} ብር\n🏦 መንገድ: {data['method']}\n📝 ዝርዝር: {message.text.strip()}",
        reply_markup=admin_withdraw_action_keyboard(withdrawal_id),
    )
    await state.clear()


@router.message(Command("admin"))
@router.message(F.text == ADMIN_BTN)
async def admin_panel_handler(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ ይህ ክፍል ለአስተዳዳሪዎች ብቻ ነው።")
        return
    await message.answer(
        "<b>🛠 አስተዳዳሪ ፓነል</b>\nከታች ያሉትን አማራጮች ይጠቀሙ።",
        reply_markup=admin_panel_keyboard(),
    )


@router.callback_query(F.data == "admin:stats")
async def admin_stats_handler(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("አልተፈቀደም", show_alert=True)
        return
    stats = db.get_stats()
    text = f"""
<b>📊 አጠቃላይ ስታትስ</b>

👥 ጠቅላላ ተጠቃሚዎች: {stats['users']}
🎉 ጠቅላላ ጊቭአዌዮች: {stats['giveaways']}
📣 ንቁ ተግባሮች: {stats['tasks']}
💸 በመጠባበቅ ላይ ያሉ የወጪ ጥያቄዎች: {stats['pending_withdrawals']}
"""
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == "admin:withdrawals")
async def admin_withdrawals_handler(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("አልተፈቀደም", show_alert=True)
        return
    rows = db.get_pending_withdrawals()
    if not rows:
        await callback.message.answer("የሚጠባበቁ የወጪ ጥያቄዎች የሉም።")
        await callback.answer()
        return
    for item in rows[:10]:
        username = f"@{item['username']}" if item['username'] else "—"
        text = f"""
<b>💸 የወጪ ጥያቄ #{item['id']}</b>
👤 ተጠቃሚ: {item['full_name']}
🔖 ዩዘርኔም: {username}
💰 መጠን: {item['amount']} ብር
🏦 መንገድ: {item['method']}
📝 ዝርዝር: {item['account_details']}
📅 ቀን: {item['created_at']}
"""
        await callback.message.answer(text, reply_markup=admin_withdraw_action_keyboard(item["id"]))
    await callback.answer()


@router.callback_query(F.data.startswith("admin:approve:"))
async def approve_withdrawal_handler(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("አልተፈቀደም", show_alert=True)
        return
    withdrawal_id = int(callback.data.split(":")[-1])
    result = db.approve_withdrawal(withdrawal_id)
    if not result:
        await callback.answer("ጥያቄው አልተገኘም ወይም ተሰርቷል።", show_alert=True)
        return
    user = db.fetchone("SELECT telegram_id FROM users WHERE id = ?", (result['user_id'],))
    if user:
        try:
            await bot.send_message(user["telegram_id"], f"✅ የወጪ ጥያቄዎ #{withdrawal_id} ተፈቅዷል።")
        except Exception:
            pass
    await callback.message.answer(f"✅ የወጪ ጥያቄ #{withdrawal_id} ተፈቅዷል።")
    await callback.answer("ተፈቅዷል")


@router.callback_query(F.data.startswith("admin:reject:"))
async def reject_withdrawal_handler(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("አልተፈቀደም", show_alert=True)
        return
    withdrawal_id = int(callback.data.split(":")[-1])
    result = db.reject_withdrawal(withdrawal_id)
    if not result:
        await callback.answer("ጥያቄው አልተገኘም ወይም ተሰርቷል።", show_alert=True)
        return
    user = db.fetchone("SELECT telegram_id FROM users WHERE id = ?", (result['user_id'],))
    if user:
        try:
            await bot.send_message(user["telegram_id"], f"❌ የወጪ ጥያቄዎ #{withdrawal_id} ውድቅ ተደርጓል። ብርዎ ወደ ባላንስዎ ተመልሷል።")
        except Exception:
            pass
    await callback.message.answer(f"❌ የወጪ ጥያቄ #{withdrawal_id} ውድቅ ተደርጓል።")
    await callback.answer("ውድቅ ተደርጓል")


@router.callback_query(F.data == "admin:add_channel")
async def admin_add_channel_handler(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("አልተፈቀደም", show_alert=True)
        return
    await state.set_state(AddChannelStates.title)
    await callback.message.answer("የቻናሉን ስም ያስገቡ፦")
    await callback.answer()


@router.message(AddChannelStates.title)
async def add_channel_title_state(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(AddChannelStates.username)
    await message.answer("የቻናሉን username ወይም chat id ያስገቡ፦\nለምሳሌ @adonay_channel")


@router.message(AddChannelStates.username)
async def add_channel_username_state(message: Message, state: FSMContext):
    await state.update_data(username=message.text.strip())
    await state.set_state(AddChannelStates.invite_link)
    await message.answer("የinvite link ያስገቡ። ከሌለ  - ብለው ይላኩ።")


@router.message(AddChannelStates.invite_link)
async def add_channel_invite_state(message: Message, state: FSMContext):
    invite_link = "" if message.text.strip() == "-" else message.text.strip()
    await state.update_data(invite_link=invite_link)
    await state.set_state(AddChannelStates.channel_type)
    await message.answer("የቻናሉን አይነት ያስገቡ፦\nforce ወይም task")


@router.message(AddChannelStates.channel_type)
async def add_channel_type_state(message: Message, state: FSMContext):
    channel_type = message.text.strip().lower()
    if channel_type not in {"force", "task"}:
        await message.answer("እባክዎ force ወይም task ብቻ ያስገቡ።")
        return
    data = await state.get_data()
    channel_id = db.add_channel(data["title"], data["username"], data.get("invite_link", ""), channel_type)
    await message.answer(f"✅ ቻናሉ ተመዝግቧል። መለያ: <code>{channel_id}</code>\nአይነት: <b>{channel_type}</b>")
    await state.clear()


@router.callback_query(F.data == "admin:add_task")
async def admin_add_task_handler(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("አልተፈቀደም", show_alert=True)
        return
    channels = db.get_task_channels()
    lines = ["<b>📣 ያሉ የTask Channel ዝርዝሮች</b>"]
    if channels:
        for ch in channels:
            lines.append(f"{ch['id']}. {ch['title']} — {ch['username']}")
    else:
        lines.append("እስካሁን የtask channel አልተጨመረም። መጀመሪያ /admin በመጠቀም channel ያክሉ እና አይነቱን task ያድርጉ።")
    await callback.message.answer("\n".join(lines))
    await state.set_state(AddTaskStates.channel_id)
    await callback.message.answer("ተግባሩ የሚገኝበትን channel id ያስገቡ፦")
    await callback.answer()


@router.message(AddTaskStates.channel_id)
async def add_task_channel_id_state(message: Message, state: FSMContext):
    try:
        channel_id = int(message.text.strip())
    except Exception:
        await message.answer("እባክዎ ትክክለኛ channel id ያስገቡ።")
        return
    await state.update_data(channel_id=channel_id)
    await state.set_state(AddTaskStates.title)
    await message.answer("የተግባሩን ርዕስ ያስገቡ፦")


@router.message(AddTaskStates.title)
async def add_task_title_state(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(AddTaskStates.description)
    await message.answer("የተግባሩን ማብራሪያ ያስገቡ፦")


@router.message(AddTaskStates.description)
async def add_task_desc_state(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await state.set_state(AddTaskStates.reward)
    await message.answer("የሽልማት መጠን በብር ያስገቡ፦")


@router.message(AddTaskStates.reward)
async def add_task_reward_state(message: Message, state: FSMContext):
    try:
        reward = int(message.text.strip())
    except Exception:
        await message.answer("እባክዎ ትክክለኛ ቁጥር ያስገቡ።")
        return
    data = await state.get_data()
    try:
        task_id = db.add_task(data["channel_id"], data["title"], data["description"], reward)
    except ValueError as exc:
        await message.answer(f"❌ {exc}")
        await state.clear()
        return
    await message.answer(f"✅ ተግባሩ ተመዝግቧል። መለያ: <code>{task_id}</code>")
    await state.clear()


@router.callback_query(F.data == "admin:create_giveaway")
async def admin_create_giveaway_handler(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("አልተፈቀደም", show_alert=True)
        return
    await state.set_state(GiveawayStates.title)
    await callback.message.answer("የጊቭአዌዩን ርዕስ ያስገቡ፦")
    await callback.answer()


@router.message(GiveawayStates.title)
async def giveaway_title_state(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(GiveawayStates.description)
    await message.answer("ማብራሪያ ያስገቡ፦")


@router.message(GiveawayStates.description)
async def giveaway_description_state(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await state.set_state(GiveawayStates.reward_text)
    await message.answer("የሽልማት ዝርዝር ያስገቡ፦")


@router.message(GiveawayStates.reward_text)
async def giveaway_reward_state(message: Message, state: FSMContext):
    await state.update_data(reward_text=message.text.strip())
    await state.set_state(GiveawayStates.winner_count)
    await message.answer("የአሸናፊዎች ብዛት ያስገቡ፦")


@router.message(GiveawayStates.winner_count)
async def giveaway_winner_count_state(message: Message, state: FSMContext):
    try:
        count = int(message.text.strip())
    except Exception:
        await message.answer("እባክዎ ትክክለኛ ቁጥር ያስገቡ።")
        return
    await state.update_data(winner_count=count)
    await state.set_state(GiveawayStates.end_at)
    await message.answer("የማብቂያ ቀን በዚህ ቅርጸት ያስገቡ፦ YYYY-MM-DD HH:MM")


@router.message(GiveawayStates.end_at)
async def giveaway_end_state(message: Message, state: FSMContext):
    try:
        datetime.strptime(message.text.strip(), "%Y-%m-%d %H:%M")
    except Exception:
        await message.answer("ቅርጸቱ ልክ አይደለም። ምሳሌ: 2026-04-30 18:00")
        return
    data = await state.get_data()
    giveaway_id = db.create_giveaway(
        data["title"],
        data["description"],
        data["reward_text"],
        int(data["winner_count"]),
        message.text.strip(),
        message.from_user.id,
    )
    await message.answer(f"✅ ጊቭአዌዩ ተፈጥሯል። መለያ: <code>{giveaway_id}</code>")
    await state.clear()


@router.callback_query(F.data == "admin:broadcast")
async def broadcast_start_handler(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("አልተፈቀደም", show_alert=True)
        return
    await state.set_state(BroadcastStates.text)
    await callback.message.answer("ለሁሉም ተጠቃሚዎች የሚላከውን መልዕክት ያስገቡ፦")
    await callback.answer()


@router.message(BroadcastStates.text)
async def broadcast_text_state(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    users = db.all_users()
    sent = 0
    failed = 0
    for user in users:
        try:
            await bot.send_message(user["telegram_id"], message.text)
            sent += 1
            await asyncio.sleep(0.03)
        except Exception:
            failed += 1
    await message.answer(f"📢 ማስታወቂያ ተልኳል።\n✅ ተልኳል: {sent}\n❌ አልተላከም: {failed}")
    await state.clear()


async def main():
    if not config.bot_token:
        raise RuntimeError("BOT_TOKEN በ .env ፋይል ውስጥ ያስገቡ")
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await set_commands(bot)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

