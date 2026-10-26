"""
Isolated LLM agent adapter for answering custom form questions.
Integrates Claude or Agy CLI to generate direct, human, factual answers.
"""

import os
import shutil
import asyncio
from typing import Optional

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

def _read_ai_settings() -> dict:
    try:
        from pathlib import Path
        import json
        cfg_path = Path(__file__).resolve().parent.parent.parent / "config" / "ai_settings.json"
        if cfg_path.exists():
            return json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def _query_api_sync(prompt: str, settings: dict) -> str:
    import json
    import urllib.request

    ant_key = settings.get("anthropicApiKey") or os.environ.get("ANTHROPIC_API_KEY", "")
    if ant_key and ant_key.startswith("sk-ant-"):
        try:
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=json.dumps({
                    "model": "claude-3-5-sonnet-20241022",
                    "max_tokens": 1024,
                    "messages": [{"role": "user", "content": prompt}],
                }).encode("utf-8"),
                headers={
                    "x-api-key": ant_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("content", [{}])[0].get("text", "").strip()
        except Exception:
            pass

    oai_key = settings.get("openaiApiKey") or os.environ.get("OPENAI_API_KEY", "")
    if oai_key and oai_key.startswith("sk-"):
        try:
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=json.dumps({
                    "model": "gpt-4o",
                    "messages": [{"role": "user", "content": prompt}],
                }).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {oai_key}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        except Exception:
            pass

    gem_key = settings.get("geminiApiKey") or os.environ.get("GEMINI_API_KEY", "")
    if gem_key and len(gem_key) > 15:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gem_key}"
            req = urllib.request.Request(
                url,
                data=json.dumps({
                    "contents": [{"parts": [{"text": prompt}]}],
                }).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "").strip()
        except Exception:
            pass

    ds_key = settings.get("deepseekApiKey") or os.environ.get("DEEPSEEK_API_KEY", "")
    if ds_key and ds_key.startswith("sk-"):
        try:
            req = urllib.request.Request(
                "https://api.deepseek.com/v1/chat/completions",
                data=json.dumps({
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                }).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {ds_key}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        except Exception:
            pass

    kimi_key = settings.get("kimiApiKey") or os.environ.get("KIMI_API_KEY", "")
    if kimi_key and kimi_key.startswith("sk-"):
        try:
            req = urllib.request.Request(
                "https://api.moonshot.cn/v1/chat/completions",
                data=json.dumps({
                    "model": "moonshot-v1-8k",
                    "messages": [{"role": "user", "content": prompt}],
                }).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {kimi_key}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        except Exception:
            pass

    custom_url = settings.get("customOpenAiBaseUrl", "").strip()
    custom_key = settings.get("customOpenAiApiKey", "").strip()
    custom_model = settings.get("customOpenAiModel", "").strip() or "gpt-4o"
    if custom_url:
        endpoint = custom_url.rstrip("/")
        if not endpoint.endswith("/chat/completions"):
            endpoint = f"{endpoint}/chat/completions"
        try:
            headers = {"Content-Type": "application/json"}
            if custom_key:
                headers["Authorization"] = f"Bearer {custom_key}"
            req = urllib.request.Request(
                endpoint,
                data=json.dumps({
                    "model": custom_model,
                    "messages": [{"role": "user", "content": prompt}],
                }).encode("utf-8"),
                headers=headers,
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        except Exception:
            pass

    return ""

def _find_cli_bin(name: str) -> Optional[str]:
    env_var = f"{name.upper()}_BIN"
    if os.environ.get(env_var):
        return os.environ.get(env_var)
    return shutil.which(name)

async def query_model(prompt: str, preferred_provider: str = "auto", timeout: int = 35) -> str:
    """Query direct API or local LLM CLI with timeout and fallback."""
    settings = _read_ai_settings()
    if settings.get("anthropicApiKey") or settings.get("openaiApiKey") or settings.get("geminiApiKey"):
        try:
            api_res = await asyncio.to_thread(_query_api_sync, prompt, settings)
            if api_res:
                return api_res
        except Exception:
            pass

    provider = os.environ.get("AGENT_PROVIDER", "auto") if preferred_provider == "auto" else preferred_provider
    order = ["agy", "claude", "codex"] if provider in ("auto", "agy") else ["claude", "agy", "codex"]

    for cli in order:
        bin_path = _find_cli_bin(cli)
        if not bin_path:
            continue
        try:
            if cli == "agy":
                cmd = [bin_path, "--output-format", "text", "--disable-slash-commands", "--dangerously-skip-permissions", "-p", prompt]
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
            elif cli == "codex":
                cmd = [bin_path, "exec", "--no-tools", prompt]
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
        except Exception:
            continue

    return ""

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

    req_clause = ""
    if is_required:
        req_clause = "\nCRITICAL REQUIREMENT: This question is MANDATORY/REQUIRED (*) by the employer. You must provide a complete, clear, and professional response that directly answers the question without leaving it blank."

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
