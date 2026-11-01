"""
Isolated LLM agent adapter for answering custom form questions.
Integrates Claude, Agy, Codex CLI, or direct APIs to generate direct, human, factual answers.
"""

import re
from typing import Optional, List

from src.automation.ai_client import (
    read_ai_settings,
    query_api_sync,
    find_cli_bin,
    query_model,
)

# Backwards compatibility private aliases
_read_ai_settings = read_ai_settings
_query_api_sync = query_api_sync
_find_cli_bin = find_cli_bin

SYSTEM_RULES = """You are an application assistant for a job candidate.
CRITICAL EXECUTION RULE:
- DO NOT CALL ANY TOOLS OR RUN COMMANDS. DO NOT SEARCH THE FILESYSTEM.
- You are operating strictly as a text generator. Return only the final text answer.

CRITICAL RULES FOR WRITING ANSWERS:
1. STRICT TRUTH & FIDELITY: Ground answers strictly in the candidate's real profile and technical experience. Never invent companies, dates, degrees, or tools outside this profile.
2. HUMAN WRITING RULES (Wikipedia:Signs_of_AI_writing):
   - Never use AI vocabulary words: additionally, align with, boasts, bolstered, crucial, cutting-edge, deep dive, delve, diverse array, elevate, emphasizing, encompassing, enduring, enhance, enhancing, fostering, cultivating, garner, groundbreaking, highlight, highlighting, interplay, intricate, intricacies, landscape, leverage, leveraging, meticulous, meticulously, mission-critical, pivotal, profound, proven track record, renowned, resonate with, robust, rock-solid, seamlessly, showcase, showcasing, spearheaded, streamlined, tapestry, testament, underscore, underscoring, valuable insights, vibrant.
   - No superficial present-participle tails (-ing) at the end of sentences ("...integrated Playwright into GitHub Actions, ensuring high reliability"). End sentences with a period.
   - No puffery, legacy clichés, or significance statements ("stands as a testament", "plays a crucial role", "evolving landscape", "passion for excellence").
   - No negative parallelisms ("Not only X, but also Y", "Not X, but Y").
   - Use simple copulatives: is, are, has, uses, built, tested.
   - No em dashes ("—" or "--"). Use commas or parentheses.
   - Use straight quotes (" and '), never curly quotes.
3. CONCISENESS & DIRECTNESS:
   - Answer the exact question asked in English.
   - Keep answers strictly under 100 words.
   - Do not write filler openings ("Certainly!", "As a passionate QA engineer...", "In today's fast-paced...").
   - If the question asks about the company (e.g., "Why <Company>?"), focus on your interest in their product, their engineering standards, and why you want to work on their team.
   - If the question asks about the role (e.g., "Why this role?"), focus on your relevant experience, technical skills, and technical fit.
"""


