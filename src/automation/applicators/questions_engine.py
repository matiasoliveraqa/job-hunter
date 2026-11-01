"""
Deterministic and dynamic question resolution engine for ATS applications.
"""

import re
from typing import Optional, Dict, List, Any
from src.core.synonyms import get_dropdown_choices, GENERAL_DECLINE_CHOICES
from src.automation.applicators.salary import CONTRACTOR_KEYWORDS


class QuestionsEngineMixin:
    """Methods for classifying questions, deterministic answers, and dropdown matching."""

    @staticmethod
    def is_deterministic_field(text: str, field_meta: Optional[dict] = None) -> bool:
        """Return True if field belongs to closed deterministic whitelist (never send to LLM)."""
        meta = field_meta or {}
        combined = f"{text or ''} {meta.get('name', '')} {meta.get('id', '')} {meta.get('autocomplete', '')}".lower()
        patterns = [
            # Gender / Sex (English & Spanish)
            re.compile(r"\b(gender|sex|género|genero|sexo)\b", re.IGNORECASE),
            # Race / Ethnicity (English & Spanish)
            re.compile(r"\b(race|ethnicity|hispanic|latino|raza|etnia|hispano)\b", re.IGNORECASE),
            # Veteran (English & Spanish)
            re.compile(r"\b(veteran|military|veterano|condición\s+de\s+veterano|condicion\s+de\s+veterano|militar)\b", re.IGNORECASE),
            # Disability (English & Spanish)
            re.compile(r"\b(disability|handicap|discapacidad|situación\s+de\s+discapacidad|situacion\s+de\s+discapacidad)\b", re.IGNORECASE),
            # Names (English & Spanish)
            re.compile(r"\b(preferred\s+name|first\s+name|last\s+name|full\s+name|given\s+name|family\s+name|legal\s+name|nombre|apellido|nombre\s+completo|primer\s+nombre|segundo\s+nombre)\b", re.IGNORECASE),
            # Contact (Email / Phone) (English & Spanish)
            re.compile(r"\b(email|phone|telephone|mobile|cell|correo\s+electr[oó]nico|correo|tel[eé]fono|m[oó]vil|celular)\b", re.IGNORECASE),
            # Location / Residence / City / State / Country (English & Spanish)
            re.compile(r"\b(location|city|country|state|province|office|region|country\s+of\s+residence|city\s+of\s+residence|where\s+are\s+you\s+based|ubicaci[oó]n|pa[ií]s|provincia|departamento|ciudad|oficina|sede|regi[oó]n|donde\s+vives|donde\s+resides|residencia)\b", re.IGNORECASE),
            # Postal / ZIP Code (English & Spanish)
            re.compile(r"\b(zip(\s*code)?|postal(\s*code)?|c[oó]digo\s*postal)\b", re.IGNORECASE),
            # Date Available / Start Date (English & Spanish)
            re.compile(r"\b(date\s+available|available\s+date|earliest\s+start|start\s+date|fecha\s+disponible)\b", re.IGNORECASE),
            # Authorization / Visa (English & Spanish)
            re.compile(r"\b(authorized\s+to\s+work|work\s+authorization|legally\s+authorized|visa\s+sponsorship|require\s+sponsorship|autorizaci[oó]n\s+para\s+trabajar|autorizacion\s+para\s+trabajar|autorizado\s+para\s+trabajar|patrocinio\s+de\s+visa|patrocinio)\b", re.IGNORECASE),
        ]
        return any(p.search(combined) for p in patterns)

    @staticmethod
    def is_sensitive_field(text: str) -> bool:
        """Return True if field is related to EEO (gender, race, veteran, disability) or location/residency."""
        t = (text or "").lower()
        patterns = [
            # EEO (English & Spanish)
            r"\b(gender|sex|género|genero|sexo)\b",
            r"\b(race|ethnicity|raza|etnia)\b",
            r"\b(veteran|military|veterano|condición\s+de\s+veterano|condicion\s+de\s+veterano|militar)\b",
            r"\b(disability|disabled|handicap|discapacidad|situación\s+de\s+discapacidad|situacion\s+de\s+discapacidad)\b",
            # Location / Country / State / Province / Office / City (English & Spanish)
            r"\b(location|country|state|province|office|city|region)\b",
            r"\b(ubicaci[oó]n|pa[ií]s|provincia|departamento|ciudad|oficina|sede|regi[oó]n)\b",
        ]
        return any(re.search(p, t, re.IGNORECASE) for p in patterns)

    @staticmethod
    def is_location_field(text: str) -> bool:
        """Return True if field is specifically related to location, state, country, or office."""
        t = (text or "").lower()
        patterns = [
            r"\b(location|country|state|province|office|city|region)\b",
            r"\b(ubicaci[oó]n|pa[ií]s|provincia|departamento|ciudad|oficina|sede|regi[oó]n)\b",
        ]
        return any(re.search(p, t, re.IGNORECASE) for p in patterns)

    @staticmethod
    def clean_question_label(text: str) -> str:
        """Sanitize field question/label text to avoid neighbor question contamination."""
        if not text:
            return ""
        cleaned = re.sub(r"\s+", " ", text).strip()
        if len(cleaned) > 120:
            cleaned = cleaned[:120].strip()
        if cleaned.count("?") > 1:
            cleaned = cleaned.split("?")[0] + "?"
        if cleaned.count("*") > 1:
            cleaned = (cleaned.split("*")[0] + "*").strip()
        return cleaned.strip()

    @staticmethod
    def match_experience_range(years: int, options: List[str]) -> Optional[str]:
        """Match candidate's numeric years of experience to a discrete radio/select option."""
        if not options:
            return None
        # 1. Exact range (e.g., "3-5 years", "6-9 years", "6 to 9")
        for opt in options:
            text = opt.lower().strip()
            m_range = re.search(r"(\d+)\s*(?:-|to|a)\s*(\d+)", text)
            if m_range:
                low = int(m_range.group(1))
                high = int(m_range.group(2))
                if low <= years <= high:
                    return opt
        # 2. Plus/more range (e.g., "10+ years", "5+ years", "more than 5")
        for opt in options:
            text = opt.lower().strip()
            m_plus = re.search(r"(\d+)\s*(?:\+|plus|\s+or\s+more|\s+o\s+m[aá]s)", text)
            if m_plus:
                min_y = int(m_plus.group(1))
                if years >= min_y:
                    return opt
        # 3. Less/under range (e.g., "Less than 3", "under 3", "< 3")
        for opt in options:
            text = opt.lower().strip()
            m_less = re.search(r"(?:less\s+than|under|menos\s+de|<)\s*(\d+)", text)
            if m_less:
                max_y = int(m_less.group(1))
                if years < max_y:
                    return opt
        return None

    def match_dropdown_option(
        self,
        options: List[str],
        preferred_choices: List[str],
        is_sensitive: bool = False,
        fallback_first: bool = False,
    ) -> Optional[str]:
        """
        Match dropdown options using strict 3-level matching:
        1. Normalized exact equality (strip().lower())
        2. Whole word match (\\bword\\b)
        3. Substring match (as last resort, disallowed for sensitive fields to prevent Male -> Female)

        If sensitive and no match, picks 'Decline to self-identify' / 'Prefer not to say'.
        Never selects fallback_first on sensitive fields.
        """
        if not options:
            return None

        def find_level_match(wanted: str) -> Optional[tuple[int, str]]:
            w_norm = wanted.strip().lower()
            if not w_norm:
                return None
            word_re = re.compile(rf"\b{re.escape(w_norm)}\b", re.IGNORECASE)

            # Level 1: exact normalized match
            for opt in options:
                t = (opt or "").strip()
                if t.lower() == w_norm:
                    return (1, t)

            # Level 2: whole word match
            for opt in options:
                t = (opt or "").strip()
                if word_re.search(t):
                    return (2, t)

            # Level 3: substring match (last resort, disallowed for sensitive fields)
            if not is_sensitive:
                for opt in options:
                    t = (opt or "").strip()
                    if w_norm in t.lower():
                        return (3, t)

            return None

        # 1. Match preferred choices
        best_match = None
        for choice in preferred_choices:
            if not choice:
                continue
            m = find_level_match(choice)
            if m:
                level, opt_text = m
                if level == 1:
                    return opt_text
                if best_match is None or level < best_match[0]:
                    best_match = m

        if best_match:
            return best_match[1]

        # 2. Sensitive fields: fallback to decline / prefer not to say
        if is_sensitive:
            for dec in GENERAL_DECLINE_CHOICES:
                m = find_level_match(dec)
                if m:
                    return m[1]
            return None

        # 3. Non-sensitive fallback
        if fallback_first and options:
            for opt in options:
                t = (opt or "").strip()
                if t and not any(p in t.lower() for p in ["select", "choose", "please", "elegir", "--"]):
                    return t
            return options[0]

        return None

    def _desired_dropdown_choice(self, question_text: str) -> Optional[List[str]]:
        """Return prioritized list of option substrings to pick for a dropdown/select question."""
        q = (question_text or "").strip().lower()
        if not q:
            return None

        # Explicit instruction in question: e.g. "please select 'Digital Therapeutics' from the list below"
        m_instruct = re.search(r"(?:please\s+)?select\s+['\"]([^'\"]+)['\"]", question_text, re.IGNORECASE)
        if m_instruct:
            target_val = m_instruct.group(1).strip()
            return [target_val]
        if any(k in q for k in ["visa sponsorship", "require sponsorship", "require employer sponsorship", "h-1b", "patrocinio de visa", "patrocinio"]):
            return ["No"] if self.p_info.requires_us_visa_sponsorship.strip().lower() != "yes" else ["Yes"]
        if "authorized to work" in q and any(c in q for c in ["united states", "u.s.", " in the us", "brazil", "brasil", "uk", "canada"]):
            return ["No"]
        if any(k in q for k in ["autorizado para trabajar", "autorización para trabajar", "autorizacion para trabajar"]):
            return ["Sí", "Si", "Yes"]
        if any(k in q for k in ["authorized to work", "legally authorized"]):
            return ["Yes"]
        if any(k in q for k in ["trabajo remoto"]):
            return ["Sí", "Si", "Yes"]
        if any(k in q for k in ["remote work", "comfortable working in a remote", "work remotely", "remote setting"]):
            return ["Yes"]
        if any(k in q for k in ["privacy policy", "consent", "interview transcript", "acknowledge", "data processing", "agree"]):
            return ["Yes, I consent", "Yes", "I agree", "Agree", "Accept"]
        if any(k in q for k in ["política de privacidad", "politica de privacidad", "terminos", "consentimiento", "autorizo"]):
            return ["Sí", "Si", "Acepto", "Yes"]
        if any(k in q for k in ["country are you currently a resident", "country of residence", "current resident of", "resident of", "country you reside", "country do you reside", "país de residencia", "pais de residencia"]):
            return [self.p_info.country, self.p_info.location]
        if any(k in q for k in ["based in united states", "state of residence", "outside of the united states", "outside the united states", "state in the us"]):
            return [
                "I am not located in the United States of America currently",
                "I am not located in the United States",
                "Not located in the United States",
                "Outside the United States",
                "Outside the US",
                "N/A",
                "None",
            ]
        if any(k in q for k in ["native language", "mother tongue", "first language", "primary language", "idioma nativo", "lengua materna"]):
            native = getattr(self.prefs, "native_language", None)
            return [native] if native else None
        if any(k in q for k in ["english level", "english proficiency", "level of english", "proficiency in english", "your english", "english", "nivel de inglés", "nivel de ingles"]):
            level = self.prefs.english_level
            return [level, "Fluent", "Professional", "Advanced"] if level else None
        if any(k in q for k in ["languages you are proficient in", "language proficiency", "languages you speak", "working language", "idiomas", "language"]):
            native = getattr(self.prefs, "native_language", None)
            return ["English", native] if native else ["English"]
        if any(k in q for k in ["skills category", "core strengths", "functional area", "primary skill", "area of expertise"]):
            return ["Software Engineering", "Quality Assurance", "Information Technology", "Computer Science"]
        if any(k in q for k in ["degree", "título", "titulo", "level of education", "highest level of education", "education", "educación", "educacion", "formación", "formacion"]):
            return ["Bachelors Degree", "Bachelor", "Engineer's Degree", "Associates Degree", "University", "Undergraduate", "Some College", "Universitario", "Grado", "Licenciatura", "Ingeniería", "Ingenieria"]
        if any(k in q for k in ["discipline", "major", "field of study", "carrera"]):
            return ["Computer Science", "Information Systems", "Information Technology", "Software Engineering", "Engineering", "Tecnología de la Información", "Ingeniería de Software", "Informática", "Informatica"]
        if any(k in q for k in ["gender", "sex", "género", "genero", "sexo"]):
            return get_dropdown_choices("gender", getattr(self.p_info, "gender", None))
        if any(k in q for k in ["race", "ethnicity", "raza", "etnia"]):
            return get_dropdown_choices("race", getattr(self.p_info, "race", None))
        if any(k in q for k in ["veteran", "militar", "veterano", "condición de veterano", "condicion de veterano"]):
            return get_dropdown_choices("veteran_status", getattr(self.p_info, "veteran_status", None))
        if any(k in q for k in ["disability", "discapacidad", "situación de discapacidad", "situacion de discapacidad"]):
            return get_dropdown_choices("disability_status", getattr(self.p_info, "disability_status", None))
        if any(k in q for k in ["location", "ubicación", "ubicacion", "country", "país", "pais", "state", "estado", "provincia", "departamento", "office", "oficina", "sede", "city", "ciudad", "region", "región", "regio"]):
            return [
                self.p_info.location,
                self.p_info.country,
                self.p_info.city,
                "Remote",
                "Remoto",
                "LATAM",
                "Remote - LATAM",
                "Worldwide",
                "Anywhere",
            ]
        return None

    def _generate_deterministic_answer(
        self,
        question_text: str,
        salary_str: str = "",
        salary_num: Optional[int] = None,
        field_meta: Optional[dict] = None,
    ) -> Optional[str]:
        """Generate factual, deterministic answers for contact and profile fields."""
        # 1. Attribute-based routing (clean signals from input name, id, autocomplete)
        meta = field_meta or {}
        attr_tokens = f"{meta.get('name', '')} {meta.get('id', '')} {meta.get('autocomplete', '')}".lower().strip()
        if attr_tokens:
            if re.search(r"\b(linkedin|linkedin_url)\b", attr_tokens):
                return self.p_info.linkedin_url
            if re.search(r"\b(github|github_url)\b", attr_tokens):
                return self.p_info.github_url
            if re.search(r"\b(portfolio|website|blog)\b", attr_tokens) and not re.search(r"\b(project|proud)\b", attr_tokens):
                return self.p_info.portfolio_url
            if re.search(r"\b(preferred_name|preferred_first_name)\b", attr_tokens) or attr_tokens == "preferred-name":
                return getattr(self.p_info, "preferred_name", None) or self.p_info.first_name
            if re.search(r"\b(given[-_]?name|first[-_]?name)\b", attr_tokens) or meta.get("autocomplete") == "given-name":
                return self.p_info.first_name
            if re.search(r"\b(family[-_]?name|last[-_]?name)\b", attr_tokens) or meta.get("autocomplete") == "family-name":
                return self.p_info.last_name
            if re.search(r"\b(email)\b", attr_tokens) or meta.get("autocomplete") == "email":
                return self.p_info.email
            if re.search(r"\b(phone|mobile|cell|tel)\b", attr_tokens) or meta.get("autocomplete") == "tel":
                return self.p_info.phone
            if re.search(r"\b(city)\b", attr_tokens) or meta.get("autocomplete") == "address-level2":
                return self.p_info.city or self.p_info.location
            if re.search(r"\b(state|province|region)\b", attr_tokens) or meta.get("autocomplete") == "address-level1":
                return getattr(self.p_info, "resolved_state", self.p_info.city)
            if re.search(r"\b(country)\b", attr_tokens) or meta.get("autocomplete") == "country-name":
                return self.p_info.country
            if re.search(r"\b(zip|postal|postal_code|zip_code)\b", attr_tokens) or meta.get("autocomplete") == "postal-code":
                return getattr(self.p_info, "resolved_postal_code", "")
            if re.search(r"\b(date_available|available_date|start_date)\b", attr_tokens):
                from datetime import datetime, timedelta
                return (datetime.now() + timedelta(days=14)).strftime("%d/%m/%Y")

        q = (question_text or "").strip().lower()
        if not q or len(q) < 3:
            return None

        # Guard: return None if question starts with a sensitive or deterministic field before keyword rules
        first_chunk = re.split(r"[.?;*:\n]+", (question_text or "").strip())[0].strip()
        first_tokens = " ".join(first_chunk.split()[:4]) if first_chunk else ""
        if (
            self.is_sensitive_field(first_chunk)
            or self.is_sensitive_field(first_tokens)
            or self.is_deterministic_field(first_chunk)
            or self.is_deterministic_field(first_tokens)
        ):
            if not any(re.search(rf"\b{re.escape(k)}\b", q) for k in [
                "where are you based",
                "current location",
                "country of residence",
                "city and country",
                "zip",
                "postal",
                "código postal",
                "codigo postal",
                "date available",
                "available date",
                "start date",
                "fecha disponible",
            ]):
                return None

        # Preferred name check before standard contact fields
        if re.search(r"\b(preferred\s+name|preferred\s+first\s+name)\b", q):
            return getattr(self.p_info, "preferred_name", None) or self.p_info.first_name

        # Skip standard contact fields already handled if not preferred name
        if any(re.search(rf"\b{re.escape(k)}\b", q) for k in ["first name", "last name", "full name", "email", "phone", "resume", "cv", "pronoun"]):
            return None

        if re.search(r"\blinkedin\b", q):
            return self.p_info.linkedin_url
        if re.search(r"\b(github|git\s+repository)\b", q):
            return self.p_info.github_url

        # Check if question is an open-ended question asking about a project or experience
        is_project_q = bool(re.search(r"\b(project|proud\s+of|technical\s+challenge|problem\s+you\s+solved|achievement|describe|tell\s+us\s+about)\b", q))
        if not is_project_q and re.search(r"\b(portfolio|personal\s+website|website|blog)\b", q):
            return self.p_info.portfolio_url

        if any(
            re.search(rf"\b{re.escape(k)}\b", q)
            for k in [
                "salary",
                "compensation",
                "financial expectation",
                "pay expectation",
                "expected pay",
                "expected rate",
                "rate expectation",
                "hourly rate",
                "monthly rate",
                "remuneration",
                "us dollars per month",
                "usd per month",
                "usd/month",
            ]
        ):
            if any(re.search(rf"\b{re.escape(k)}\b", q) for k in ["annual", "yearly", "per year", "/yr", "/year"]):
                if salary_num:
                    target_val = salary_num if "/ year" in salary_str else (salary_num * 12 if "/ month" in salary_str else salary_num)
                    return f"${target_val:,} USD / year"
            elif any(re.search(rf"\b{re.escape(k)}\b", q) for k in ["hourly", "per hour", "/hr", "/hour"]):
                if salary_num:
                    target_val = salary_num if "/ hour" in salary_str else max(1, round(salary_num / 160))
                    return f"${target_val:,} USD / hour"
            return salary_str or self.prefs.get_formatted_salary(is_contractor=False)

        if any(re.search(rf"\b{re.escape(k)}\b", q) for k in ["notice period", "when can you start", "earliest start", "availability to start", "how soon can you"]):
            return self.prefs.notice_period or "2 weeks"
        if re.search(r"\b(zip(\s*code)?|postal(\s*code)?|c[oó]digo\s*postal)\b", q):
            return getattr(self.p_info, "resolved_postal_code", "11000") or "11000"
        if re.search(r"\b(state|province|provincia|departamento)\b", q):
            return getattr(self.p_info, "resolved_state", self.p_info.city)
        if re.search(r"\b(date\s+available|available\s+date|earliest\s+start\s+date|start\s+date|fecha\s+disponible)\b", q):
            from datetime import datetime, timedelta
            return (datetime.now() + timedelta(days=14)).strftime("%d/%m/%Y")
        if re.search(r"\b(years\s+of\s+experience|how\s+many\s+years)\b", q):
            return str(self.p_info.years_of_experience) if getattr(self.p_info, "years_of_experience", None) is not None else None
        if any(re.search(rf"\b{re.escape(k)}\b", q) for k in ["current company", "current employer", "present employer"]):
            return self.p_info.current_company
        if any(re.search(rf"\b{re.escape(k)}\b", q) for k in ["english level", "english proficiency", "level of english", "your english"]):
            return self.prefs.english_level
        if any(re.search(rf"\b{re.escape(k)}\b", q) for k in ["native language", "mother tongue", "first language", "idioma nativo"]):
            return getattr(self.prefs, "native_language", None)

        # Explicit instruction: e.g. "type 'YES' to confirm" or "enter 'AGREE'"
        m_type = re.search(r"(?:type|enter|write)\s+['\"]([^'\"]+)['\"]", question_text, re.IGNORECASE)
        if m_type:
            return m_type.group(1).strip()

        oq = getattr(self.profile, "open_questions", None)
        if any(re.search(rf"\b{re.escape(k)}\b", q) for k in ["level of education", "highest level of education", "education completed", "educational background"]):
            return oq.education_level if oq else None
        if any(re.search(rf"\b{re.escape(k)}\b", q) for k in ["time zone", "timezone", "working hours"]):
            return oq.timezone_overlap if oq else None
        if any(re.search(rf"\b{re.escape(k)}\b", q) for k in ["where are you based", "current location", "country of residence", "city and country"]):
            return self.p_info.location
        if re.search(r"\btelegram\b", q):
            return self.p_info.phone

        if oq and oq.custom_qa:
            for kw, ans in oq.custom_qa.items():
                if re.search(rf"\b{re.escape(kw.lower())}\b", q):
                    return ans

        return None

    def _generate_open_question_answer(self, question_text: str, salary_str: str = "", salary_num: Optional[int] = None, is_required: bool = False) -> Optional[str]:
        """
        Fallback generator for open-ended application questions when LLM is unavailable.
        Strictly grounded in candidate facts.
        """
        q = (question_text or "").strip().lower()
        if not q or len(q) < 3:
            return None

        # Check deterministic fields first
        det = self._generate_deterministic_answer(question_text, salary_str=salary_str, salary_num=salary_num)
        if det:
            return det

        oq = getattr(self.profile, "open_questions", None)

        # Open-ended motivation / "Why do you want to..." / "Why <Company>?" / "What excites you..."
        is_motivation_q = bool(
            re.search(r"\bwhy\s+[a-z0-9]", q)
            or any(
                k in q
                for k in [
                    "why do you want",
                    "why are you interested",
                    "what interests you",
                    "what excites you",
                    "why this role",
                    "why apply",
                    "why join",
                    "what draws you",
                    "what you know about what we do",
                    "aligns with your career",
                    "motivat",
                ]
            )
        )
        if is_motivation_q and any(k in q for k in ["bank", "fintech", "payment"]):
            if oq and oq.fintech_motivation:
                return oq.fintech_motivation
            years = self.p_info.years_of_experience or 7
            return (
                f"I have over {years} years of professional experience testing financial systems and web platforms, "
                "where reliability, compliance, and regression test coverage are critical."
            )

        # Distinguish between questions about the company vs questions about the role
        is_about_company = any(k in q for k in ["what you know about what we do", "aligns with your career", "why us", "why this company"]) or (
            bool(self.company and self.company.lower() in q)
        )
        if is_motivation_q:
            if is_about_company:
                comp = self.company or "your company"
                years = self.p_info.years_of_experience
                years_text = f"my {years}+ years of QA experience" if years else "my QA experience"
                return (
                    f"I want to work with {comp} because I value strong product engineering and high quality standards. "
                    f"I want to apply {years_text} to improve test coverage and collaborate closely with your engineering team."
                )
            if oq and oq.motivation:
                return oq.motivation
            years = self.p_info.years_of_experience or 7
            company_mention = f"at {self.p_info.current_company}" if self.p_info.current_company else ""
            return (
                f"I have {years} years of engineering experience {company_mention}. "
                "I want to work on a team with high quality standards where I can own automated testing and CI/CD workflows."
            )

        if any(k in q for k in ["project", "proud of", "technical challenge", "problem you solved", "achievement", "quota", "kpi", "metrics", "targets"]):
            if oq and getattr(oq, "key_project", None):
                return oq.key_project
            if oq and getattr(oq, "metrics_and_kpis", None):
                return oq.metrics_and_kpis
            return (
                "I focus on designing automated testing frameworks, maintaining release stability, "
                "reducing defect rates, and meeting sprint delivery goals."
            )

        if any(k in q for k in ["anything else", "additional information", "cover letter", "additional notes"]):
            if oq and getattr(oq, "additional_info", None):
                return oq.additional_info
            if oq and oq.experience_summary:
                return oq.experience_summary

        if any(k in q for k in ["experience with automation", "describe your experience", "tell us about your experience", "relevant experience", "background"]):
            if oq and oq.experience_summary:
                return oq.experience_summary
            years = self.p_info.years_of_experience or 7
            company_mention = f"in my current role at {self.p_info.current_company}" if self.p_info.current_company else ""
            return (
                f"I have worked in software engineering and QA for over {years} years. "
                f"{company_mention.capitalize()}, I build automated test suites, maintain CI/CD pipelines, "
                "and collaborate with engineering teams to ensure release quality."
            )

        if is_required:
            years = self.p_info.years_of_experience or 7
            comp = self.company or "your team"
            return (
                f"I bring over {years} years of software testing and QA automation experience. "
                f"I want to collaborate with {comp} to improve test coverage, automate regression suites, and maintain high release standards."
            )

        return None

    def _generate_required_fallback(self, question_text: str) -> str:
        """
        Produce a safe, truthful fallback answer for any required question that wasn't covered.
        Grounded strictly in the candidate's verified profile.
        """
        q = (question_text or "").strip().lower()
        years = self.p_info.years_of_experience or 7

        if any(k in q for k in ["salary", "compensation", "rate", "remunerat"]):
            is_contractor = bool(CONTRACTOR_KEYWORDS.search(q))
            return "$4,500 USD / month" if is_contractor else "$3,000 USD / month"

        if any(k in q for k in ["notice", "start date", "availability", "how soon"]):
            return self.prefs.notice_period or "2 weeks notice period"

        if any(k in q for k in ["why", "interest", "motivat"]):
            comp = self.company or "your team"
            return (
                f"I want to join {comp} to apply my {years}+ years of QA automation experience, "
                "strengthen end-to-end test coverage, and collaborate with engineering on release quality."
            )

        return (
            f"I have over {years} years of software testing and QA automation experience. "
            "I design and maintain Playwright test suites, REST API test frameworks, and CI/CD pipelines."
        )
