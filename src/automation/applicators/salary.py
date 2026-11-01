"""
Salary and compensation detection mixin for application forms.
"""

import re
from typing import Optional, Dict, Tuple, Any

CONTRACTOR_KEYWORDS = re.compile(
    r"\b(contractor|independent\s+contractor|b2b|freelance|hourly\s+rate|usd/hr|usd\s+per\s+hour)\b",
    re.IGNORECASE,
)


class SalaryMixin:
    """Methods for detecting posted compensation ranges and computing candidate salary."""

    CONTRACTOR_KEYWORDS = CONTRACTOR_KEYWORDS

    SALARY_RANGE_PATTERNS = [
        re.compile(
            r"(?:salary|compensation|pay|rate|range|budget)?[:\s]*"
            r"\$?\s*([0-9]{1,3}(?:,[0-9]{3})*|[0-9]{2,6})(?:\.[0-9]{2})?\s*(k)?\s*"
            r"(?:-|–|—|to)\s*"
            r"\$?\s*([0-9]{1,3}(?:,[0-9]{3})*|[0-9]{2,6})(?:\.[0-9]{2})?\s*(k)?\s*"
            r"(?:usd)?\s*"
            r"(?:(?:per|\/|a)\s*(year|yr|annum|annual|month|mo|hr|hour))?",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:up\s+to|max|maximum|budget\s+of|starting\s+at)\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*|[0-9]{2,6})(?:\.[0-9]{2})?\s*(k)?\s*(?:usd)?\s*"
            r"(?:(?:per|\/|a)\s*(year|yr|annum|annual|month|mo|hr|hour))?",
            re.IGNORECASE,
        ),
    ]

    async def detect_is_contractor_posting(self) -> bool:
        """
        Check page text to determine if the job posting explicitly specifies a contractor/B2B modality.
        If not specified, returns False so the dependent employee salary is used by default.
        """
        try:
            body_text = await self.page.inner_text("body")
            return bool(CONTRACTOR_KEYWORDS.search(body_text))
        except Exception:
            return False

    async def detect_posted_salary_range(self) -> Optional[Dict[str, Any]]:
        """
        Inspect job description and page text to detect if the job posting explicitly specifies
        a salary range or compensation ceiling (hourly, monthly, or annual).
        """
        try:
            body_text = await self.page.inner_text("body")
            for pattern in self.SALARY_RANGE_PATTERNS:
                for match in pattern.finditer(body_text):
                    groups = match.groups()
                    if len(groups) == 5:
                        raw_max = groups[2]
                        is_k = bool(groups[3] or groups[1])
                        period_raw = (groups[4] or "").lower()
                    else:
                        raw_max = groups[0]
                        is_k = bool(groups[1])
                        period_raw = (groups[2] or "").lower()

                    if not raw_max:
                        continue

                    val = float(raw_max.replace(",", ""))
                    if is_k or (val < 1000 and "k" in match.group(0).lower()):
                        val *= 1000

                    # Filter out year numbers (2024, 2025, 2026, 2027) or tiny integers < 15
                    if val in (2024, 2025, 2026, 2027) or val < 15:
                        continue

                    if any(p in period_raw for p in ["year", "yr", "annum", "annual"]):
                        period = "year"
                    elif any(p in period_raw for p in ["month", "mo"]):
                        period = "month"
                    elif any(p in period_raw for p in ["hr", "hour"]):
                        period = "hour"
                    else:
                        if val >= 20000:
                            period = "year"
                        elif val <= 150:
                            period = "hour"
                        else:
                            period = "month"

                    if period == "year":
                        monthly_equiv = val / 12.0
                    elif period == "hour":
                        monthly_equiv = val * 160.0
                    else:
                        monthly_equiv = val

                    return {
                        "max_amount": val,
                        "period": period,
                        "monthly_equivalent": monthly_equiv,
                    }
        except Exception:
            pass
        return None

    async def get_effective_salary(self, is_contractor: bool = False) -> Tuple[int, str, str]:
        """
        Calculate effective salary to fill.
        If the posting specifies a salary ceiling greater than the candidate's preferences,
        adjust to that proposed maximum. If lower or not specified, use candidate's preference.
        Returns: (salary_num, salary_str, modality_label)
        """
        base_monthly = self.prefs.get_salary_value(is_contractor=is_contractor) or 3500
        modality_label = "Contractor" if is_contractor else "Dependent Employee (Default)"

        posted_salary = await self.detect_posted_salary_range()
        if posted_salary and posted_salary["monthly_equivalent"] > base_monthly:
            period = posted_salary["period"]
            max_amount = posted_salary["max_amount"]
            monthly_equiv = posted_salary["monthly_equivalent"]

            if period == "year":
                salary_num = int(max_amount)
                salary_str = f"${salary_num:,} USD / year"
                label = f"{modality_label} (Ajustado al maximo anual propuesto: {salary_str})"
            elif period == "hour":
                salary_num = int(max_amount)
                salary_str = f"${salary_num:,} USD / hour"
                label = f"{modality_label} (Ajustado al maximo por hora propuesto: {salary_str})"
            else:
                salary_num = int(monthly_equiv)
                salary_str = f"${salary_num:,} USD / month"
                label = f"{modality_label} (Ajustado al maximo mensual propuesto: {salary_str})"

            return salary_num, salary_str, label

        salary_num = base_monthly
        salary_str = self.prefs.get_formatted_salary(is_contractor=is_contractor)
        return salary_num, salary_str, modality_label
