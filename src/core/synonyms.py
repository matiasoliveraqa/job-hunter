"""
Synonym mappings for dropdowns and question routing across languages.
Supports canonical code resolution to localized option strings.
"""

from typing import Dict, List, Optional

# Canonical code -> localized option strings for form matching
DROPDOWN_SYNONYMS: Dict[str, Dict[str, List[str]]] = {
    "gender": {
        "male": [
            "Male",
            "Masculino",
            "Hombre",
            "Man",
        ],
        "female": [
            "Female",
            "Femenino",
            "Mujer",
            "Woman",
        ],
        "non_binary": [
            "Non-binary",
            "Non binary",
            "No binario",
            "Non-Binary",
            "Genderqueer",
        ],
        "decline": [
            "Decline to self-identify",
            "Prefer not to say",
            "Prefiero no responder",
            "Prefiero no decirlo",
            "I choose not to disclose",
            "No deseo responder",
        ],
    },
    "race": {
        "hispanic_latino": [
            "Hispanic or Latino",
            "Hispanic/Latino",
            "Hispanic",
            "Latino",
            "Hispano o Latino",
            "Hispano/Latino",
            "Hispano",
        ],
        "white": [
            "White",
            "Blanco",
            "White (Not Hispanic or Latino)",
            "Blanco (no hispano o latino)",
        ],
        "black": [
            "Black or African American",
            "Black",
            "Negro o Afroamericano",
            "Negro o afroamericano",
            "Afrodescendiente",
        ],
        "asian": [
            "Asian",
            "Asiático",
            "Asiatico",
        ],
        "indigenous": [
            "American Indian or Alaska Native",
            "Indigenous",
            "Indígena",
            "Indigena",
            "Nativo Americano",
        ],
        "two_or_more": [
            "Two or More Races",
            "Dos o más razas",
            "Dos o mas razas",
            "Two or more races (Not Hispanic or Latino)",
            "Dos o más etnias",
        ],
        "decline": [
            "Decline to self-identify",
            "Prefer not to say",
            "Prefiero no responder",
            "Prefiero no decirlo",
            "I choose not to disclose",
            "No deseo responder",
        ],
    },
    "veteran_status": {
        "not_veteran": [
            "I am not a veteran",
            "I am not a protected veteran",
            "Not a veteran",
            "No soy un veterano",
            "No soy veterano",
            "No",
        ],
        "veteran": [
            "I identify as one or more of the classifications of protected veteran",
            "Protected veteran",
            "I am a veteran",
            "Veteran",
            "Veterano",
            "Soy veterano protegido",
            "Yes",
            "Sí",
            "Si",
        ],
        "decline": [
            "Decline to self-identify",
            "I do not wish to self-identify",
            "I decline to self-identify",
            "Prefer not to say",
            "Prefiero no responder",
            "Prefiero no decirlo",
        ],
    },
    "disability_status": {
        "no": [
            "No, I do not have a disability",
            "No, I don't have a disability",
            "No tengo una discapacidad",
            "No tengo discapacidad",
            "No, no tengo una discapacidad",
            "No, no poseo una discapacidad",
            "No",
        ],
        "yes": [
            "Yes, I have a disability",
            "Yes, I have a disability (or previously had a disability)",
            "Yes, I have a disability (or previously had one)",
            "Sí, tengo una discapacidad",
            "Si, tengo una discapacidad",
            "Sí tengo o tuve una discapacidad",
            "Poseo una discapacidad",
            "Yes",
            "Sí",
            "Si",
        ],
        "decline": [
            "Decline to self-identify",
            "I do not wish to answer",
            "Prefer not to say",
            "Prefiero no responder",
            "Prefiero no decirlo",
            "No deseo contestar",
        ],
    },
    "work_authorization": {
        "yes": [
            "Yes",
            "Sí",
            "Si",
            "Autorizado",
        ],
        "no": [
            "No",
        ],
    },
    "visa_sponsorship": {
        "yes": [
            "Yes",
            "Sí",
            "Si",
        ],
        "no": [
            "No",
        ],
    },
}

# Standard decline / non-disclosure fallback options across languages
GENERAL_DECLINE_CHOICES: List[str] = [
    "Decline to self-identify",
    "Prefer not to say",
    "Prefiero no responder",
    "Prefiero no decirlo",
    "I do not wish to answer",
    "Do not wish to answer",
    "Decline to answer",
    "I choose not to disclose",
    "I decline to self-identify",
    "No deseo responder",
    "Decline",
]


def get_dropdown_choices(category: str, canonical_code: Optional[str]) -> List[str]:
    """
    Return prioritized localized option strings for a canonical code in a given category.
    Appends standard decline options as safe fallbacks.
    """
    cat_data = DROPDOWN_SYNONYMS.get(category, {})
    if not cat_data:
        return list(GENERAL_DECLINE_CHOICES)

    code = (canonical_code or "").strip().lower()
    choices: List[str] = []

    if code and code in cat_data:
        choices.extend(cat_data[code])

    # Append category-specific decline choices if present
    if "decline" in cat_data and code != "decline":
        for opt in cat_data["decline"]:
            if opt not in choices:
                choices.append(opt)

    # Append general decline choices
    for opt in GENERAL_DECLINE_CHOICES:
        if opt not in choices:
            choices.append(opt)

    return choices
