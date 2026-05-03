import json
import re
from pathlib import Path


_kb: dict = {}
_KB_PATH = Path("data/claude_knowledge.json")


def load() -> None:
    global _kb
    with open(_KB_PATH, encoding="utf-8") as f:
        _kb = json.load(f)


def reload() -> None:
    load()


def search(query: str) -> str | None:
    if not _kb:
        load()

    q = query.lower().strip()

    for cmd in _kb.get("commands", []):
        name = cmd["name"].lower().lstrip("/")
        aliases = [a.lower() for a in cmd.get("aliases", [])]
        if name in q or any(alias in q for alias in aliases):
            effort = ""
            return (
                f"*{cmd['name']}*\n\n"
                f"{cmd['description']}\n\n"
                f"📌 *Когда использовать:* {cmd['when_to_use']}\n\n"
                f"💡 *Пример:* `{cmd.get('example', '')}`"
            )

    effort = _kb.get("effort_levels", {})
    for level in ("low", "medium", "high"):
        keywords = [level, effort.get(level, {}).get("label", "").lower()]
        if any(k in q for k in keywords if k):
            lvl = effort[level]
            return (
                f"*Effort {level} — {lvl['label']}*\n\n"
                f"{lvl['description']}\n\n"
                f"⚡ Скорость: {lvl['speed']}\n"
                f"✅ Подходит для: {lvl['use_for']}"
            )

    if any(w in q for w in ["лимит", "токен", "контекст", "200к", "200000", "8192", "8к"]):
        limits = _kb.get("limits", {})
        return (
            f"*Лимиты Claude Code*\n\n"
            f"📦 Контекст: *{limits.get('context_tokens', 0):,}* токенов\n"
            f"📤 Один ответ: *{limits.get('output_tokens', 0):,}* токенов\n\n"
            f"{limits.get('description', '')}"
        )

    for faq in _kb.get("faq", []):
        if _fuzzy_match(q, faq["question"]):
            return faq["answer"]

    tips = _kb.get("tips", [])
    matched_tips = [t for t in tips if _fuzzy_match(q, t.lower())]
    if matched_tips:
        return "💡 " + "\n\n💡 ".join(matched_tips[:2])

    return None


def get_all_commands() -> list[dict]:
    if not _kb:
        load()
    return _kb.get("commands", [])


def get_tips() -> list[str]:
    if not _kb:
        load()
    return _kb.get("tips", [])


def get_limits() -> dict:
    if not _kb:
        load()
    return _kb.get("limits", {})


def get_effort_levels() -> dict:
    if not _kb:
        load()
    return _kb.get("effort_levels", {})


def _fuzzy_match(query: str, text: str) -> bool:
    words = re.findall(r"\w+", query)
    significant = [w for w in words if len(w) > 3]
    if not significant:
        return False
    matches = sum(1 for w in significant if w in text)
    return matches >= max(1, len(significant) // 2)
