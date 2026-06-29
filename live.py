# live.py — optional live token streaming to the web UI.
#
# When the web server runs an agent as a subprocess it sets MM_STREAM=1.
# In that mode the agents stream the model output token-by-token; each token
# is written to stdout as a sentinel-framed JSON line that the server parses
# back into a Server-Sent Event. In normal terminal use MM_STREAM is unset,
# nothing is emitted, and the LLM calls stay non-streaming (current behaviour).

import os
import sys
import json

# Unit Separator — never appears in normal console output, so the server can
# tell a streaming event line apart from an ordinary log line.
SENTINEL = "\x1f"

STREAM = os.getenv("MM_STREAM") == "1"


def _emit(obj):
    if not STREAM:
        return
    sys.stdout.write(SENTINEL + json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def stream_begin(label=""):
    """Mark the start of a live generation (one LLM call)."""
    _emit({"type": "stream_begin", "label": label})


def stream_end():
    """Mark the end of a live generation."""
    _emit({"type": "stream_end"})


def on_token(text, kind="content"):
    """Token callback passed to llm_client. kind is 'thinking' or 'content'."""
    if text:
        _emit({"type": "token", "text": text, "kind": kind})


# Pass this to llm_client.call_llm(on_token=...) only when streaming is on:
# in terminal mode it stays None so the call keeps the non-streaming path.
token_cb = on_token if STREAM else None
