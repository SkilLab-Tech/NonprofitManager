"""Unit tests for volunteer ↔ opportunity matching."""

from __future__ import annotations

from datetime import date, time, timedelta

import pytest

from utils.matching import (
    MatchScore,
    Opportunity,
    OpportunityWindow,
    Volunteer,
    VolunteerSlot,
    is_background_check_expiring_soon,
    rank_matches,
    score_match,
)


def vol(skill_ids=frozenset(), slots=(), bg_active=False, bg_expired=False):
    return Volunteer(
        skill_ids=frozenset(skill_ids),
        slots=tuple(slots),
        background_check_active=bg_active,
        background_check_expired=bg_expired,
    )


def opp(required_skills=frozenset(), windows=(), require_bg=False):
    return Opportunity(
        required_skill_ids=frozenset(required_skills),
        windows=tuple(windows),
        requires_background_check=require_bg,
    )


class TestSkillOverlap:
    def test_empty_requirement_qualifies_everyone(self):
        score = score_match(vol(skill_ids={1, 2}), opp())
        assert score.skill_pct == 100

    def test_no_volunteer_skills_zero_pct(self):
        score = score_match(vol(), opp(required_skills={1, 2}))
        assert score.skill_pct == 0

    def test_partial_overlap(self):
        score = score_match(vol(skill_ids={1, 2, 3}), opp(required_skills={1, 2, 4, 5}))
        # 2/4 required skills met = 50%
        assert score.skill_pct == 50

    def test_full_overlap(self):
        score = score_match(vol(skill_ids={1, 2, 3}), opp(required_skills={1, 2, 3}))
        assert score.skill_pct == 100

    def test_volunteer_has_extra_skills_doesnt_penalize(self):
        score = score_match(vol(skill_ids={1, 2, 3, 4, 5}), opp(required_skills={1, 2}))
        assert score.skill_pct == 100


class TestAvailabilityOverlap:
    def test_no_windows_required_passes(self):
        score = score_match(vol(slots=[VolunteerSlot(0, time(9), time(12))]), opp())
        assert score.availability_pct == 100

    def test_overlapping_window(self):
        score = score_match(
            vol(slots=[VolunteerSlot(2, time(9), time(12))]),
            opp(windows=[OpportunityWindow(2, time(10), time(11))]),
        )
        assert score.availability_pct == 100

    def test_same_weekday_disjoint_hours(self):
        score = score_match(
            vol(slots=[VolunteerSlot(2, time(9), time(11))]),
            opp(windows=[OpportunityWindow(2, time(14), time(16))]),
        )
        assert score.availability_pct == 50

    def test_different_weekday(self):
        score = score_match(
            vol(slots=[VolunteerSlot(0, time(9), time(12))]),
            opp(windows=[OpportunityWindow(3, time(10), time(11))]),
        )
        assert score.availability_pct == 0

    def test_no_volunteer_slots_when_required(self):
        score = score_match(
            vol(),
            opp(windows=[OpportunityWindow(0, time(9), time(12))]),
        )
        assert score.availability_pct == 0

    def test_first_overlapping_window_wins(self):
        # Multiple windows, volunteer overlaps one of them → 100
        score = score_match(
            vol(slots=[VolunteerSlot(0, time(9), time(12))]),
            opp(windows=[
                OpportunityWindow(5, time(9), time(12)),  # Saturday — vol not available
                OpportunityWindow(0, time(10), time(11)), # Monday — match
            ]),
        )
        assert score.availability_pct == 100


class TestBackgroundCheck:
    def test_not_required_always_100(self):
        score = score_match(vol(bg_active=False), opp(required_skills=frozenset()))
        assert score.bg_pct == 100

    def test_required_and_active_100(self):
        score = score_match(vol(bg_active=True, bg_expired=False), opp(require_bg=True))
        assert score.bg_pct == 100

    def test_required_and_expired_50(self):
        score = score_match(vol(bg_active=True, bg_expired=True), opp(require_bg=True))
        assert score.bg_pct == 50

    def test_required_and_missing_0(self):
        score = score_match(vol(bg_active=False), opp(require_bg=True))
        assert score.bg_pct == 0


class TestOverallScore:
    def test_overall_is_weighted_sum(self):
        # 100% skill, 100% avail, 100% bg → 100
        score = score_match(
            vol(skill_ids={1}, slots=[VolunteerSlot(0, time(9), time(12))], bg_active=True),
            opp(required_skills={1}, windows=[OpportunityWindow(0, time(10), time(11))], require_bg=True),
        )
        assert score.overall == 100

    def test_overall_clamped_to_range(self):
        # Even with weird input, overall stays [0, 100]
        for _ in range(10):
            score = score_match(vol(), opp())
            assert 0 <= score.overall <= 100

    def test_overall_with_partial_signals(self):
        # 50% skill, 100% avail, 100% bg = 60*0.5 + 30 + 10 = 70
        score = score_match(
            vol(skill_ids={1, 2}, slots=[VolunteerSlot(0, time(9), time(12))], bg_active=True),
            opp(
                required_skills={1, 2, 3, 4},
                windows=[OpportunityWindow(0, time(10), time(11))],
                require_bg=True,
            ),
        )
        assert score.overall == 70

    def test_reasons_populated_for_partial(self):
        score = score_match(vol(), opp(required_skills={1}))
        assert "no required skills met" in score.reasons
        assert score.skill_pct == 0


class TestRankMatches:
    def test_returns_sorted_desc(self):
        opp_ = opp(required_skills={1})
        vols = [
            vol(),                          # 0% skill
            vol(skill_ids={1}),             # 100% skill
            vol(skill_ids={1, 2}),          # 100% skill (same)
        ]
        ranked = rank_matches(vols, opp_)
        # First two should have higher score than third
        scores = [m.overall for _, m in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_preserves_original_indices(self):
        opp_ = opp()
        vols = [vol(), vol(), vol()]
        ranked = rank_matches(vols, opp_)
        indices = {idx for idx, _ in ranked}
        assert indices == {0, 1, 2}


class TestBackgroundCheckExpiringSoon:
    TODAY = date(2026, 5, 23)

    def test_none_returns_false(self):
        assert not is_background_check_expiring_soon(None, self.TODAY)

    def test_within_30_days(self):
        expiry = self.TODAY + timedelta(days=15)
        assert is_background_check_expiring_soon(expiry, self.TODAY)

    def test_today_is_expiring(self):
        assert is_background_check_expiring_soon(self.TODAY, self.TODAY)

    def test_already_expired_not_expiring_soon(self):
        # 'expiring soon' is for future expiry within window; already-expired
        # is a different state.
        expired = self.TODAY - timedelta(days=5)
        assert not is_background_check_expiring_soon(expired, self.TODAY)

    def test_far_future_not_expiring_soon(self):
        far = self.TODAY + timedelta(days=120)
        assert not is_background_check_expiring_soon(far, self.TODAY)

    def test_custom_warn_window(self):
        expiry = self.TODAY + timedelta(days=50)
        assert is_background_check_expiring_soon(expiry, self.TODAY, warn_within_days=60)
        assert not is_background_check_expiring_soon(expiry, self.TODAY, warn_within_days=30)
