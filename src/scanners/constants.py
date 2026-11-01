"""
Regex patterns, country synonym registries, and keyword constants for ATS job scanners.
"""

import re

# Regex patterns to extract minimum required years of experience from job descriptions
EXPERIENCE_PATTERNS = [
    re.compile(
        r"\b(\d{1,2})\s*(?:\+|\s*(?:to|-|–)\s*\d{1,2})?\s*(?:years?|yrs?|años?)\b"
        r"(?:\s+of)?\s+(?:[a-z\-]+\s+){0,4}?(?:experience|experiencia)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:minimum|at\s+least|mínimo|al\s+menos)\s+(?:of\s+)?(\d{1,2})\+?\s*(?:years?|yrs?|años?)"
        r"(?:\s+of\s+(?:[a-z\-]+\s+){0,3}?experience)?",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:experience|experiencia)\s*(?:of|:)?\s*(\d{1,2})\s*(?:\+|\s*(?:to|-|–)\s*\d{1,2})?\s*(?:years?|yrs?|años?)",
        re.IGNORECASE,
    ),
]

# Explicit LATAM / Global keywords that override regional restrictions in location strings
LATAM_OR_GLOBAL_RE = re.compile(
    r"\b("
    r"latam|latin\s+america|south\s+america|americas|"
    r"argentina|bolivia|brazil|brasil|chile|colombia|costa\s+rica|ecuador|el\s+salvador|guatemala|"
    r"honduras|mexico|m\u00e9xico|nicaragua|panama|panam\u00e1|paraguay|peru|per\u00fa|"
    r"dominican\s+republic|uruguay|venezuela|"
    r"worldwide|global|"
    r"anywhere(?!\s+in\s+(?:the\s+)?(us|u\.s\.|usa|united\s+states|uk|united\s+kingdom|canada|europe|eu|india|apac|brazil|brasil))"
    r")\b",
    re.IGNORECASE,
)

# Reject explicit on-site and in-office jobs immediately
ONSITE_RE = re.compile(
    r"\b(onsite|on-site|in-office|presencial|office-based)\b",
    re.IGNORECASE,
)

# Hybrid jobs are only acceptable if located in the candidate's own city or country
HYBRID_RE = re.compile(
    r"\b(hybrid|híbrido)\b",
    re.IGNORECASE,
)

US_STATES_DELIMITED = (
    r",\s*(?:AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|"
    r"MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|"
    r"SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC)\b"
)

US_VARIANTS = r"(?:united\s+states|usa|us|u\.?\s?s\.?)"

