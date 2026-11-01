"""
LLM client execution for job application automation.
Supports direct HTTP API calls (Anthropic, OpenAI, Gemini, DeepSeek, Kimi, Custom)
and local CLI fallbacks (Agy, Claude, Codex).
"""

import os
import shutil
import asyncio
from pathlib import Path
import json
from typing import Optional


def read_ai_settings() -> dict:
    """Read AI settings from config/ai_settings.json if present."""
    try:
        cfg_path = Path(__file__).resolve().parent.parent.parent / "config" / "ai_settings.json"
        if cfg_path.exists():
            return json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def query_api_sync(prompt: str, settings: dict) -> str:
    """Execute direct HTTP API query based on configured provider keys."""
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


def find_cli_bin(name: str) -> Optional[str]:
    """Resolve executable path for local CLI tools."""
    env_var = f"{name.upper()}_BIN"
    if os.environ.get(env_var):
        return os.environ.get(env_var)
    return shutil.which(name)


async def query_model(prompt: str, preferred_provider: str = "auto", timeout: int = 35) -> str:
    """Query direct API or local LLM CLI with timeout and fallback."""
    settings = read_ai_settings()
    if settings.get("anthropicApiKey") or settings.get("openaiApiKey") or settings.get("geminiApiKey"):
        try:
            api_res = await asyncio.to_thread(query_api_sync, prompt, settings)
            if api_res:
                return api_res
        except Exception:
            pass

    provider = os.environ.get("AGENT_PROVIDER", "auto") if preferred_provider == "auto" else preferred_provider
    order = ["agy", "claude", "codex"] if provider in ("auto", "agy") else ["claude", "agy", "codex"]

    for cli in order:
        bin_path = find_cli_bin(cli)
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
