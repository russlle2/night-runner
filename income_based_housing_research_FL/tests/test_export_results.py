import pandas as pd

from export_results import EXPORT_COLUMNS, summary_sections


def test_summary_sections_mentions_best_options():
    df = pd.DataFrame(
        [
            {
                "property_name": "Wildwood Commons",
                "city": "Wildwood",
                "program_type": "Unknown affordable rental",
                "phone": "(352) 748-0047",
                "vacancy_likelihood_score": 3,
                "confidence_score": 60,
                "rent_type": "income-based",
                "exact_published_rent_by_bedroom": "NOT FOUND",
                "property_type": "Family",
                "population_served": "family",
                "waitlist_status": "open",
                "vacancy_status": "waitlist_only",
                "source_quality": "government",
                "required_documents": "government-issued ID; proof of income",
                "vacancy_likelihood_reason": "Open waitlist shown.",
            }
        ]
    )
    for column in EXPORT_COLUMNS:
        if column not in df.columns:
            df[column] = ""
    summary = summary_sections(df)
    assert "Best options to call first" in summary
    assert "Wildwood Commons" in summary