# Non-LATAM country/city/region restrictions in location or title (e.g. "United States (Remote)", "Remote, US", "Anywhere in the US.")
RESTRICTED_LOCATION_RE = re.compile(
    r"(?:"
    r"\b(?:united\s+states|usa)\b|\bu\.s\.?(?!\w)|"
    rf"^\s*{US_VARIANTS}\s*$|"
    rf"^\s*{US_VARIANTS}\s*[-–,/|\)\]]|"
    rf"[-–,/|\(\[]\s*{US_VARIANTS}\s*(?:[-–,/|\)\]\.]|$)|"
    rf"\b(?:anywhere|everywhere|remote|based|located|resident)\s+in\s+(?:the\s+)?{US_VARIANTS}(?!\w)|"
    rf"\b(?:in|within)\s+(?:the\s+)?{US_VARIANTS}(?!\w)|"
    rf"\b(?:us|u\.?\s?s\.?|united\s+states)\s+(?:remote|only|based|resident|citizens?|nationwide)\b|"
    rf"\b(?:remote\s*[-–,/|\s]\s*{US_VARIANTS})(?!\w)|"
    r"\b(?:north\s+america|americas)\b|"
    + US_STATES_DELIMITED + r"|"
    r"\b(uk|united\s+kingdom|england|london|manchester|scotland|"
    r"canada|toronto|ottawa|montreal|vancouver|british\s+columbia|"
    r"europe|european\s+union|eu\s+remote|emea|cet|"
    r"germany|berlin|munich|france|paris|spain|madrid|barcelona|italy|rome|ireland|dublin|"
    r"netherlands|amsterdam|belgium|sweden|stockholm|switzerland|zurich|denmark|copenhagen|"
    r"poland|warsaw|serbia|belgrade|cyprus|romania|bulgaria|georgia|ukraine|kyiv|czech|prague|armenia|"
    r"finland|espoo|helsinki|norway|oslo|austria|vienna|hungary|budapest|israel|tel\s+aviv|"
    r"china|guangdong|beijing|shanghai|shenzhen|hong\s+kong|"
    r"india|ind-remote|bengaluru|bangalore|hyderabad|pune|mumbai|"
    r"philippines|manila|apac|vietnam|japan|tokyo|singapore|taiwan|south\s+korea|korea|pangyo|malaysia|kuala\s+lumpur|australia|sydney|melbourne|new\s+zealand|auckland|"
    r"california|san\s+francisco|san\s+mateo|santa\s+clara|marina\s+del\s+rey|los\s+angeles|los\s+gatos|"
    r"new\s+york|texas|dallas|plano|austin|houston|seattle|washington|chicago|illinois|atlanta|maryland|boston|massachusetts|denver|colorado|miami|florida|alabama|birmingham|kentucky|ft\.?\s*knox)\b"
    r")",
    re.IGNORECASE,
)

# Phrases inside the job description or application form questions that restrict the role to specific residents/citizens
RESIDENCY_RESTRICTION_RE = re.compile(
    r"(?:"
    r"state\s+of\s+residence\s+within\s+the\s+united\s+states|"
    r"(?:must\s+(?:be\s+)?(?:reside|live|located|based)\s+in)\s+(?:the\s+)?(?:united\s+states|usa|uk|canada|europe|eu|brazil|brasil|india|north\s+america|\bu\.?\s?s\.?(?!\w))|"
    r"(?:candidates?|applicants?)\s+(?:who\s+)?(?:must\s+be\s+)?(?:reside|residing|live|living|located|based)\s+in\s+(?:the\s+)?(?:united\s+states|usa|uk|canada|europe|eu|brazil|brasil|india|north\s+america|\bu\.?\s?s\.?(?!\w))|"
    r"(?:role|position)\s+(?:requires\s+(?:you\s+to\s+be\s+)?(?:located|based|residing|living)\s+in|is\s+only\s+open\s+to\s+(?:candidates\s+in)?)\s+(?:the\s+)?(?:united\s+states|usa|uk|canada|europe|eu|brazil|brasil|\bu\.?\s?s\.?(?!\w))|"
    r"only\s+(?:hiring|open\s+to\s+candidates|able\s+to\s+hire|consider\s+candidates)\b|"
    r"residir\s+(?:en|no)\s+(?:brasil|brazil)|"
    r"contrato\s+clt|regime\s+clt|vaga\s+exclusiva\s+para\s+residentes|"
    r"requires?\s+on-site\s+availability|"
    r"required\s+clearance\s*:\s*(?:public\s+trust|secret|active\s+secret|top\s+secret)|"
    r"\bu\.?\s?s\.?(?!\w)\s+citizenship\s+(?:is\s+)?required|"
    r"\b(?:anywhere|everywhere)\s+in\s+(?:the\s+)?(?:united\s+states|usa|\bu\.?\s?s\.?(?!\w))|"
    r"\b(?:united\s+states|\bu\.?\s?s\.?(?!\w))\s+(?:only|residents?\s+only|based\s+candidates\s+only|citizens?\s+only)\b|"
    r"\b(?:open|available)\s+(?:only\s+to|to)\s+(?:candidates\s+(?:based|located)\s+in\s+(?:the\s+)?(?:united\s+states|usa|\bu\.?\s?s\.?(?!\w)))|"
    r"\b(?:remote\s+within\s+(?:the\s+)?(?:united\s+states|usa|\bu\.?\s?s\.?(?!\w)))|"
    r"\b(?:remote\s*[-–,/|]\s*(?:anywhere\s+in\s+(?:the\s+)?(?:united\s+states|usa|\bu\.?\s?s\.?(?!\w))|\(?us\s+only\)?))|"
    r"(?:location|workplace)\s*[:\s–-]+\s*(?:anywhere\s+in\s+(?:the\s+)?(?:united\s+states|usa|\bu\.?\s?s\.?(?!\w))|(?:united\s+states|usa|\bu\.?\s?s\.?(?!\w))\s+remote|remote\s*[,–-]\s*(?:united\s+states|usa|\bu\.?\s?s\.?(?!\w)))|"
    r"(?:authorized|eligible|legally\s+(?:authorized|eligible|able))\s+to\s+work\s+in\s+(?:the\s+)?(?:united\s+states|usa|\bu\.?\s?s\.?(?!\w))|"
    r"work\s+in\s+the\s+us\s+without\s+sponsorship|"
    r"contingent\s+on\s+us\s+work\s+authorization|"
    r"\bu\.?\s?s\.?(?!\w)[-\s]based\s+(?:employees|candidates|applicants|workers|team|only)|"
    r"\bu\.?\s?s\.?(?!\w)\s+work\s+authorization"
    r")",
    re.IGNORECASE,
)

