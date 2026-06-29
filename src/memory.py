# memory.py — context management for agents with long conversations.
# Implements context compression: when messages exceed a threshold,
# summarizes older ones into a compact block and keeps only the recent ones.
# Used by detective_agent.py and suspect_agent.py — transparent to the agent.

import config
import llm_client

SYSTEM_PROMPT_SUMMARY = """You are an assistant specialized in summarizing conversations.
You receive a sequence of messages and produce a compact but faithful summary.
Preserve all important factual information.
Reply ONLY with the summary text — no JSON, no prefixes."""


def _summarize(text, context_label="conversation"):
    """Single LLM call to compress text. Actor — no loop."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_SUMMARY},
        {"role": "user",   "content": f"Summarize this {context_label}, preserving all important facts:\n\n{text}"},
    ]
    return llm_client.call_llm(
        messages    = messages,
        model       = config.DETECTIVE_MODEL,
        temperature = 0.2,
        max_tokens  = 2048,
    )


def comprimi_messaggi(messages, soglia, contesto="conversation"):
    """
    If the message list exceeds the threshold, compresses older messages into a summary.
    Handles two cases:
    - messages with a system prompt at position 0 (detective)
    - messages without a system prompt (suspect history)
    Returns the compressed list, or unchanged if below threshold.
    """
    if len(messages) <= soglia:
        return messages

    recent_n   = config.MESSAGGI_RECENTI
    has_system = messages[0]["role"] == "system"

    if has_system:
        system_msg  = messages[0]
        to_compress = messages[1:-recent_n]
        recent      = messages[-recent_n:]
    else:
        system_msg  = None
        to_compress = messages[:-recent_n]
        recent      = messages[-recent_n:]

    if not to_compress:
        return messages

    # Build the text to summarize — truncate very long messages
    text = "\n".join(
        f"{m['role'].upper()}: {m['content'][:500]}"
        for m in to_compress
    )

    print(f"[memory] Compressing {len(to_compress)} messages ({contesto})...")
    summary = _summarize(text, contesto)

    summary_msg = {
        "role":    "user",
        "content": f"[SUMMARY OF PREVIOUS CONTEXT]:\n{summary}",
    }

    if has_system:
        return [system_msg, summary_msg] + recent
    else:
        return [summary_msg] + recent
