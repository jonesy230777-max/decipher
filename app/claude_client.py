"""Claude API wrapper for Decipher.

Two public functions:
  complete_structured  – Haiku 4.5, returns validated JSON dict via forced tool use
  complete_narrative   – Opus 4.7, returns plain text with adaptive thinking

Every call is logged to events_log (action='claude_api_call').
"""
from __future__ import annotations

import os
from typing import Any

import anthropic

from app.db import event

OPUS = "claude-opus-4-7"
HAIKU = "claude-haiku-4-5"

_COST_PER_M: dict[str, dict[str, float]] = {
    OPUS:  {"input": 5.00,  "output": 25.00},
    HAIKU: {"input": 1.00,  "output": 5.00},
}

_CACHE_THRESHOLD = 2_000  # chars; cache system prompts longer than this

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


class ClaudeCallError(Exception):
    """Raised when a Claude API call fails."""


def _log(model: str, input_tokens: int, output_tokens: int) -> None:
    rates = _COST_PER_M.get(model, {"input": 0.0, "output": 0.0})
    cost_usd = (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000
    event(
        "claude_api_call",
        actor="system",
        payload={
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(cost_usd, 6),
        },
    )


def complete_structured(
    prompt: str,
    schema: dict[str, Any],
    *,
    model: str = HAIKU,
) -> dict[str, Any]:
    """Call Claude with a forced tool-use pattern to get structured JSON.

    Args:
        prompt: The user message.
        schema: JSON Schema dict describing the expected output object.
        model: Defaults to Haiku 4.5.

    Returns:
        Dict matching the schema (tool input block from Claude).

    Raises:
        ClaudeCallError: On API error or unexpected response shape.
    """
    client = _get_client()
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=4096,
            tools=[
                {
                    "name": "structured_output",
                    "description": "Return the structured output exactly as specified.",
                    "input_schema": schema,
                }
            ],
            tool_choice={"type": "tool", "name": "structured_output"},
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError as exc:
        raise ClaudeCallError(f"Claude API error ({model}): {exc}") from exc

    _log(model, resp.usage.input_tokens, resp.usage.output_tokens)

    for block in resp.content:
        if block.type == "tool_use" and block.name == "structured_output":
            return block.input  # type: ignore[return-value]

    raise ClaudeCallError(f"No structured_output tool call in response from {model}")


def complete_narrative(
    system: str,
    user: str,
    *,
    model: str = OPUS,
) -> str:
    """Call Claude for a plain-text narrative with adaptive thinking.

    Caches the system prompt when it exceeds _CACHE_THRESHOLD characters to
    amortise cost across repeated report generation calls.

    Args:
        system: System prompt (persona + report context, typically large).
        user: User turn (respondent scores + archetype for this call).
        model: Defaults to Opus 4.7.

    Returns:
        Plain text string (thinking blocks excluded, text blocks concatenated).

    Raises:
        ClaudeCallError: On API error.
    """
    client = _get_client()

    system_content: list[dict[str, Any]] | str
    if len(system) > _CACHE_THRESHOLD:
        system_content = [
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }
        ]
    else:
        system_content = system

    kwargs: dict[str, Any] = dict(
        model=model,
        max_tokens=8192,
        system=system_content,
        messages=[{"role": "user", "content": user}],
    )
    if model == OPUS:
        kwargs["thinking"] = {"type": "adaptive"}

    try:
        resp = client.messages.create(**kwargs)
    except anthropic.APIError as exc:
        raise ClaudeCallError(f"Claude API error ({model}): {exc}") from exc

    _log(model, resp.usage.input_tokens, resp.usage.output_tokens)

    text_parts = [b.text for b in resp.content if hasattr(b, "text") and b.text]
    if not text_parts:
        raise ClaudeCallError(f"No text content in response from {model}")
    return "".join(text_parts)
