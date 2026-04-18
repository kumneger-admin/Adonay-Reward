import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _parse_admin_ids(raw: str) -> list[int]:
    items = []
    for part in (raw or "").split(","):
        part = part.strip()
        if part.isdigit():
            items.append(int(part))
    return items


@dataclass
class Config:
    bot_token: str = os.getenv("BOT_TOKEN", "8723528717:AAFvrY1jtv_x9YSghtCiVlx4ltmZmR2G9A")
    db_path: str = os.getenv("DB_PATH", "adonay_reward.db")
    bot_name: str = os.getenv("BOT_NAME", "Adonay Reward")
    bot_username: str = os.getenv("BOT_USERNAME", "@AdonayRewardbot")
    admin_ids: list[int] = None
    referral_bonus: int = int(os.getenv("REFERRAL_BONUS", "15"))
    min_withdrawal: int = int(os.getenv("MIN_WITHDRAWAL", "100"))
    daily_rewards: list[int] = None
    max_active_tasks: int = int(os.getenv("MAX_ACTIVE_TASKS", "5"))

    def __post_init__(self):
        self.admin_ids = _parse_admin_ids(os.getenv("ADMIN_IDS", "7014626219"))
        self.daily_rewards = [5, 7, 10, 12, 15, 20, 25]


config = Config()

