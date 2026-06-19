from export_sun_city_bias_phone import budget_summary, move_in_cost_summary


def test_move_in_cost_summary_combines_fee_and_deposit():
    row = {"application_fee": "$25", "deposit": "$200"}
    assert move_in_cost_summary(row) == "Application fee: $25; Deposit: $200"


def test_move_in_cost_summary_handles_unknowns():
    row = {"application_fee": "NOT FOUND / NEEDS CALL", "deposit": "NOT FOUND / NEEDS CALL"}
    assert move_in_cost_summary(row) == "NOT FOUND / NEEDS CALL"


def test_budget_summary_compares_values():
    assert budget_summary(1025.0, 900.0) == "At or under budget"
    assert budget_summary(525.0, 760.0) == "Above budget"
    assert budget_summary(525.0, None) == "Rent not published"