LATAM_COUNTRIES_LIST = [
    "argentina", "bolivia", "brazil", "brasil", "chile", "colombia", "costa rica", "ecuador",
    "el salvador", "guatemala", "honduras", "mexico", "méxico", "nicaragua", "panama", "panamá",
    "paraguay", "peru", "perú", "dominican republic", "uruguay", "venezuela"
]

LATAM_KEYWORDS = [
    "latam", r"latin\s+america", r"south\s+america"
] + [re.escape(c).replace(r"\ ", r"\s+") for c in LATAM_COUNTRIES_LIST]

LATAM_RE = re.compile(r"\b(" + "|".join(LATAM_KEYWORDS) + r")\b", re.IGNORECASE)

NORTH_AMERICA_RE = re.compile(
    r"\b(united\s+states|usa|u\.s\.?|us|canada|toronto|vancouver|montreal|north\s+america)\b",
    re.IGNORECASE
)

OTHER_REGIONS_RESTRICTED_RE = re.compile(
    r"\b(uk|united\s+kingdom|england|london|manchester|scotland|"
    r"europe|european\s+union|eu\s+remote|emea|cet|"
    r"germany|berlin|munich|france|paris|spain|madrid|barcelona|italy|rome|ireland|dublin|"
    r"netherlands|amsterdam|belgium|sweden|stockholm|switzerland|zurich|denmark|copenhagen|"
    r"poland|warsaw|serbia|belgrade|cyprus|romania|bulgaria|georgia|ukraine|kyiv|czech|prague|armenia|"
    r"finland|espoo|helsinki|norway|oslo|austria|vienna|hungary|budapest|israel|tel\s+aviv|"
    r"china|guangdong|beijing|shanghai|shenzhen|hong\s+kong|"
    r"india|ind-remote|bengaluru|bangalore|hyderabad|pune|mumbai|"
    r"philippines|manila|apac|vietnam|japan|tokyo|singapore|taiwan|south\s+korea|korea|pangyo|malaysia|kuala\s+lumpur|australia|sydney|melbourne|new\s+zealand|auckland)\b",
    re.IGNORECASE,
)

