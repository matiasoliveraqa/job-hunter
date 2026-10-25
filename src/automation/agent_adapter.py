"""
Isolated LLM agent adapter for answering custom form questions.
Integrates Claude or Agy CLI to generate direct, human, factual answers.
"""

import os
import shutil
import asyncio
from typing import Optional

SYSTEM_RULES = """You are an application assistant for a job candidate.
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

def _find_cli_bin(name: str) -> Optional[str]:
    env_var = f"{name.upper()}_BIN"
    if os.environ.get(env_var):
        return os.environ.get(env_var)
    return shutil.which(name)

async def query_model(prompt: str, preferred_provider: str = "auto", timeout: int = 35) -> str:
    """Query local LLM CLI (agy or claude) with timeout and fallback."""
    provider = os.environ.get("AGENT_PROVIDER", "auto") if preferred_provider == "auto" else preferred_provider

    order = ["agy", "claude"] if provider in ("auto", "agy") else ["claude", "agy"]

    for cli in order:
        bin_path = _find_cli_bin(cli)
        if not bin_path:
            continue
        try:
            if cli == "agy":
                cmd = [bin_path, "--output-format", "text", "--disable-slash-commands", "--sandbox", "-p", prompt]
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
                if proc.returncode == 0 and stdout:
                    res = stdout.decode("utf-8").strip()
                    if res:
                        return res
            elif cli == "claude":
                cmd = [bin_path, "-p", "--output-format", "text", "--tools", "", "--no-session-persistence"]
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(input=prompt.encode("utf-8")), timeout=timeout)
                if proc.returncode == 0 and stdout:
                    res = stdout.decode("utf-8").strip()
                    if res:
                        return res
        except Exception:
            continue

    return ""

async def answer_form_question(
    question_text: str,
    job_title: str = "",
    company: str = "",
    job_context: str = "",
    candidate_profile = None,
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

    prompt = f"""{SYSTEM_RULES}

CANDIDATE: {candidate_name} ({years}+ years of professional engineering experience).
{skills_context}
TARGET COMPANY: {company or "Target Company"}
TARGET ROLE: {job_title or "QA Automation Engineer"}

QUESTION:
"{question_text}"

ADDITIONAL CONTEXT FROM JOB POSTING:
{job_context[:800] if job_context else "QA automation and software testing role."}

TASK:
Write a direct, factual answer in English for this specific question based on the candidate's profile.
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
