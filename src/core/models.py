"""
Data models for Job Hunter.
"""

from typing import List, Optional, Dict
from enum import Enum
from pydantic import BaseModel, Field

class ATSPlatform(str, Enum):
    ASHBY = "ashby"
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    WORKABLE = "workable"
    OTHER = "other"

class PersonalInfo(BaseModel):
    full_name: str = Field(..., description="Candidate full name")
    email: str = Field(..., description="Candidate email address")
    phone: str = Field(..., description="Candidate phone number with country code")
    location: str = Field(..., description="City and Country or Remote base")
    linkedin_url: str = Field(..., description="LinkedIn profile URL")
    github_url: Optional[str] = Field(None, description="GitHub profile URL")
    portfolio_url: Optional[str] = Field(None, description="Personal portfolio or website URL")
    current_company: Optional[str] = Field(None, description="Current employer or 'Freelance'")
    years_of_experience: Optional[int] = Field(None, description="Total years of professional experience")
    requires_us_visa_sponsorship: str = Field("No", description="'Yes' or 'No'")
    gender: Optional[str] = Field(None, description="Gender (e.g. 'Male', 'Female', 'Decline to self-identify')")
    race: Optional[str] = Field(None, description="Race / Ethnicity (e.g. 'Decline to self-identify')")
    veteran_status: Optional[str] = Field(None, description="Veteran status")
    disability_status: Optional[str] = Field(None, description="Disability status")

    @property
    def first_name(self) -> str:
        return self.full_name.strip().split()[0] if self.full_name and self.full_name.strip() else ""

    @property
    def last_name(self) -> str:
        parts = self.full_name.strip().split() if self.full_name else []
        return " ".join(parts[1:]) if len(parts) > 1 else ""

    @property
    def city(self) -> str:
        if not self.location:
            return ""
        return self.location.split(",")[0].strip()

    @property
    def country(self) -> str:
        if not self.location:
            return ""
        parts = self.location.split(",")
        return parts[-1].strip() if len(parts) > 1 else self.location.strip()

class SearchCriteria(BaseModel):
    target_roles: List[str] = Field(default_factory=list, description="Target job titles / roles")
    keywords: List[str] = Field(default_factory=list, description="Technical skill keywords")
    location_keywords: List[str] = Field(
        default_factory=lambda: ["remote", "latam", "worldwide", "global", "anywhere"],
        description="Location filtering keywords"
    )
    max_years_of_experience: Optional[int] = Field(
        None,
        description="Maximum years of experience required by a job posting (defaults to personal_info.years_of_experience)"
    )
    min_salary_usd: Optional[int] = Field(None, description="Minimum target compensation")

class ATSSettings(BaseModel):
    enabled_platforms: List[str] = Field(
        default_factory=lambda: ["ashby", "greenhouse", "lever"],
        description="Active ATS scanners"
    )
    auto_upload_resume: bool = True
    stealth_mode: bool = True

class CandidatePreferences(BaseModel):
    dependent_salary_usd: Optional[int] = Field(
        None,
        description="Expected salary as a dependent employee (default when posting does not specify contractor)"
    )
    contractor_salary_usd: Optional[int] = Field(
        None,
        description="Expected salary for B2B / independent contractor roles"
    )
    desired_salary_usd: Optional[int] = Field(
        None,
        description="Fallback expected compensation in USD if dependent/contractor are not set separately"
    )
    salary_period: str = Field("monthly", description="'monthly' or 'annual'")
    notice_period: str = Field("2 weeks", description="e.g. 'Immediately', '2 weeks', '1 month'")
    english_level: Optional[str] = Field("Fluent / Professional", description="e.g. 'B2', 'Fluent', 'Native'")
    legally_authorized_to_work: str = Field("Yes", description="'Yes' or 'No'")

    def get_salary_value(self, is_contractor: bool = False) -> Optional[int]:
        """
        Return the appropriate salary amount based on contract modality.
        If is_contractor is True, prefers contractor_salary_usd.
        Otherwise defaults to dependent_salary_usd (with fallback to desired_salary_usd).
        """
        if is_contractor and self.contractor_salary_usd:
            return self.contractor_salary_usd
        if self.dependent_salary_usd:
            return self.dependent_salary_usd
        if self.desired_salary_usd:
            return self.desired_salary_usd
        return self.contractor_salary_usd

    def get_formatted_salary(self, is_contractor: bool = False) -> str:
        val = self.get_salary_value(is_contractor=is_contractor)
        if not val:
            return ""
        period_str = "/ month" if self.salary_period.lower() == "monthly" else "/ year"
        return f"${val:,} USD {period_str}"

    @property
    def formatted_salary(self) -> str:
        return self.get_formatted_salary(is_contractor=False)

class OpenQuestionTemplates(BaseModel):
    motivation: Optional[str] = Field(
        None,
        description="General motivation answer (Why do you want to work here / Why this role)"
    )
    experience_summary: Optional[str] = Field(
        None,
        description="Summary of background and daily technical stack"
    )
    key_project: Optional[str] = Field(
        None,
        description="Proudest project or technical challenge solved"
    )
    timezone_overlap: Optional[str] = Field(
        None,
        description="Time zone and overlap statement"
    )
    education_level: Optional[str] = Field(
        None,
        description="Highest level of education completed or current degree"
    )
    additional_info: Optional[str] = Field(
        None,
        description="Additional information or cover letter notes"
    )
    fintech_motivation: Optional[str] = Field(
        None,
        description="Legacy fallback motivation answer for fintech"
    )
    metrics_and_kpis: Optional[str] = Field(
        None,
        description="Legacy fallback targets and KPIs"
    )
    custom_qa: Dict[str, str] = Field(
        default_factory=dict,
        description="Key-value pairs of common question keywords and tailored answers"
    )

class CandidateProfile(BaseModel):
    personal_info: PersonalInfo
    search_criteria: SearchCriteria
    preferences: CandidatePreferences = Field(default_factory=CandidatePreferences)
    ats_settings: ATSSettings = Field(default_factory=ATSSettings)
    open_questions: OpenQuestionTemplates = Field(default_factory=OpenQuestionTemplates)

    @property
    def effective_max_years(self) -> Optional[int]:
        """Return max years of experience filter from search_criteria or personal_info."""
        if self.search_criteria.max_years_of_experience is not None:
            return self.search_criteria.max_years_of_experience
        return self.personal_info.years_of_experience

class JobPosting(BaseModel):
    ats: ATSPlatform
    company: str
    title: str
    location: str
    url: str
    match_score: Optional[int] = None
    compensation: Optional[str] = None
    required_years: Optional[int] = None
    created_at: Optional[str] = None
    has_captcha: bool = False
