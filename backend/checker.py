import json
import re
from difflib import SequenceMatcher

import httpx

from prompts import build_system_prompt, build_user_message


def _extract_json(text: str) -> dict:
    text = text.strip()
    if not text:
        raise ValueError("Empty model response")

    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fence:
        text = fence.group(1).strip()

    candidates = [text]
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        candidates.append(text[start : end + 1])

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
        except Exception:
            continue
    raise json.JSONDecodeError("no valid JSON object", text, 0)


def _salvage_corrected_line(text: str) -> str | None:
    """Pull corrected_line out of broken JSON the model emitted."""
    match = re.search(
        r'"corrected_line"\s*:\s*"((?:[^"\\]|\\.)*)"',
        text,
        re.DOTALL,
    )
    if not match:
        return None
    raw = match.group(1)
    try:
        return json.loads(f'"{raw}"')
    except json.JSONDecodeError:
        return raw.replace('\\"', '"').replace("\\n", " ").strip()


def _salvage_notes(text: str) -> list[str]:
    """Pull annotation/issue messages out of broken JSON."""
    messages = re.findall(r'"message"\s*:\s*"((?:[^"\\]|\\.)*)"', text, re.DOTALL)
    out = []
    for m in messages:
        try:
            out.append(json.loads(f'"{m}"'))
        except json.JSONDecodeError:
            out.append(m.replace('\\"', '"').strip())
    return out


_MD_BOLD = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
_MD_UNDER = re.compile(r"__(.+?)__", re.DOTALL)
_MD_ITALIC = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", re.DOTALL)


def _strip_markdown(text: str) -> str:
    """Remove the bold/italic/underline markers we send to the model."""
    text = _MD_BOLD.sub(r"\1", text)
    text = _MD_UNDER.sub(r"\1", text)
    text = _MD_ITALIC.sub(r"\1", text)
    return text


_TOKEN_RE = re.compile(r"\s+|\w+|[^\w\s]", re.UNICODE)


def _tokenize(text: str) -> list[tuple[str, int]]:
    """Split text into (token, start_offset) pairs preserving positions."""
    return [(m.group(0), m.start()) for m in _TOKEN_RE.finditer(text)]


def _issues_from_diff(original: str, corrected: str) -> list[dict]:
    """Word-level diff so suggestions read as whole words, not stray characters."""
    if original == corrected:
        return []

    orig_tokens = _tokenize(original)
    corr_tokens = _tokenize(corrected)
    orig_words = [t[0] for t in orig_tokens]
    corr_words = [t[0] for t in corr_tokens]

    matcher = SequenceMatcher(None, orig_words, corr_words, autojunk=False)
    raw_ops = [op for op in matcher.get_opcodes() if op[0] != "equal"]

    # Merge changes separated only by a single whitespace token for readability.
    merged: list[list] = []
    for op in raw_ops:
        if merged:
            prev = merged[-1]
            gap_words = orig_words[prev[2] : op[1]]
            if op[1] - prev[2] <= 1 and all(w.isspace() for w in gap_words):
                prev[2] = op[2]
                prev[4] = op[4]
                continue
        merged.append(list(op))

    issues: list[dict] = []
    for _tag, i1, i2, j1, j2 in merged:
        start = orig_tokens[i1][1] if i1 < len(orig_tokens) else len(original)
        if i2 > 0 and i2 <= len(orig_tokens):
            last_tok, last_start = orig_tokens[i2 - 1]
            end = last_start + len(last_tok)
        else:
            end = start
        if j2 > 0 and j2 <= len(corr_tokens):
            sugg_start = corr_tokens[j1][1] if j1 < len(corr_tokens) else len(corrected)
            sugg_last_tok, sugg_last_start = corr_tokens[j2 - 1]
            sugg_end = sugg_last_start + len(sugg_last_tok)
            suggestion = corrected[sugg_start:sugg_end]
        else:
            suggestion = ""

        issues.append(
            {
                "start": start,
                "end": end,
                "type": "grammar",
                "original": original[start:end],
                "suggestion": suggestion,
                "message": "",
            }
        )
    return issues


def _normalize_notes(annotations: list) -> list[dict]:
    """The AI's free-form explanations, kept separate from diff spans."""
    notes: list[dict] = []
    for ann in annotations or []:
        if isinstance(ann, str):
            text = ann.strip()
            if text:
                notes.append({"type": "note", "message": text})
        elif isinstance(ann, dict):
            message = (ann.get("message") or ann.get("text") or "").strip()
            if message:
                notes.append({"type": ann.get("type", "note"), "message": message})
    return notes


