"""Pure-Python helpers used by project_task — no Odoo imports.

Kept separate so they can be unit-tested without an Odoo environment.
"""

from __future__ import annotations

import json


def parse_ai_priority_response(response: str | None) -> tuple[int | None, str | None]:
    """Defensive parse of the JSON returned by the ``task_priority`` template.

    Expected shape: ``{"ranking": [{"id": "...", "score": 0-100, "reason": "..."}]}``.

    Returns ``(score, reason)`` — both can be ``None`` if the response is
    missing, malformed, or shaped unexpectedly. ``score`` is always clamped
    to ``[0, 100]`` when not ``None``. Never raises.
    """
    if not response:
        return None, None
    try:
        data = json.loads(response)
    except (TypeError, ValueError):
        return None, None
    ranking = data.get("ranking") if isinstance(data, dict) else None
    if not ranking or not isinstance(ranking, list):
        return None, None
    first = ranking[0]
    if not isinstance(first, dict):
        return None, None
    score = first.get("score")
    reason = first.get("reason")
    try:
        score = int(score) if score is not None else None
    except (TypeError, ValueError):
        score = None
    if score is not None:
        score = max(0, min(100, score))
    return score, (str(reason) if reason else None)
