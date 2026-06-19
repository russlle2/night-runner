from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

SourceQuality = Literal[
    "official_property_site",
    "government",
    "housing_authority",
    "HUD/USDA/FHFC",
    "apartment_listing",
    "nonprofit_directory",
    "unknown",
]
WaitlistStatus = Literal["open", "closed", "unknown", "call_required"]
VacancyStatus = Literal["available_now", "waitlist_only", "no_vacancy", "unknown", "call_required"]
RentType = Literal["income-based", "fixed affordable rent", "max LIHTC rent", "market + vouchers accepted", "unknown"]


class DiscoveredUrlRecord(BaseModel):
    url: str
    title: str = ""
    snippet: str = ""
    discovery_method: str
    query: str = ""
    city: str = ""
    county: str = ""
    source_quality: SourceQuality = "unknown"
    source_category: str = ""


class SnippetRecord(BaseModel):
    source_url: str
    source_title: str = ""
    candidate_property_name: str = ""
    source_quality: SourceQuality = "unknown"
    city_hint: str = ""
    county_hint: str = ""
    contact_phone: str = ""
    email: str = ""
    address: str = ""
    management_company_hint: str = ""
    website_url: str = ""
    snippet_type: str
    snippet_text: str
    raw_html_path: str = ""
    screenshot_path: str = ""
    last_updated_date_from_source: str = ""


class EvidenceRecord(BaseModel):
    source_url: str
    source_quality: SourceQuality = "unknown"
    confirmed_fields: list[str] = Field(default_factory=list)
    snippet: str = ""
    raw_html_path: str = ""
    screenshot_path: str = ""
    notes: str = ""


class PhoneVerificationRecord(BaseModel):
    property_name: str
    phone: str = ""
    date_called: str = ""
    person_spoken_to: str = ""
    vacancy_status: str = ""
    waitlist_status: str = ""
    rent_details: str = ""
    documents_needed: str = ""
    next_step: str = ""
    notes: str = ""


class HousingProperty(BaseModel):
    property_name: str
    property_type: str = "Unknown"
    address: str = "NOT FOUND / NEEDS CALL"
    city: str = "Unknown"
    county: str = "Unknown"
    state: str = "FL"
    zip: str = ""
    phone: str = ""
    email: str = ""
    website_url: str = ""
    management_company: str = ""
    management_company_phone: str = ""
    housing_authority_or_agency: str = ""
    source_urls: list[str] = Field(default_factory=list)
    source_quality: SourceQuality = "unknown"
    bedroom_sizes: str = ""
    unit_count: str = ""
    population_served: str = ""
    program_type: str = "Unknown"
    rent_type: RentType = "unknown"
    exact_published_rent_by_bedroom: str = "NOT FOUND"
    exact_published_rent_by_income_bracket: str = "NOT FOUND"
    income_limits_by_household_size: str = "NOT FOUND"
    AMI_brackets_supported: str = "NOT FOUND"
    application_fee: str = "NOT FOUND / NEEDS CALL"
    deposit: str = "NOT FOUND / NEEDS CALL"
    utilities_included: str = "NOT FOUND / NEEDS CALL"
    pet_policy: str = "NOT FOUND / NEEDS CALL"
    criminal_background_policy: str = "NOT FOUND / NEEDS CALL"
    credit_policy: str = "NOT FOUND / NEEDS CALL"
    eviction_policy: str = "NOT FOUND / NEEDS CALL"
    minimum_income_requirement: str = "NOT FOUND / NEEDS CALL"
    maximum_income_requirement: str = "NOT FOUND / NEEDS CALL"
    required_documents: str = "NOT FOUND / NEEDS CALL"
    application_method: str = "call office"
    application_url: str = ""
    waitlist_status: WaitlistStatus = "call_required"
    vacancy_status: VacancyStatus = "call_required"
    last_updated_date_from_source: str = ""
    vacancy_likelihood_score: int = 2
    vacancy_likelihood_reason: str = "No reliable online vacancy evidence located; property verification is required."
    phone_verification_needed: bool = True
    notes: str = ""
    confidence_score: int = 35
    distance_miles_to_target_area: float | None = None
    evidence: list[EvidenceRecord] = Field(default_factory=list)
    evidence_snippets: list[str] = Field(default_factory=list)
    discovered_from: list[str] = Field(default_factory=list)

    @field_validator("source_urls")
    @classmethod
    def ensure_unique_urls(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys([item for item in value if item]))

    @field_validator("vacancy_likelihood_score")
    @classmethod
    def validate_vacancy_score(cls, value: int) -> int:
        if not 0 <= value <= 4:
            raise ValueError("vacancy_likelihood_score must be between 0 and 4")
        return value

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence_score(cls, value: int) -> int:
        if not 0 <= value <= 100:
            raise ValueError("confidence_score must be between 0 and 100")
        return value

    def add_source_url(self, url: str) -> None:
        if url and url not in self.source_urls:
            self.source_urls.append(url)

    def add_evidence(self, evidence: EvidenceRecord | dict[str, Any]) -> None:
        if isinstance(evidence, dict):
            evidence = EvidenceRecord(**evidence)
        self.evidence.append(evidence)
        if evidence.snippet:
            self.evidence_snippets.append(evidence.snippet)
        self.add_source_url(evidence.source_url)

    def export_dict(self) -> dict[str, Any]:
        payload = self.model_dump()
        payload["source_urls"] = "; ".join(self.source_urls)
        payload["evidence"] = [entry.model_dump() for entry in self.evidence]
        payload["evidence_snippets"] = " || ".join(self.evidence_snippets)
        payload["discovered_from"] = "; ".join(self.discovered_from)
        return payload
