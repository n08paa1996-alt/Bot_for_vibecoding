from aiogram.fsm.state import State, StatesGroup


class DeployStates(StatesGroup):
    choosing_type = State()
    waiting_code = State()
    showing_recommendation = State()


class AuditStates(StatesGroup):
    waiting_code = State()
