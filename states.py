from aiogram.fsm.state import State, StatesGroup

class AddChannelStates(StatesGroup):
    link = State()
    topic = State()
    subscribers = State()
    views = State()
    price = State()
    er = State()
    comment = State()

class AddClientStates(StatesGroup):
    username = State()
    topic = State()
    budget = State()
    comment = State()

class ComplaintStates(StatesGroup):
    reason = State()