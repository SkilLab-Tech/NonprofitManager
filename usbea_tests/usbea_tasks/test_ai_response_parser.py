"""Unit tests for parse_ai_priority_response.

The parser is defensive — model output is untrusted; the parser must never
crash on malformed JSON or unexpected shapes. We import it directly from
the utils module so no Odoo stack is involved.
"""

from __future__ import annotations

import pytest

from utils.ai_parsing import parse_ai_priority_response as parse


class TestParseAIPriorityResponse:
    def test_empty_response_returns_none(self):
        assert parse("") == (None, None)
        assert parse(None) == (None, None)

    def test_malformed_json_returns_none(self):
        assert parse("not json") == (None, None)
        assert parse("{incomplete") == (None, None)

    def test_well_formed_response(self):
        response = '{"ranking": [{"id": "1", "score": 85, "reason": "deadline tomorrow"}]}'
        score, reason = parse(response)
        assert score == 85
        assert reason == "deadline tomorrow"

    def test_clamps_score_above_100(self):
        response = '{"ranking": [{"id": "1", "score": 250, "reason": "extreme"}]}'
        score, _ = parse(response)
        assert score == 100

    def test_clamps_score_below_0(self):
        response = '{"ranking": [{"id": "1", "score": -5, "reason": "x"}]}'
        score, _ = parse(response)
        assert score == 0

    def test_missing_score(self):
        response = '{"ranking": [{"id": "1", "reason": "no score"}]}'
        score, reason = parse(response)
        assert score is None
        assert reason == "no score"

    def test_empty_ranking_returns_none(self):
        assert parse('{"ranking": []}') == (None, None)

    def test_missing_ranking_key(self):
        assert parse('{"other_key": "value"}') == (None, None)

    def test_non_dict_top_level(self):
        assert parse('[1, 2, 3]') == (None, None)

    def test_non_int_score_coerced(self):
        response = '{"ranking": [{"score": "42", "reason": "r"}]}'
        score, _ = parse(response)
        assert score == 42

    def test_non_numeric_score_returns_none(self):
        response = '{"ranking": [{"score": "high", "reason": "r"}]}'
        score, reason = parse(response)
        assert score is None
        assert reason == "r"

    def test_first_ranking_used(self):
        response = (
            '{"ranking": ['
            '{"id":"1","score":50,"reason":"first"},'
            '{"id":"2","score":99,"reason":"second"}'
            ']}'
        )
        score, reason = parse(response)
        assert score == 50
        assert reason == "first"

    def test_string_reason_coerced(self):
        # Edge case: reason as a number should be coerced to string.
        response = '{"ranking": [{"score": 50, "reason": 42}]}'
        score, reason = parse(response)
        assert score == 50
        assert reason == "42"

    def test_none_reason_returns_none(self):
        response = '{"ranking": [{"score": 50}]}'
        score, reason = parse(response)
        assert score == 50
        assert reason is None
