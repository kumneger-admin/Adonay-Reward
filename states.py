from aiogram.fsm.state import State, StatesGroup


class WithdrawalStates(StatesGroup):
    amount = State()
    details = State()


class AddChannelStates(StatesGroup):
    title = State()
    username = State()
    invite_link = State()
    channel_type = State()


class AddTaskStates(StatesGroup):
    channel_id = State()
    title = State()
    description = State()
    reward = State()


class GiveawayStates(StatesGroup):
    title = State()
    description = State()
    reward_text = State()
    winner_count = State()
    end_at = State()


class BroadcastStates(StatesGroup):
    text = State()

