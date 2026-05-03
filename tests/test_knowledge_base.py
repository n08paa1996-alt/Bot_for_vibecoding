import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import knowledge_base


def test_search_compact_command():
    result = knowledge_base.search("/compact")
    assert result is not None
    assert "compact" in result.lower()


def test_search_by_alias():
    result = knowledge_base.search("что делает compact?")
    assert result is not None


def test_search_plan_command():
    result = knowledge_base.search("/plan")
    assert result is not None
    assert "план" in result.lower() or "plan" in result.lower()


def test_search_limits():
    result = knowledge_base.search("лимит токенов")
    assert result is not None
    assert "200" in result


def test_search_effort_high():
    result = knowledge_base.search("effort high")
    assert result is not None
    assert "high" in result.lower()


def test_search_unknown_returns_none():
    result = knowledge_base.search("абракадабра блаблабла нетакогослова")
    assert result is None


def test_get_all_commands():
    commands = knowledge_base.get_all_commands()
    assert len(commands) >= 5
    names = [c["name"] for c in commands]
    assert "/compact" in names
    assert "/plan" in names
    assert "/init" in names


def test_get_tips():
    tips = knowledge_base.get_tips()
    assert len(tips) >= 5


def test_get_limits():
    limits = knowledge_base.get_limits()
    assert limits["context_tokens"] == 200000
    assert limits["output_tokens"] == 8192


def test_reload():
    knowledge_base.reload()
    result = knowledge_base.search("compact")
    assert result is not None
