from aiogram.types import InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

PROFILE_BTN = "👤 ፕሮፋይል"
DAILY_BTN = "🎁 ዕለታዊ ቦነስ"
TASKS_BTN = "📣 ተግባሮች"
GIVEAWAYS_BTN = "🎉 ጊቭአዌይ"
REFERRAL_BTN = "👥 ሪፈራል"
LEADERBOARD_BTN = "🏆 ሊደርቦርድ"
WITHDRAW_BTN = "💸 ገንዘብ ማውጣት"
HELP_BTN = "ℹ️ እገዛ"
ADMIN_BTN = "🛠 አስተዳዳሪ ፓነል"


def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text=PROFILE_BTN), KeyboardButton(text=DAILY_BTN)],
        [KeyboardButton(text=TASKS_BTN), KeyboardButton(text=GIVEAWAYS_BTN)],
        [KeyboardButton(text=REFERRAL_BTN), KeyboardButton(text=LEADERBOARD_BTN)],
        [KeyboardButton(text=WITHDRAW_BTN), KeyboardButton(text=HELP_BTN)],
    ]
    if is_admin:
        rows.append([KeyboardButton(text=ADMIN_BTN)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)



def force_join_keyboard(channels: list[dict]):
    builder = InlineKeyboardBuilder()
    for ch in channels:
        label = f"➡️ {ch['title']}"
        url = ch["invite_link"] or f"https://t.me/{str(ch['username']).lstrip('@')}"
        builder.row(InlineKeyboardButton(text=label[:64], url=url))
    builder.row(InlineKeyboardButton(text="✅ ድጋሚ ማረጋገጥ", callback_data="force_recheck"))
    return builder.as_markup()



def leaderboard_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💰 ባላንስ", callback_data="lb:balance"),
        InlineKeyboardButton(text="👥 ሪፈራል", callback_data="lb:referrals"),
    )
    builder.row(
        InlineKeyboardButton(text="🔥 ስትሪክ", callback_data="lb:streak"),
        InlineKeyboardButton(text="✅ ተግባር", callback_data="lb:tasks"),
    )
    return builder.as_markup()



def withdrawal_methods_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📱 TeleBirr", callback_data="withdraw:telebirr"),
        InlineKeyboardButton(text="🏦 CBE Birr", callback_data="withdraw:cbe_birr"),
    )
    builder.row(InlineKeyboardButton(text="🏛 ባንክ ማስተላለፍ", callback_data="withdraw:bank_transfer"))
    return builder.as_markup()



def admin_panel_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 አጠቃላይ ስታትስ", callback_data="admin:stats"),
        InlineKeyboardButton(text="💸 የወጪ ጥያቄዎች", callback_data="admin:withdrawals"),
    )
    builder.row(
        InlineKeyboardButton(text="➕ ቻናል", callback_data="admin:add_channel"),
        InlineKeyboardButton(text="➕ ተግባር", callback_data="admin:add_task"),
    )
    builder.row(
        InlineKeyboardButton(text="🎁 ጊቭአዌይ መፍጠር", callback_data="admin:create_giveaway"),
        InlineKeyboardButton(text="📢 ማስታወቂያ", callback_data="admin:broadcast"),
    )
    return builder.as_markup()



def task_keyboard(task: dict):
    builder = InlineKeyboardBuilder()
    url = task.get("invite_link") or f"https://t.me/{str(task['username']).lstrip('@')}"
    builder.row(
        InlineKeyboardButton(text="📎 ቻናሉን ክፈት", url=url),
        InlineKeyboardButton(text="✅ አረጋግጥ", callback_data=f"verify_task:{task['id']}"),
    )
    return builder.as_markup()



def giveaway_keyboard(giveaway_id: int):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🎉 ለመሳተፍ", callback_data=f"join_giveaway:{giveaway_id}"))
    return builder.as_markup()



def admin_withdraw_action_keyboard(withdrawal_id: int):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ ፍቀድ", callback_data=f"admin:approve:{withdrawal_id}"),
        InlineKeyboardButton(text="❌ ውድቅ", callback_data=f"admin:reject:{withdrawal_id}"),
    )
    return builder.as_markup()

