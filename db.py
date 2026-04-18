import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from config import config


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.init_db()

    def init_db(self):
        schema_path = Path(__file__).with_name("schema.sql")
        self.conn.executescript(schema_path.read_text(encoding="utf-8"))
        self.conn.commit()

    def execute(self, query: str, params: tuple = ()):
        cur = self.conn.cursor()
        cur.execute(query, params)
        self.conn.commit()
        return cur

    def fetchone(self, query: str, params: tuple = ()):
        return self.conn.execute(query, params).fetchone()

    def fetchall(self, query: str, params: tuple = ()):
        return self.conn.execute(query, params).fetchall()

    def now(self) -> str:
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    def today(self) -> str:
        return datetime.utcnow().strftime("%Y-%m-%d")

    def _get_or_create_referrer(self, code: Optional[str]):
        if not code:
            return None
        return self.fetchone("SELECT * FROM users WHERE referral_code = ?", (code.strip(),))

    def get_user_by_telegram_id(self, telegram_id: int):
        return self.fetchone("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))

    def create_or_get_user(self, tg_user, referral_code: Optional[str] = None):
        existing = self.get_user_by_telegram_id(tg_user.id)
        if existing:
            self.touch_user(tg_user.id, tg_user.full_name, tg_user.username)
            return self.get_user_by_telegram_id(tg_user.id), False

        created_at = self.now()
        own_code = f"AR{tg_user.id}"
        referrer = self._get_or_create_referrer(referral_code)
        invited_by = referrer["id"] if referrer and referrer["telegram_id"] != tg_user.id else None

        self.execute(
            """
            INSERT INTO users (
                telegram_id, full_name, username, referral_code, invited_by,
                created_at, last_active_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tg_user.id,
                tg_user.full_name,
                tg_user.username,
                own_code,
                invited_by,
                created_at,
                created_at,
            ),
        )
        user = self.get_user_by_telegram_id(tg_user.id)

        if invited_by:
            self.execute(
                """
                UPDATE users
                SET referral_count = referral_count + 1,
                    balance = balance + ?,
                    total_earned = total_earned + ?
                WHERE id = ?
                """,
                (config.referral_bonus, config.referral_bonus, invited_by),
            )
        return user, True

    def touch_user(self, telegram_id: int, full_name: str | None = None, username: str | None = None):
        self.execute(
            """
            UPDATE users
            SET full_name = COALESCE(?, full_name),
                username = COALESCE(?, username),
                last_active_at = ?
            WHERE telegram_id = ?
            """,
            (full_name, username, self.now(), telegram_id),
        )

    def get_force_join_channels(self):
        rows = self.fetchall(
            "SELECT * FROM channels WHERE is_force_join = 1 AND is_active = 1 ORDER BY id ASC"
        )
        return [dict(r) for r in rows]

    def get_task_channels(self):
        rows = self.fetchall(
            "SELECT * FROM channels WHERE is_task_channel = 1 AND is_active = 1 ORDER BY id ASC"
        )
        return [dict(r) for r in rows]

    def add_channel(self, title: str, username: str, invite_link: str, channel_type: str):
        username = username.strip()
        if not username.startswith("@") and not username.startswith("-100"):
            username = f"@{username}"
        is_force = 1 if channel_type == "force" else 0
        is_task = 1 if channel_type == "task" else 0
        existing = self.fetchone("SELECT * FROM channels WHERE username = ?", (username,))
        if existing:
            self.execute(
                """
                UPDATE channels
                SET title = ?, invite_link = ?, is_force_join = ?, is_task_channel = ?, is_active = 1
                WHERE id = ?
                """,
                (title, invite_link, is_force, is_task, existing["id"]),
            )
            return existing["id"]
        cur = self.execute(
            """
            INSERT INTO channels (title, username, invite_link, is_force_join, is_task_channel, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, 1, ?)
            """,
            (title, username, invite_link, is_force, is_task, self.now()),
        )
        return cur.lastrowid

    def add_task(self, channel_id: int, title: str, description: str, reward: int):
        active_count = self.fetchone(
            "SELECT COUNT(*) AS total FROM channel_tasks WHERE is_active = 1"
        )["total"]
        if active_count >= config.max_active_tasks:
            raise ValueError("የተፈቀደው ከፍተኛ የንቁ ተግባር ብዛት 5 ነው።")
        cur = self.execute(
            """
            INSERT INTO channel_tasks (channel_id, title, description, reward_points, is_active, created_at)
            VALUES (?, ?, ?, ?, 1, ?)
            """,
            (channel_id, title, description, reward, self.now()),
        )
        return cur.lastrowid

    def get_active_tasks(self):
        rows = self.fetchall(
            """
            SELECT t.*, c.title AS channel_title, c.username, c.invite_link
            FROM channel_tasks t
            JOIN channels c ON c.id = t.channel_id
            WHERE t.is_active = 1 AND c.is_active = 1
            ORDER BY t.id ASC
            LIMIT ?
            """,
            (config.max_active_tasks,),
        )
        return [dict(r) for r in rows]

    def get_task(self, task_id: int):
        row = self.fetchone(
            """
            SELECT t.*, c.title AS channel_title, c.username, c.invite_link
            FROM channel_tasks t
            JOIN channels c ON c.id = t.channel_id
            WHERE t.id = ?
            """,
            (task_id,),
        )
        return dict(row) if row else None

    def has_completed_task(self, user_id: int, task_id: int) -> bool:
        row = self.fetchone(
            "SELECT 1 FROM task_completions WHERE user_id = ? AND task_id = ?",
            (user_id, task_id),
        )
        return bool(row)

    def complete_task(self, user_id: int, task_id: int):
        task = self.get_task(task_id)
        if not task:
            raise ValueError("ተግባሩ አልተገኘም።")
        if self.has_completed_task(user_id, task_id):
            return False, task["reward_points"]
        self.execute(
            """
            INSERT INTO task_completions (user_id, task_id, reward_points, completed_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, task_id, task["reward_points"], self.now()),
        )
        self.execute(
            """
            UPDATE users
            SET balance = balance + ?, total_earned = total_earned + ?, tasks_completed = tasks_completed + 1
            WHERE id = ?
            """,
            (task["reward_points"], task["reward_points"], user_id),
        )
        return True, task["reward_points"]

    def claim_daily_bonus(self, user_id: int):
        user = self.fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
        today = datetime.utcnow().date()
        last_bonus_date = None
        if user["last_bonus_date"]:
            last_bonus_date = datetime.strptime(user["last_bonus_date"], "%Y-%m-%d").date()
        if last_bonus_date == today:
            return False, 0, user["daily_streak"]

        if last_bonus_date == today - timedelta(days=1):
            streak = user["daily_streak"] + 1
        else:
            streak = 1
        reward = config.daily_rewards[min(streak, len(config.daily_rewards)) - 1]
        self.execute(
            """
            UPDATE users
            SET balance = balance + ?, total_earned = total_earned + ?, daily_streak = ?, last_bonus_date = ?
            WHERE id = ?
            """,
            (reward, reward, streak, today.strftime("%Y-%m-%d"), user_id),
        )
        self.execute(
            """
            INSERT INTO daily_bonus_claims (user_id, streak_day, reward_points, claimed_date, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, streak, reward, today.strftime("%Y-%m-%d"), self.now()),
        )
        return True, reward, streak

    def create_withdrawal(self, user_id: int, method: str, amount: int, account_details: str):
        user = self.fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
        if not user:
            raise ValueError("ተጠቃሚ አልተገኘም።")
        if amount < config.min_withdrawal:
            raise ValueError(f"ከ {config.min_withdrawal} ብር በታች ማውጣት አይቻልም።")
        if user["balance"] < amount:
            raise ValueError("በቂ ባላንስ የለም።")
        self.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (amount, user_id))
        cur = self.execute(
            """
            INSERT INTO withdrawals (user_id, method, amount, account_details, status, created_at)
            VALUES (?, ?, ?, ?, 'pending', ?)
            """,
            (user_id, method, amount, account_details, self.now()),
        )
        return cur.lastrowid

    def get_pending_withdrawals(self):
        rows = self.fetchall(
            """
            SELECT w.*, u.telegram_id, u.full_name, u.username
            FROM withdrawals w
            JOIN users u ON u.id = w.user_id
            WHERE w.status = 'pending'
            ORDER BY w.id ASC
            """
        )
        return [dict(r) for r in rows]

    def approve_withdrawal(self, withdrawal_id: int):
        row = self.fetchone("SELECT * FROM withdrawals WHERE id = ?", (withdrawal_id,))
        if not row or row["status"] != "pending":
            return None
        self.execute(
            "UPDATE withdrawals SET status = 'approved', processed_at = ? WHERE id = ?",
            (self.now(), withdrawal_id),
        )
        self.execute(
            "UPDATE users SET total_withdrawn = total_withdrawn + ? WHERE id = ?",
            (row["amount"], row["user_id"]),
        )
        return dict(self.fetchone("SELECT * FROM withdrawals WHERE id = ?", (withdrawal_id,)))

    def reject_withdrawal(self, withdrawal_id: int):
        row = self.fetchone("SELECT * FROM withdrawals WHERE id = ?", (withdrawal_id,))
        if not row or row["status"] != "pending":
            return None
        self.execute(
            "UPDATE withdrawals SET status = 'rejected', processed_at = ? WHERE id = ?",
            (self.now(), withdrawal_id),
        )
        self.execute(
            "UPDATE users SET balance = balance + ? WHERE id = ?",
            (row["amount"], row["user_id"]),
        )
        return dict(self.fetchone("SELECT * FROM withdrawals WHERE id = ?", (withdrawal_id,)))

    def create_giveaway(self, title: str, description: str, reward_text: str, winner_count: int, end_at: str, created_by: int | None):
        cur = self.execute(
            """
            INSERT INTO giveaways (title, description, reward_text, winner_count, end_at, is_active, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (title, description, reward_text, winner_count, end_at, created_by, self.now()),
        )
        return cur.lastrowid

    def get_active_giveaways(self):
        rows = self.fetchall(
            """
            SELECT g.*, COUNT(ge.id) AS total_entries
            FROM giveaways g
            LEFT JOIN giveaway_entries ge ON ge.giveaway_id = g.id
            WHERE g.is_active = 1
            GROUP BY g.id
            ORDER BY g.id DESC
            """
        )
        return [dict(r) for r in rows]

    def join_giveaway(self, giveaway_id: int, user_id: int):
        existing = self.fetchone(
            "SELECT 1 FROM giveaway_entries WHERE giveaway_id = ? AND user_id = ?",
            (giveaway_id, user_id),
        )
        if existing:
            return False
        self.execute(
            "INSERT INTO giveaway_entries (giveaway_id, user_id, joined_at) VALUES (?, ?, ?)",
            (giveaway_id, user_id, self.now()),
        )
        self.execute(
            "UPDATE users SET giveaways_joined = giveaways_joined + 1 WHERE id = ?",
            (user_id,),
        )
        return True

    def total_active_tasks(self) -> int:
        row = self.fetchone("SELECT COUNT(*) AS total FROM channel_tasks WHERE is_active = 1")
        return row["total"]

    def completed_tasks_count(self, user_id: int) -> int:
        row = self.fetchone("SELECT COUNT(*) AS total FROM task_completions WHERE user_id = ?", (user_id,))
        return row["total"]

    def get_leaderboard(self, category: str):
        column_map = {
            "balance": "balance",
            "referrals": "referral_count",
            "streak": "daily_streak",
            "tasks": "tasks_completed",
        }
        column = column_map.get(category, "balance")
        rows = self.fetchall(
            f"SELECT full_name, username, {column} AS score FROM users ORDER BY {column} DESC, id ASC LIMIT 10"
        )
        return [dict(r) for r in rows]

    def get_stats(self):
        users = self.fetchone("SELECT COUNT(*) AS total FROM users")["total"]
        giveaways = self.fetchone("SELECT COUNT(*) AS total FROM giveaways")["total"]
        tasks = self.fetchone("SELECT COUNT(*) AS total FROM channel_tasks WHERE is_active = 1")["total"]
        withdrawals = self.fetchone(
            "SELECT COUNT(*) AS total FROM withdrawals WHERE status = 'pending'"
        )["total"]
        return {
            "users": users,
            "giveaways": giveaways,
            "tasks": tasks,
            "pending_withdrawals": withdrawals,
        }

    def all_users(self):
        return [dict(r) for r in self.fetchall("SELECT * FROM users ORDER BY id ASC")]

