"""
Base Form Applicator Interface.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict
from playwright.async_api import Page
from src.core.models import CandidateProfile
from src.automation.applicators.hud import HudMixin
from src.automation.applicators.salary import SalaryMixin, CONTRACTOR_KEYWORDS
from src.automation.applicators.questions_engine import QuestionsEngineMixin
from src.automation.applicators.audit import AuditMixin
from src.automation.applicators.file_uploader import FileUploaderMixin
from src.automation.applicators.custom_questions import CustomQuestionsMixin
from src.automation.applicators.form_controls import FormControlsMixin


class BaseApplicator(
    HudMixin,
    SalaryMixin,
    QuestionsEngineMixin,
    AuditMixin,
    FileUploaderMixin,
    CustomQuestionsMixin,
    FormControlsMixin,
    ABC,
):
    """
    Abstract base applicator orchestrating browser interactions, compensation detection,
    deterministic and LLM question answering, form control interaction, and audits.
    """

    CONTRACTOR_KEYWORDS = CONTRACTOR_KEYWORDS

    def __init__(self, page: Page, profile: CandidateProfile, company: str = "", role: str = ""):
        self.page = page
        self.profile = profile
        self.p_info = profile.personal_info
        self.prefs = profile.preferences
        self.company = company
        self.role = role
        self.filled_fields: Dict[str, str] = {}

    @abstractmethod
    async def fill_form(self, cv_pdf_path: Optional[Path] = None) -> bool:
        """Fill all standard fields on the application page."""
        pass