COUNTRY_SYNONYMS = {
    "alemania": ["alemania", "germany", "deutschland", "berlin", "munich"],
    "germany": ["alemania", "germany", "deutschland", "berlin", "munich"],
    "japon": ["japon", "japón", "japan", "tokyo"],
    "japón": ["japon", "japón", "japan", "tokyo"],
    "japan": ["japon", "japón", "japan", "tokyo"],
    "espana": ["españa", "espana", "spain", "madrid", "barcelona"],
    "españa": ["españa", "espana", "spain", "madrid", "barcelona"],
    "spain": ["españa", "espana", "spain", "madrid", "barcelona"],
    "estados unidos": ["estados unidos", "united states", "usa", "us"],
    "united states": ["estados unidos", "united states", "usa", "us"],
    "reino unido": ["reino unido", "united kingdom", "uk", "great britain", "england", "london"],
    "united kingdom": ["reino unido", "united kingdom", "uk", "great britain", "england", "london"],
    "paises bajos": ["paises bajos", "países bajos", "netherlands", "holland", "amsterdam"],
    "países bajos": ["paises bajos", "países bajos", "netherlands", "holland", "amsterdam"],
    "netherlands": ["paises bajos", "países bajos", "netherlands", "holland", "amsterdam"],
    "brasil": ["brasil", "brazil", "sao paulo", "rio"],
    "brazil": ["brasil", "brazil", "sao paulo", "rio"],
    "mexico": ["mexico", "méxico"],
    "méxico": ["mexico", "méxico"],
    "canada": ["canada", "canadá", "toronto", "vancouver", "montreal"],
    "canadá": ["canada", "canadá", "toronto", "vancouver", "montreal"],
    "italia": ["italia", "italy", "rome", "milan"],
    "italy": ["italia", "italy", "rome", "milan"],
    "francia": ["francia", "france", "paris"],
    "france": ["francia", "france", "paris"],
    "suecia": ["suecia", "sweden", "stockholm"],
    "sweden": ["suecia", "sweden", "stockholm"],
    "suiza": ["suiza", "switzerland", "zurich", "geneva"],
    "switzerland": ["suiza", "switzerland", "zurich", "geneva"],
    "irlanda": ["irlanda", "ireland", "dublin"],
    "ireland": ["irlanda", "ireland", "dublin"],
    "polonia": ["polonia", "poland", "warsaw"],
    "poland": ["polonia", "poland", "warsaw"],
    "portugal": ["portugal", "lisbon", "porto"],
    "noruega": ["noruega", "norway", "oslo"],
    "norway": ["noruega", "norway", "oslo"],
    "dinamarca": ["dinamarca", "denmark", "copenhagen"],
    "denmark": ["dinamarca", "denmark", "copenhagen"],
    "finlandia": ["finlandia", "finland", "helsinki"],
    "finland": ["finlandia", "finland", "helsinki"],
    "belgica": ["bélgica", "belgica", "belgium", "brussels"],
    "bélgica": ["bélgica", "belgica", "belgium", "brussels"],
    "belgium": ["bélgica", "belgica", "belgium", "brussels"],
    "austria": ["austria", "vienna"],
    "republica checa": ["república checa", "republica checa", "czech republic", "czechia", "prague"],
    "república checa": ["república checa", "republica checa", "czech republic", "czechia", "prague"],
    "czech republic": ["república checa", "republica checa", "czech republic", "czechia", "prague"],
    "corea del sur": ["corea del sur", "south korea", "korea", "seoul"],
    "south korea": ["corea del sur", "south korea", "korea", "seoul"],
    "emiratos arabes unidos": ["emiratos árabes unidos", "emiratos arabes unidos", "united arab emirates", "uae", "dubai", "abu dhabi"],
    "emiratos árabes unidos": ["emiratos árabes unidos", "emiratos arabes unidos", "united arab emirates", "uae", "dubai", "abu dhabi"],
    "united arab emirates": ["emiratos árabes unidos", "emiratos arabes unidos", "united arab emirates", "uae", "dubai", "abu dhabi"],
    "nueva zelanda": ["nueva zelanda", "new zealand", "auckland"],
    "new zealand": ["nueva zelanda", "new zealand", "auckland"],
    "sudafrica": ["sudáfrica", "sudafrica", "south africa", "cape town", "johannesburg"],
    "sudáfrica": ["sudáfrica", "sudafrica", "south africa", "cape town", "johannesburg"],
    "south africa": ["sudáfrica", "sudafrica", "south africa", "cape town", "johannesburg"],
    "singapur": ["singapur", "singapore"],
    "singapore": ["singapur", "singapore"],
    "filipinas": ["filipinas", "philippines", "manila"],
    "philippines": ["filipinas", "philippines", "manila"],
    "ucrania": ["ucrania", "ukraine", "kyiv"],
    "ukraine": ["ucrania", "ukraine", "kyiv"],
    "peru": ["perú", "peru", "lima"],
    "perú": ["perú", "peru", "lima"],
    "uruguay": ["uruguay", "montevideo"],
    "argentina": ["argentina", "buenos aires"],
    "chile": ["chile", "santiago"],
    "colombia": ["colombia", "bogota", "bogotá", "medellin", "medellín"],
}

