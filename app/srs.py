from datetime import date, timedelta


def clamp_score(score: int) -> int:
    if score < 0:
        return 0
    if score > 5:
        return 5
    return score


def calculate_sm2_update(
    repetitions: int,
    interval_days: int,
    ease_factor: float,
    score: int,
    review_date: date | None = None,
) -> dict[str, int | float | str]:
    score = clamp_score(score)
    review_date = review_date or date.today()
    ease_factor = max(1.3, ease_factor)

    if score < 3:
        repetitions = 0
        interval_days = 1
    else:
        if repetitions == 0:
            interval_days = 1
        elif repetitions == 1:
            interval_days = 6
        else:
            interval_days = max(1, round(interval_days * ease_factor))
        repetitions += 1

    ease_factor = ease_factor + (
        0.1 - (5 - score) * (0.08 + (5 - score) * 0.02)
    )
    ease_factor = max(1.3, round(ease_factor, 2))

    next_review = review_date + timedelta(days=interval_days)
    return {
        "repetitions": repetitions,
        "interval_days": interval_days,
        "ease_factor": ease_factor,
        "next_review_at": next_review.isoformat(),
    }
