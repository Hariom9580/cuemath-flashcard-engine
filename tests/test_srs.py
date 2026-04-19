from datetime import date

from app.srs import calculate_sm2_update


def test_sm2_initial_success():
    update = calculate_sm2_update(
        repetitions=0,
        interval_days=0,
        ease_factor=2.5,
        score=4,
        review_date=date(2026, 4, 19),
    )
    assert update["repetitions"] == 1
    assert update["interval_days"] == 1
    assert update["next_review_at"] == "2026-04-20"
    assert update["ease_factor"] >= 2.4


def test_sm2_second_success_interval_growth():
    update = calculate_sm2_update(
        repetitions=1,
        interval_days=1,
        ease_factor=2.5,
        score=5,
        review_date=date(2026, 4, 19),
    )
    assert update["repetitions"] == 2
    assert update["interval_days"] == 6
    assert update["next_review_at"] == "2026-04-25"


def test_sm2_reset_on_failure():
    update = calculate_sm2_update(
        repetitions=3,
        interval_days=10,
        ease_factor=2.4,
        score=1,
        review_date=date(2026, 4, 19),
    )
    assert update["repetitions"] == 0
    assert update["interval_days"] == 1
    assert update["next_review_at"] == "2026-04-20"
    assert update["ease_factor"] >= 1.3
