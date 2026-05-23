"""Unit tests for the grant application pipeline state machine."""

from __future__ import annotations

import pytest

from utils.pipeline import (
    ACTIVE_STATES,
    PIPELINE_STATES,
    STATE_TRANSITIONS,
    TERMINAL_STATES,
    is_active,
    is_terminal,
    validate_transition,
)


class TestStateConstants:
    def test_all_states_listed(self):
        expected = {
            "prospect", "researching", "drafting", "submitted",
            "under_review", "awarded", "declined", "withdrawn",
        }
        assert set(PIPELINE_STATES) == expected

    def test_terminal_states(self):
        # The three terminal states must be exactly these.
        assert set(TERMINAL_STATES) == {"awarded", "declined", "withdrawn"}

    def test_active_is_complement(self):
        assert set(ACTIVE_STATES) | set(TERMINAL_STATES) == set(PIPELINE_STATES)
        assert not set(ACTIVE_STATES) & set(TERMINAL_STATES)

    def test_terminal_states_have_no_outgoing(self):
        for state in TERMINAL_STATES:
            assert STATE_TRANSITIONS[state] == ()

    def test_active_states_have_outgoing(self):
        for state in ACTIVE_STATES:
            assert len(STATE_TRANSITIONS[state]) > 0

    def test_withdrawn_is_reachable_from_all_active(self):
        for state in ACTIVE_STATES:
            assert "withdrawn" in STATE_TRANSITIONS[state], (
                f"{state} must allow withdrawal — it's a universal exit"
            )


class TestValidateTransition:
    @pytest.mark.parametrize("from_state,to_state", [
        ("prospect", "researching"),
        ("researching", "drafting"),
        ("drafting", "submitted"),
        ("submitted", "under_review"),
        ("under_review", "awarded"),
        ("under_review", "declined"),
        ("drafting", "researching"),  # bouncing back is legal from drafting
    ])
    def test_legal_transitions_pass(self, from_state, to_state):
        result = validate_transition(from_state, to_state)
        assert result.ok, result.reason

    @pytest.mark.parametrize("from_state,to_state", [
        ("prospect", "submitted"),       # skip steps
        ("prospect", "awarded"),         # cannot jump to terminal
        ("researching", "submitted"),    # must draft first
        ("submitted", "drafting"),       # cannot un-submit
        ("awarded", "researching"),      # terminal — no resurrect
        ("declined", "submitted"),       # terminal — no resurrect
        ("withdrawn", "prospect"),       # terminal — no resurrect
    ])
    def test_illegal_transitions_blocked(self, from_state, to_state):
        result = validate_transition(from_state, to_state)
        assert not result.ok
        assert result.reason  # has a descriptive message

    def test_self_transition_blocked(self):
        result = validate_transition("drafting", "drafting")
        assert not result.ok
        assert "already in state" in result.reason.lower()

    def test_unknown_source(self):
        result = validate_transition("invalid", "drafting")
        assert not result.ok
        assert "unknown source state" in result.reason.lower()

    def test_unknown_target(self):
        result = validate_transition("drafting", "invalid")
        assert not result.ok
        assert "unknown target state" in result.reason.lower()

    def test_universal_withdrawal(self):
        # Every active state allows withdrawal.
        for state in ACTIVE_STATES:
            result = validate_transition(state, "withdrawn")
            assert result.ok, f"withdrawing from {state} should be allowed"


class TestPredicates:
    def test_is_terminal(self):
        assert is_terminal("awarded")
        assert is_terminal("declined")
        assert is_terminal("withdrawn")
        assert not is_terminal("drafting")
        assert not is_terminal("prospect")

    def test_is_active(self):
        for s in ACTIVE_STATES:
            assert is_active(s)
        for s in TERMINAL_STATES:
            assert not is_active(s)
