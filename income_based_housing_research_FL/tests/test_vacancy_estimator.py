from utils.scoring_utils import infer_vacancy_from_text


def test_vacancy_score_available_now():
    score, reason, waitlist, vacancy = infer_vacancy_from_text("Now leasing affordable apartments with units available now.")
    assert score == 4
    assert waitlist == "open"
    assert vacancy == "available_now"


def test_vacancy_score_waitlist_closed():
    score, reason, waitlist, vacancy = infer_vacancy_from_text("The waitlist is closed and the property is not accepting applications.")
    assert score == 0
    assert waitlist == "closed"
    assert vacancy == "no_vacancy"
