from export_general_rentals_under_1000_phone import budget_fit, monthly_budget


def test_monthly_budget_uses_thirty_percent_rule():
    assert monthly_budget(21000) == 525
    assert monthly_budget(41000) == 1025


def test_budget_fit_labels_correctly():
    assert budget_fit(700, 1025) == "At or under budget"
    assert budget_fit(700, 525) == "Above budget"