ROLE_ACRONYM_MAP = {
    "qa": re.compile(r"\b(qa|quality\s+assurance)\b", re.IGNORECASE),
    "quality assurance": re.compile(r"\b(qa|quality\s+assurance)\b", re.IGNORECASE),
    "qc": re.compile(r"\b(qc|quality\s+control)\b", re.IGNORECASE),
    "quality control": re.compile(r"\b(qc|quality\s+control)\b", re.IGNORECASE),
    "qe": re.compile(r"\b(qe|quality\s+engineer(?:ing)?)\b", re.IGNORECASE),
    "quality engineer": re.compile(r"\b(qe|quality\s+engineer(?:ing)?)\b", re.IGNORECASE),
    "quality engineering": re.compile(r"\b(qe|quality\s+engineer(?:ing)?)\b", re.IGNORECASE),
    "qia": re.compile(r"\b(qia|quality\s+(?:ai|ia)|(?:ai|ia)\s+(?:qa|quality))\b", re.IGNORECASE),
    "quality ai": re.compile(r"\b(qia|quality\s+(?:ai|ia)|(?:ai|ia)\s+(?:qa|quality))\b", re.IGNORECASE),
    "quality ia": re.compile(r"\b(qia|quality\s+(?:ai|ia)|(?:ai|ia)\s+(?:qa|quality))\b", re.IGNORECASE),
    "ai qa": re.compile(r"\b(qia|quality\s+(?:ai|ia)|(?:ai|ia)\s+(?:qa|quality))\b", re.IGNORECASE),
    "sdet": re.compile(r"\b(sdet|software\s+(?:development\s+)?engineer\s+in\s+test)\b", re.IGNORECASE),
    "software engineer in test": re.compile(r"\b(sdet|software\s+(?:development\s+)?engineer\s+in\s+test)\b", re.IGNORECASE),
    "software development engineer in test": re.compile(r"\b(sdet|software\s+(?:development\s+)?engineer\s+in\s+test)\b", re.IGNORECASE),
    "test": re.compile(r"\b(tests?|testers?|testing)\b", re.IGNORECASE),
    "tester": re.compile(r"\b(tests?|testers?|testing)\b", re.IGNORECASE),
    "testing": re.compile(r"\b(tests?|testers?|testing)\b", re.IGNORECASE),
    "automation": re.compile(r"\b(automation|automated)\b", re.IGNORECASE),
    "quality": re.compile(r"\bquality\b", re.IGNORECASE),
}

GENERIC_ROLE_WORDS = {
    "engineer", "engineering", "senior", "sr", "junior", "jr", "lead", "staff",
    "principal", "manager", "analyst", "specialist", "developer", "software",
    "architect", "intern", "director", "vp", "head", "in", "and", "of", "for",
    "to", "ii", "iii", "iv", "mid", "tech", "level", "team", "group", "associate",
    "consultant", "expert",
}
