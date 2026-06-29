# jury.py — jury that evaluates the conclusions of multiple detectives.
# This is an ACTOR: single LLM call, no loop, no autonomous decisions.

import json
import config
import llm_client
import live

from rich.console import Console
console = Console()

SYSTEM_PROMPT = """You are the chair of an investigative commission.
You have received the verdicts of multiple detectives who investigated the same case independently.
Your task is to evaluate their conclusions and issue the final verdict.

Be fast. Reason briefly and internally — do NOT write long step-by-step
deliberations or any <think>/<reasoning> block. Keep the "thought" field short,
then give the verdict.

Evaluation criteria:
- Strength of reasoning matters more than numerical majority
- A forced verdict (detective that exhausted their steps) is worth less than an autonomous one
- A detailed and coherent justification is worth more than a vague one, even if shared

Respond in the same language as the detective conclusions you receive.
Reply ONLY with valid JSON:
{
  "thought": "reasoning about the quality of evidence brought by each detective",
  "conclusion": "full name of the culprit",
  "reason": "explanation of why you chose this verdict",
  "consenso": "unanimous / majority / minority"
}"""


def chiedi_giuria(conclusions):
    """
    Receives a list of detective conclusions and returns the final verdict.
    Each conclusion has: detective, conclusion, reason, forzato.
    """
    summary = ""
    for i, c in enumerate(conclusions, 1):
        forced_str = " [FORCED VERDICT — steps exhausted]" if c.get("forzato") else ""
        summary += (
            f"Detective {i} — {c['detective'].upper()}{forced_str}\n"
            f"Accusation: {c['conclusion']}\n"
            f"Justification: {c['reason']}\n\n"
        )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": f"Verdicts received:\n\n{summary}Issue the final verdict."},
    ]

    console.print("[dim]Jury deliberating...[/dim]")
    live.stream_begin("jury")
    try:
        text = llm_client.call_llm(
            messages    = messages,
            model       = config.DETECTIVE_MODEL,
            temperature = 0.2,
            max_tokens  = config.MAX_TOKENS,
            on_token    = live.token_cb,
        )
    finally:
        live.stream_end()

    # Robust parsing: extract the first balanced JSON ignoring extra text
    # (same approach as detective_agent.py — needed with thinking models)
    try:
        start = text.index("{")
    except ValueError:
        raise RuntimeError(f"The jury did not produce valid JSON:\n{text[:300]}")
    depth     = 0
    in_string = False
    escape    = False
    for i, c in enumerate(text[start:], start):
        if escape:
            escape = False; continue
        if c == "\\" and in_string:
            escape = True; continue
        if c == '"':
            in_string = not in_string; continue
        if in_string:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i+1])
                except json.JSONDecodeError as e:
                    raise RuntimeError(f"The jury did not produce valid JSON: {e}\n{text[:300]}")
    raise RuntimeError(f"The jury did not produce balanced JSON:\n{text[:300]}")
