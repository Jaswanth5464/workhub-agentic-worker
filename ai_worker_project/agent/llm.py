"""
LLM Adapter and Fallback Chain.

Phase 2: Handles communication with multiple LLM providers, structured output
parsing (JSON repair), and automatic fallback on 429/timeout errors.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

import httpx
from config.loader import settings as _cfg

logger = logging.getLogger(__name__)

def get_fallback_chain(complexity: str = "medium") -> List[str]:
    """Returns a provider chain optimized for the requested complexity, respecting config."""
    env_chain = os.environ.get("LLM_FALLBACK_PROVIDERS")
    if env_chain:
        return [p.strip() for p in env_chain.split(",") if p.strip()]
        
    cfg_chain = None
    if hasattr(_cfg, 'llm') and isinstance(_cfg.llm, dict):
        cfg_chain = _cfg.llm.get("fallback_providers")
    elif hasattr(_cfg, 'llm') and hasattr(_cfg.llm, 'fallback_providers'):
        cfg_chain = _cfg.llm.fallback_providers

    if cfg_chain:
        return [p.strip() for p in cfg_chain.split(",") if p.strip()]
        
    # Dynamically build based on which API keys are actually present in the environment!
    chain = []
    if os.environ.get("LLM_API_KEY"): # Groq
        chain.append("groq")
    if os.environ.get("OPENROUTER_API_KEY"):
        chain.append("openrouter")
    if os.environ.get("MISTRAL_API_KEY"):
        chain.append("mistral")
    if os.environ.get("GEMINI_API_KEY"):
        chain.append("gemini")
    if os.environ.get("NVIDIA_API_KEY"):
        chain.append("nvidia")
    if os.environ.get("OLLAMA_BASE_URL"):
        chain.append("ollama")
        
    # If no specific keys were found, default to trying groq, openrouter, and mistral first
    if not chain:
        return ["groq", "openrouter", "mistral", "nvidia", "gemini"]
        
    return chain


class LLMError(Exception):
    """Base exception for LLM failures."""
    pass


class RateLimitError(LLMError):
    """Raised when the provider rate limits (429)."""
    pass


class TimeoutError(LLMError):
    """Raised when the provider times out."""
    pass


async def _call_openai_compatible(
    base_url: str,
    api_key: str,
    model: str,
    system_prompt: str,
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int,
    timeout: int
) -> str:
    """Generic async caller for OpenAI-compatible APIs (NVIDIA, Groq, Ollama)."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    
    # Format messages
    api_messages = []
    if system_prompt:
        api_messages.append({"role": "system", "content": system_prompt})
    api_messages.extend(messages)

    payload = {
        "model": model,
        "messages": api_messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(base_url, headers=headers, json=payload)
        except httpx.TimeoutException:
            raise TimeoutError(f"Timeout calling {base_url}")
        except httpx.RequestError as e:
            raise LLMError(f"Request error: {e}")

        if response.status_code == 429:
            raise RateLimitError(f"Rate limited by {base_url}")
        elif response.status_code != 200:
            try:
                err_data = response.json()
                err_obj = err_data.get("error", {})
                if err_obj.get("code") == "tool_use_failed" and "failed_generation" in err_obj:
                    fg = err_obj["failed_generation"]
                    try:
                        tool_call = json.loads(fg)
                        return json.dumps({
                            "thought": f"Executing {tool_call.get('name')}",
                            "action": {
                                "tool": tool_call.get("name"),
                                "args": tool_call.get("arguments", {})
                            }
                        })
                    except Exception:
                        return fg
            except Exception:
                pass
            raise LLMError(f"API error {response.status_code}: {response.text}")

        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise LLMError(f"Unexpected response structure: {data}")


async def call_nvidia(system_prompt: str, messages: List[Dict[str, str]], **kwargs) -> str:
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        raise LLMError("NVIDIA_API_KEY not set")
    model = os.environ.get("NVIDIA_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")
    return await _call_openai_compatible(
        base_url="https://integrate.api.nvidia.com/v1/chat/completions",
        api_key=api_key,
        model=model,
        system_prompt=system_prompt,
        messages=messages,
        temperature=kwargs.get("temperature", 0.0),
        max_tokens=kwargs.get("max_tokens", 4000),
        timeout=kwargs.get("timeout", int(os.environ.get("LLM_TIMEOUT_SECONDS", 120)))
    )


async def call_groq(system_prompt: str, messages: List[Dict[str, str]], **kwargs) -> str:
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        raise LLMError("LLM_API_KEY (Groq) not set")
    model = os.environ.get("LLM_MODEL", "llama-3.3-70b-versatile")
    return await _call_openai_compatible(
        base_url="https://api.groq.com/openai/v1/chat/completions",
        api_key=api_key,
        model=model,
        system_prompt=system_prompt,
        messages=messages,
        temperature=kwargs.get("temperature", 0.0),
        max_tokens=kwargs.get("max_tokens", 4000),
        timeout=kwargs.get("timeout", int(os.environ.get("LLM_TIMEOUT_SECONDS", 120)))
    )


async def call_ollama(system_prompt: str, messages: List[Dict[str, str]], **kwargs) -> str:
    base_url = os.environ.get("OLLAMA_BASE_URL") or _cfg.get("llm", {}).get("ollama_base_url")
    model = os.environ.get("OLLAMA_MODEL") or _cfg.get("llm", {}).get("ollama_model")
    if not base_url or not model:
        raise LLMError("Ollama base URL or model not configured.")
    
    api_messages = []
    if system_prompt:
        api_messages.append({"role": "system", "content": system_prompt})
    api_messages.extend(messages)
    
    async with httpx.AsyncClient(timeout=kwargs.get("timeout", 120)) as client:
        try:
            # Auto-detect model if configured model fails
            payload = {
                "model": model,
                "messages": api_messages,
                "stream": False,
                "options": {
                    "temperature": kwargs.get("temperature", 0.0),
                }
            }
            response = await client.post(f"{base_url}/api/chat", json=payload)
            if response.status_code == 404:
                # Fetch installed models from tags API
                tags_res = await client.get(f"{base_url}/api/tags")
                if tags_res.status_code == 200:
                    installed = [m.get("name") for m in tags_res.json().get("models", [])]
                    if installed:
                        model = installed[0]
                        payload["model"] = model
                        response = await client.post(f"{base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]
        except Exception as e:
            raise LLMError(f"Ollama failed: {e}")


async def call_gemini(system_prompt: str, messages: List[Dict[str, str]], **kwargs) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise LLMError("GEMINI_API_KEY not set")
    
    try:
        from google import genai
        # Setup using new genai client
        # In actual usage this defaults to GEMINI_API_KEY env var
        client = genai.Client(api_key=api_key)
        
        model_name = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
        
        # Reconstruct full prompt string since new client `interactions` uses simple strings
        # or we use generate_content
        full_prompt = system_prompt + "\n\n"
        for m in messages:
            full_prompt += f"{m['role'].upper()}: {m['content']}\n"
            
        # Using generate_content for simple request/response
        response = client.models.generate_content(
            model=model_name,
            contents=full_prompt
        )
        return response.text
    except Exception as e:
        if "429" in str(e):
            raise RateLimitError(f"Gemini rate limit: {e}")
        raise LLMError(f"Gemini failed: {e}")


async def call_openrouter(system_prompt: str, messages: List[Dict[str, str]], **kwargs) -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise LLMError("OPENROUTER_API_KEY not set")
    model = os.environ.get("OPENROUTER_MODEL", "apodex/apodex-1.1-mini:free")
    
    # Attempt primary model, fallback to :free or base if 404
    try:
        return await _call_openai_compatible(
            base_url="https://openrouter.ai/api/v1/chat/completions",
            api_key=api_key,
            model=model,
            system_prompt=system_prompt,
            messages=messages,
            temperature=kwargs.get("temperature", 0.0),
            max_tokens=kwargs.get("max_tokens", 4000),
            timeout=kwargs.get("timeout", int(os.environ.get("LLM_TIMEOUT_SECONDS", 120)))
        )
    except LLMError as e:
        if "404" in str(e):
            alt_model = "apodex/apodex-1.1-mini:free" if ":free" not in model else "apodex/apodex-1.1-mini"
            logger.info(f"OpenRouter 404 with {model}, trying alternative {alt_model}")
            return await _call_openai_compatible(
                base_url="https://openrouter.ai/api/v1/chat/completions",
                api_key=api_key,
                model=alt_model,
                system_prompt=system_prompt,
                messages=messages,
                temperature=kwargs.get("temperature", 0.0),
                max_tokens=kwargs.get("max_tokens", 4000),
                timeout=kwargs.get("timeout", int(os.environ.get("LLM_TIMEOUT_SECONDS", 120)))
            )
        raise


async def call_mistral(system_prompt: str, messages: List[Dict[str, str]], **kwargs) -> str:
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise LLMError("MISTRAL_API_KEY not set")
    model = os.environ.get("MISTRAL_MODEL", "open-mistral-7b")

    try:
        return await _call_openai_compatible(
            base_url="https://api.mistral.ai/v1/chat/completions",
            api_key=api_key,
            model=model,
            system_prompt=system_prompt,
            messages=messages,
            temperature=kwargs.get("temperature", 0.0),
            max_tokens=kwargs.get("max_tokens", 4000),
            timeout=kwargs.get("timeout", int(os.environ.get("LLM_TIMEOUT_SECONDS", 120)))
        )
    except RateLimitError:
        # If rate limited on mistral-small, try open-mistral-7b or codestral
        fallback_models = ["open-mistral-7b", "codestral-latest"]
        for fb_model in fallback_models:
            if fb_model != model:
                try:
                    return await _call_openai_compatible(
                        base_url="https://api.mistral.ai/v1/chat/completions",
                        api_key=api_key,
                        model=fb_model,
                        system_prompt=system_prompt,
                        messages=messages,
                        temperature=kwargs.get("temperature", 0.0),
                        max_tokens=kwargs.get("max_tokens", 4000),
                        timeout=kwargs.get("timeout", int(os.environ.get("LLM_TIMEOUT_SECONDS", 120)))
                    )
                except Exception:
                    continue
        raise


PROVIDERS = {
    "groq": call_groq,
    "openrouter": call_openrouter,
    "mistral": call_mistral,
    "nvidia": call_nvidia,
    "gemini": call_gemini,
    "ollama": call_ollama,
}


async def generate_response(
    system_prompt: str, 
    messages: List[Dict[str, str]], 
    require_json: bool = True,
    complexity: str = "medium"
) -> str:
    """
    Calls the LLM using the fallback chain.
    If require_json is True, ensures the response contains parsable JSON.
    """
    chain = get_fallback_chain(complexity)
    if not chain:
        chain = ["groq"]
        
    last_error = None
    
    for provider_name in chain:
        provider_fn = PROVIDERS.get(provider_name)
        if not provider_fn:
            logger.warning(f"Unknown provider in fallback chain: {provider_name}")
            continue
            
        logger.info(f"Attempting LLM call via {provider_name}")
        try:
            raw_response = await provider_fn(system_prompt, messages)
            
            if require_json:
                # Basic sanity check
                try:
                    extract_json(raw_response)
                    return raw_response
                except ValueError as ve:
                    # Model didn't return valid JSON. Raise so fallback tries next model.
                    raise LLMError(f"Invalid JSON returned: {ve}")
            
            return raw_response
            
        except (RateLimitError, TimeoutError) as e:
            logger.warning(f"{provider_name} failed with {type(e).__name__}: {e}. Trying next...")
            last_error = e
        except LLMError as e:
            logger.warning(f"{provider_name} failed: {e}. Trying next...")
            last_error = e
        except Exception as e:
            logger.exception(f"Unexpected error with {provider_name}: {e}")
            last_error = e
            
    raise LLMError(f"All providers in fallback chain failed. Last error: {last_error}")



# ─────────────────────────────────────────────────────────────────────────────
# Large Observation Handling
# ─────────────────────────────────────────────────────────────────────────────

# Max characters an observation may occupy before it gets summarized
OBS_MAX_CHARS = 1200
# Max rows to show in an inline sample when observation is truncated
OBS_SAMPLE_ROWS = 4
# How many recent history messages to keep intact; older ones get compressed
HISTORY_WINDOW = 4


def truncate_observation(observation: str) -> str:
    """
    Intelligently truncates a large observation so it fits within LLM context.

    Strategy (in order):
    1. If the observation is already small, return it as-is.
    2. If it looks like a list/table (JSON list or dict with a list), produce a
       structured summary: total_count, columns, and the first OBS_SAMPLE_ROWS rows.
    3. Otherwise, hard-truncate at OBS_MAX_CHARS and append a notice.
    """
    if len(observation) <= OBS_MAX_CHARS:
        return observation

    # ── Try JSON-structured summarization ────────────────────────────────────
    # Strip common "Success: " / "Observation from X:\n" prefixes before parsing
    prefix = ""
    json_payload = observation
    for marker in ("Success: ", "Failed: "):
        if observation.startswith(marker):
            prefix = marker
            json_payload = observation[len(marker):]
            break

    try:
        parsed = json.loads(json_payload)
    except (json.JSONDecodeError, ValueError):
        parsed = None

    if parsed is not None:
        # Detect list at top level
        rows: list | None = None
        extra_meta: dict = {}

        if isinstance(parsed, list):
            rows = parsed
        elif isinstance(parsed, dict):
            # Look for common list keys
            for key in ("rows", "items", "records", "data", "results", "records", "payables", "transactions"):
                if isinstance(parsed.get(key), list):
                    rows = parsed[key]
                    extra_meta = {k: v for k, v in parsed.items() if k != key}
                    break

        if rows is not None:
            total = len(rows)
            sample = rows[:OBS_SAMPLE_ROWS]
            columns = list(sample[0].keys()) if sample and isinstance(sample[0], dict) else []

            summary_parts = [
                f"[DATA SUMMARY — {total} record(s) returned, showing first {min(total, OBS_SAMPLE_ROWS)}]"
            ]
            if columns:
                summary_parts.append(f"Columns: {', '.join(columns)}")
            if extra_meta:
                summary_parts.append(f"Metadata: {json.dumps(extra_meta)}")
            summary_parts.append("Sample rows:")
            for i, row in enumerate(sample, 1):
                summary_parts.append(f"  {i}. {json.dumps(row)}")
            if total > OBS_SAMPLE_ROWS:
                summary_parts.append(
                    f"  ... {total - OBS_SAMPLE_ROWS} more row(s) omitted to conserve context."
                )

            return prefix + "\n".join(summary_parts)

        # It's a large dict but no recognizable list key — just stringify & truncate
        summary = json.dumps(parsed)
        if len(summary) > OBS_MAX_CHARS:
            summary = summary[:OBS_MAX_CHARS] + f"\n... [truncated — full response was {len(summary)} chars]"
        return prefix + summary

    # ── Fallback: hard truncate string ───────────────────────────────────────
    truncated = observation[:OBS_MAX_CHARS]
    return truncated + f"\n... [truncated — full response was {len(observation)} chars. Use a more specific query or filter to reduce data.]"


def prune_history_for_context(history: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Keeps the last HISTORY_WINDOW messages intact; compresses older observation
    messages to a single-line summary so they don't bloat the context window.

    The first user message (the original task) is always preserved in full.
    """
    if len(history) <= HISTORY_WINDOW + 1:
        return history  # nothing to prune

    preserved_head = history[:1]   # always keep the original task
    tail = history[-(HISTORY_WINDOW):]
    middle = history[1:-(HISTORY_WINDOW)]

    compressed_middle = []
    for msg in middle:
        if msg["role"] == "user" and msg["content"].startswith("Observation"):
            # Extract first line as summary
            first_line = msg["content"].split("\n")[0]
            compressed_middle.append({
                "role": "user",
                "content": f"[COMPRESSED] {first_line}"
            })
        else:
            compressed_middle.append(msg)

    return preserved_head + compressed_middle + tail


import json_repair

def extract_json(text: str) -> Dict[str, Any]:
    """
    Robust JSON extraction from LLM output using json-repair.
    """
    # 1. Find json block if it exists
    block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if block_match:
        content = block_match.group(1)
    else:
        # Fallback: find the first { and last }
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            content = text[start:end+1]
        else:
            content = text
            
    # Use json_repair to parse and fix any structural issues
    try:
        parsed = json_repair.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError("Parsed JSON is not a dictionary")
        return parsed
    except Exception as e:
        raise ValueError(f"Failed to parse JSON even with json-repair: {e}\nContent was: {content}")
