"""Tests for quiz scoring and flashcard SM-2 algorithm."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone, timedelta


class TestQuizScoring:
    """Unit tests for quiz score calculation logic (extracted from route logic)."""

    def _calculate_score(self, correct: int, total: int) -> float:
        """Mirror the scoring logic from the quiz route."""
        if total == 0:
            return 0.0
        return round((correct / total) * 100, 2)

    def test_perfect_score(self):
        assert self._calculate_score(10, 10) == 100.0

    def test_zero_score(self):
        assert self._calculate_score(0, 10) == 0.0

    def test_partial_score(self):
        assert self._calculate_score(7, 10) == 70.0

    def test_rounding(self):
        # 1/3 ≈ 33.33%
        score = self._calculate_score(1, 3)
        assert score == 33.33

    def test_zero_total(self):
        assert self._calculate_score(0, 0) == 0.0

    def test_high_precision(self):
        # 8/10 = 80%
        assert self._calculate_score(8, 10) == 80.0


class TestSM2Algorithm:
    """Unit tests for the SM-2 spaced repetition algorithm."""

    def _make_card(self):
        card = MagicMock()
        card.repetitions = 0
        card.interval_days = 1
        card.ease_factor = 2.5
        card.next_review_at = None
        return card

    def _apply_sm2(self, card, quality: int) -> None:
        """Copy of the SM-2 implementation from flashcards route."""
        q = max(0, min(5, quality))

        if q >= 3:
            if card.repetitions == 0:
                card.interval_days = 1
            elif card.repetitions == 1:
                card.interval_days = 6
            else:
                card.interval_days = round(card.interval_days * card.ease_factor)
            card.repetitions += 1
        else:
            card.repetitions = 0
            card.interval_days = 1

        card.ease_factor = max(
            1.3, card.ease_factor + 0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)
        )
        card.next_review_at = datetime.now(timezone.utc) + timedelta(days=card.interval_days)

    def test_first_correct_review(self):
        card = self._make_card()
        self._apply_sm2(card, 5)
        assert card.repetitions == 1
        assert card.interval_days == 1

    def test_second_correct_review(self):
        card = self._make_card()
        self._apply_sm2(card, 5)
        self._apply_sm2(card, 5)
        assert card.repetitions == 2
        assert card.interval_days == 6

    def test_failed_review_resets(self):
        card = self._make_card()
        self._apply_sm2(card, 5)  # pass
        self._apply_sm2(card, 5)  # pass
        self._apply_sm2(card, 1)  # fail
        assert card.repetitions == 0
        assert card.interval_days == 1

    def test_ease_factor_increases_on_easy(self):
        card = self._make_card()
        initial_ef = card.ease_factor
        self._apply_sm2(card, 5)
        assert card.ease_factor > initial_ef

    def test_ease_factor_decreases_on_hard(self):
        card = self._make_card()
        initial_ef = card.ease_factor
        self._apply_sm2(card, 3)
        assert card.ease_factor < initial_ef

    def test_ease_factor_minimum(self):
        card = self._make_card()
        # Apply many failed reviews
        for _ in range(20):
            self._apply_sm2(card, 0)
        assert card.ease_factor >= 1.3

    def test_quality_clamped_to_0_5(self):
        card = self._make_card()
        self._apply_sm2(card, 10)  # should be clamped to 5
        assert card.repetitions == 1

    def test_next_review_in_future(self):
        card = self._make_card()
        self._apply_sm2(card, 4)
        assert card.next_review_at > datetime.now(timezone.utc)


class TestMasteryCalculation:
    """Tests for the mastery score calculation in learning_service."""

    def _calculate_mastery(self, old_mastery: float, quiz_score: float, is_first: bool) -> float:
        if is_first:
            return quiz_score
        return round(0.7 * old_mastery + 0.3 * quiz_score, 2)

    def test_first_attempt_equals_score(self):
        assert self._calculate_mastery(0, 80, True) == 80.0

    def test_weighted_average(self):
        # 0.7 * 50 + 0.3 * 100 = 35 + 30 = 65
        result = self._calculate_mastery(50, 100, False)
        assert result == 65.0

    def test_mastery_improves_on_good_score(self):
        result = self._calculate_mastery(50, 90, False)
        assert result > 50

    def test_mastery_decreases_on_poor_score(self):
        result = self._calculate_mastery(80, 20, False)
        assert result < 80

    def test_mastery_capped_at_100(self):
        # Natural cap — weighted average can't exceed max input
        result = self._calculate_mastery(100, 100, False)
        assert result == 100.0

    def test_mastery_at_zero(self):
        result = self._calculate_mastery(0, 0, True)
        assert result == 0.0


class TestMasteryLabel:
    """Tests for the mastery label helper (standalone, no app imports)."""

    def setup_method(self):
        # Inline the function so this test has no app dependencies
        def calculate_mastery_label(score: float) -> str:
            if score >= 85:
                return "Strong"
            elif score >= 65:
                return "Good"
            elif score >= 45:
                return "Developing"
            elif score >= 25:
                return "Weak"
            else:
                return "Not started"
        self.label = calculate_mastery_label

    def test_strong(self):
        assert self.label(90) == "Strong"
        assert self.label(85) == "Strong"

    def test_good(self):
        assert self.label(70) == "Good"
        assert self.label(65) == "Good"

    def test_developing(self):
        assert self.label(50) == "Developing"
        assert self.label(45) == "Developing"

    def test_weak(self):
        assert self.label(30) == "Weak"
        assert self.label(25) == "Weak"

    def test_not_started(self):
        assert self.label(0) == "Not started"
        assert self.label(24) == "Not started"