async def answer_form_question(
    question_text: str,
    job_title: str = "",
    company: str = "",
    job_context: str = "",
    candidate_profile = None,
    is_required: bool = False,
) -> Optional[str]:
    """
    Generate a direct, factual answer for open-ended application questions
    grounded in the candidate's real profile and CV.
    """
    p_info = getattr(candidate_profile, "personal_info", None)
    search_crit = getattr(candidate_profile, "search_criteria", None)
    candidate_name = getattr(p_info, "full_name", None) or "Candidate"
    years = getattr(p_info, "years_of_experience", None) or 5
    keywords = getattr(search_crit, "keywords", None)
    skills_context = f"CORE SKILLS: {', '.join(keywords)}." if keywords else ""
    target_role = job_title or (search_crit.target_roles[0] if (search_crit and getattr(search_crit, "target_roles", None)) else "Software Professional")
    job_desc_summary = job_context[:800] if job_context else f"Role at {company or 'the company'}."

    req_clause = ""
    if is_required:
        req_clause = "\nCRITICAL REQUIREMENT: This question is MANDATORY/REQUIRED (*) by the employer. You must provide a complete, clear, and professional response that directly answers the question without leaving it blank."

    prompt = f"""{SYSTEM_RULES}

CANDIDATE: {candidate_name} ({years}+ years of professional experience).
{skills_context}
TARGET COMPANY: {company or "Target Company"}
TARGET ROLE: {target_role}

QUESTION:
"{question_text}"

ADDITIONAL CONTEXT FROM JOB POSTING:
{job_desc_summary}

TASK:
Write a direct, factual answer in English for this specific question based on the candidate's profile.{req_clause}
Answer directly without pleasantries. Keep it under 100 words. End sentences with a period.
"""

    ans = await query_model(prompt)
    if not ans:
        return None

    # Clean markdown fences or surrounding quotes if returned by the model
    clean = ans.strip()
    if clean.startswith("```"):
        lines = clean.splitlines()
        clean = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:]).strip()
    if (clean.startswith('"') and clean.endswith('"')) or (clean.startswith("'") and clean.endswith("'")):
        clean = clean[1:-1].strip()

    return clean if len(clean) >= 10 else None


async def choose_radio_option(
    question_text: str,
    options: List[str],
    job_title: str = "",
    company: str = "",
    job_context: str = "",
    candidate_profile = None,
) -> Optional[str]:
    """
    Select the single most accurate option from a list of radio choices
    based on the candidate's real profile and CV.
    """
    if not question_text or not options:
        return None

    valid_options = [opt.strip() for opt in options if opt and opt.strip()]
    if not valid_options:
        return None

    p_info = getattr(candidate_profile, "personal_info", None)
    search_crit = getattr(candidate_profile, "search_criteria", None)
    candidate_name = getattr(p_info, "full_name", None) or "Candidate"
    years = getattr(p_info, "years_of_experience", None) or 5
    location = getattr(p_info, "location", None) or ""
    keywords = getattr(search_crit, "keywords", None)
    skills_context = f"CORE SKILLS: {', '.join(keywords)}." if keywords else ""
    target_role = job_title or (search_crit.target_roles[0] if (search_crit and getattr(search_crit, "target_roles", None)) else "Software Professional")
    oq = getattr(candidate_profile, "open_questions", None)
    exp_summary = getattr(oq, "experience_summary", None) if oq else None
    exp_context = f"CANDIDATE BACKGROUND: {exp_summary}." if exp_summary else ""

    options_list_str = "\n".join(f"{i+1}. {opt}" for i, opt in enumerate(valid_options))
    loc_str = f", based in {location}" if location else ""

    prompt = f"""{SYSTEM_RULES}

CANDIDATE: {candidate_name} ({years}+ years of professional experience{loc_str}).
{skills_context}
{exp_context}
TARGET COMPANY: {company or "Target Company"}
TARGET ROLE: {target_role}

QUESTION:
"{question_text}"

AVAILABLE OPTIONS:
{options_list_str}

TASK:
Select the single option from the list above that best and most truthfully reflects the candidate's professional experience and background.
Return ONLY the exact text of the selected option, with no additional commentary, no quotes, and no numbers.
"""

    ans = await query_model(prompt)
    if not ans:
        return None

    clean = ans.strip().strip('"').strip("'")

    # 1. Exact match (case insensitive)
    for opt in valid_options:
        if clean.lower() == opt.lower():
            return opt

    # 2. Numbered match (e.g., "1" or "Option 1" or "1. Yes")
    m_num = re.match(r"^(?:option\s+)?(\d+)(?:\.|\:|\s|$)", clean, re.IGNORECASE)
    if m_num:
        idx = int(m_num.group(1)) - 1
        if 0 <= idx < len(valid_options):
            return valid_options[idx]

    # 3. Substring match
    for opt in valid_options:
        if opt.lower() in clean.lower() or clean.lower() in opt.lower():
            return opt

    return None