def _api_url(api_base: str) -> str:
    base = api_base.rstrip("/")
    if not base.endswith("/v1"):
        base = f"{base}/v1"
    return f"{base}/chat/completions"


def _headers(api_key: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _raise_api_error(response: httpx.Response) -> None:
    detail = response.text
    try:
        payload = response.json()
        if isinstance(payload, dict):
            detail = payload.get("error") or payload.get("message") or detail
            if isinstance(detail, dict):
                detail = detail.get("message") or str(detail)
    except Exception:
        pass
    raise RuntimeError(str(detail).strip() or f"API error {response.status_code}")


def _build_messages(
    *,
    strictness: int,
    target_line: str,
    line_number: int,
    context_before: list[str],
    context_after: list[str],
) -> list[dict[str, str]]:
    system = build_system_prompt(strictness)
    user = build_user_message(target_line, line_number, context_before, context_after)
    return [{"role": "user", "content": f"{system}\n\n{user}"}]


async def list_models(*, api_base: str, api_key: str = "", timeout: float = 15.0) -> list[str]:
    base = api_base.rstrip("/")
    if not base.endswith("/v1"):
        base = f"{base}/v1"
    url = f"{base}/models"
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url, headers=_headers(api_key))
        if response.is_error:
            _raise_api_error(response)
        data = response.json()
    models = []
    for item in data.get("data", []):
        model_id = item.get("id", "")
        if model_id and "embed" not in model_id.lower():
            models.append(model_id)
    return models


async def test_connection(*, api_base: str, model: str, api_key: str = "", timeout: float = 30.0) -> dict:
    url = _api_url(api_base)
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Reply with exactly: ok"}],
        "temperature": 0,
        "max_tokens": 16,
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=payload, headers=_headers(api_key))
        if response.is_error:
            _raise_api_error(response)
        data = response.json()
    message = data["choices"][0]["message"]
    content = (message.get("content") or message.get("reasoning_content") or "").strip()
    return {"ok": True, "model": model, "sample": content[:120] or "ready"}


async def check_line(
    *,
    target_line: str,
    line_number: int,
    context_before: list[str],
    context_after: list[str],
    strictness: int,
    api_base: str,
    model: str,
    api_key: str = "",
    timeout: float = 180.0,
) -> dict:
    url = _api_url(api_base)
    payload = {
        "model": model,
        "messages": _build_messages(
            strictness=strictness,
            target_line=target_line,
            line_number=line_number,
            context_before=context_before,
            context_after=context_after,
        ),
        "temperature": 0.2,
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=payload, headers=_headers(api_key))
        if response.is_error:
            _raise_api_error(response)
        data = response.json()

    message = data["choices"][0]["message"]
    content = (message.get("content") or message.get("reasoning_content") or "").strip()

    # target_line arrives as markdown (bold/italic markers) so the model is
    # aware of formatting; we diff on the plain-text form to keep offsets aligned
    # with what the editor renders.
    original = _strip_markdown(target_line)

    annotations: list = []
    corrected_md = None
    try:
        parsed = _extract_json(content)
        corrected_md = parsed.get("corrected_line")
        annotations = parsed.get("annotations") or parsed.get("issues") or []
        hint = parsed.get("hint")
    except Exception:
        # Broken JSON — salvage what we can rather than failing the paragraph.
        corrected_md = _salvage_corrected_line(content)
        annotations = _salvage_notes(content)
        hint = None

    if not isinstance(corrected_md, str) or not corrected_md.strip():
        corrected_md = target_line
    corrected = _strip_markdown(corrected_md)

    notes = _normalize_notes(annotations)

    # Guard against the model hallucinating an entirely different paragraph
    # (e.g. rewriting a heading like "1.04 // 2nd" into prose).
    ratio = SequenceMatcher(None, original, corrected).ratio()
    if corrected != original and ratio < 0.30 and len(corrected) > len(original) + 40:
        corrected = original
        notes = []
        hint = None

    issues = _issues_from_diff(original, corrected)

    if hint is not None and (not isinstance(hint, str) or not hint.strip()):
        hint = None

    return {
        "line_number": line_number,
        "original": original,
        "corrected": corrected,
        "issues": issues,
        "notes": notes,
        "hint": hint,
        "has_issues": len(issues) > 0 or corrected != original,
    }
