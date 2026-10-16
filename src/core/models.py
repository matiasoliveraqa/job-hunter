"""
Data models for Job Hunter.
"""

from typing import List, Optional
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
    requires_us_visa_sponsorship: str = Field("No", description="'Yes' or 'No'")

    @property
    def first_name(self) -> str:
        return self.full_name.split()[0] if self.full_name else ""

    @property
    def last_name(self) -> str:
        parts = self.full_name.split()
        return " ".join(parts[1:]) if len(parts) > 1 else ""

class SearchCriteria(BaseModel):
    target_roles: List[str] = Field(default_factory=list, description="Target job titles / roles")
    keywords: List[str] = Field(default_factory=list, description="Technical skill keywords")
    location_keywords: List[str] = Field(
        default_factory=lambda: ["remote", "latam", "worldwide", "global", "anywhere"],
        description="Location filtering keywords"
    )
    min_salary_usd: Optional[int] = Field(None, description="Minimum target compensation")

class ATSSettings(BaseModel):
    enabled_platforms: List[str] = Field(
        default_factory=lambda: ["ashby", "greenhouse", "lever"],
        description="Active ATS scanners"
    )
    auto_upload_resume: bool = True
    stealth_mode: bool = True

class CandidateProfile(BaseModel):
    personal_info: PersonalInfo
    search_criteria: SearchCriteria
    ats_settings: ATSSettings = Field(default_factory=ATSSettings)

class JobPosting(BaseModel):
    ats: ATSPlatform
    company: str
    title: str
    location: str
    url: str
    match_score: Optional[int] = None
    compensation: Optional[str] = None
    created_at: Optional[str] = None
