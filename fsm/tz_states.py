from aiogram.fsm.state import State, StatesGroup


class TZStates(StatesGroup):
    goal = State()
    audience = State()
    features = State()
    tech_constraints = State()
    desired_result = State()
    confirming = State()
