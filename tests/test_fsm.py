import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fsm.tz_states import TZStates
from fsm.deploy_states import DeployStates, AuditStates
from models.schemas import TZData


def test_tz_states_exist():
    assert TZStates.goal
    assert TZStates.audience
    assert TZStates.features
    assert TZStates.tech_constraints
    assert TZStates.desired_result
    assert TZStates.confirming


def test_deploy_states_exist():
    assert DeployStates.choosing_type
    assert DeployStates.waiting_code
    assert DeployStates.showing_recommendation
    assert AuditStates.waiting_code


def test_tz_data_model():
    data = TZData(
        goal="Телеграм-бот для трекинга расходов",
        audience="Фрилансеры и соло-предприниматели",
        features="добавить расход, отчёт, экспорт",
        tech_constraints="Python, Railway",
        desired_result="Рабочий MVP",
    )
    assert data.goal == "Телеграм-бот для трекинга расходов"
    assert data.audience == "Фрилансеры и соло-предприниматели"


def test_tz_data_defaults():
    data = TZData(
        goal="Тест",
        audience="Все",
        features="фича",
        tech_constraints="нет",
        desired_result="MVP",
    )
    assert isinstance(data, TZData)


def test_progress_bar_format():
    from handlers.tz_wizard import _progress_bar
    bar = _progress_bar(1)
    assert "20%" in bar
    bar5 = _progress_bar(5)
    assert "100%" in bar5


def test_step_message_contains_header():
    from handlers.tz_wizard import _step_message
    msg = _step_message(0)
    assert "1/5" in msg


def test_back_button_none_for_first_step():
    from handlers.tz_wizard import _back_button
    assert _back_button(0) is None


def test_back_button_exists_for_later_steps():
    from handlers.tz_wizard import _back_button
    kb = _back_button(2)
    assert kb is not None
