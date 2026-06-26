# detective_agent.py — detective ReAct loop.
# The detective reasons, picks a skill, observes the result, repeats.
# This is an AGENT: it decides autonomously when it has enough information.

import json
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

import config
import llm_client
import tools
import memory

console = Console()

# ── Dispatch dict — maps skill names to Python functions ──────────────
# Safe alternative to eval(). Adding a skill = adding one line.
SKILL = {
    "list_files":          tools.list_files,
    "read_file":           tools.read_file,
    "cross_check":         tools.cross_check,
    "take_note":           tools.take_note,
    "interrogate_suspect": tools.interrogate_suspect,
}

# ── Detective system prompt ───────────────────────────────────────────
SYSTEM_PROMPT = """You are a detective assigned to solve a criminal case.
You have access to a folder with the case files and can use these skills:

- list_files(case_dir): list the available files in the case
- read_file(case_dir, filename): read a case file
- cross_check(case_dir, file_a, file_b): compare two files together
- take_note(case_dir, key, value): save a deduction in your notebook
- interrogate_suspect(case_dir, suspect_name, question): interrogate a suspect

Always reply ONLY with valid JSON in one of these two formats:

ACTION format — when you want to use a skill:
{
  "thought": "your internal reasoning",
  "action": "skill_name",
  "args": { "argument": "value" }
}

CONCLUSION format — when you have decided on the culprit:
{
  "thought": "final reasoning",
  "conclusion": "name of the culprit",
  "reason": "detailed explanation"
}

General rules:
- Do not invent information — only use what you read in the files or hear in responses
- Interrogate suspects with specific questions, not generic ones
- Reply ONLY with JSON, no text before or after
- Write your "thought" and "reason" fields in the same language as the case content

Verification rules — MANDATORY before concluding:
1. When you have a first suspect, do NOT use CONCLUSION immediately.
   Save the hypothesis with take_note: key "ipotesi_1", value "name — reason"
2. Look for at least one piece of evidence that CONTRADICTS your hypothesis.
   If you find none, the hypothesis is strengthened. If you do, reassess everything.
3. Look for at least one piece of evidence that CONFIRMS the hypothesis from a source
   different from the one that made you suspicious.
4. Only after these three steps may you use the CONCLUSION format."""


def extract_json(text):
    """
    Extracts the first complete JSON object from the model's response.
    Uses brace counting instead of rindex("}") to handle cases where the model
    produces text or a second JSON object after the main one.
    """
    try:
        start = text.index("{")
    except ValueError:
        raise RuntimeError(f"No JSON found in response:\n{text[:300]}")

    depth     = 0
    in_string = False
    escape    = False
    for i, c in enumerate(text[start:], start):
        if escape:
            escape = False
            continue
        if c == "\\" and in_string:
            escape = True
            continue
        if c == '"':
            in_string = not in_string
            continue
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
                    raise RuntimeError(f"Response is not valid JSON: {e}\n{text[:300]}")

    raise RuntimeError(f"No balanced JSON found:\n{text[:300]}")


def write_log(log_path, entry):
    """Writes one step to the narrative log. Called at each step, not at the end."""
    if log_path.exists():
        log = json.loads(log_path.read_text(encoding="utf-8"))
    else:
        log = []
    log.append(entry)
    log_path.write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")


def run_detective(case_dir, profile=None):
    """
    Starts the detective ReAct loop on the given case.
    profile = {"nome": "methodical", "temperature": 0.2, "stile": "..."}
    If profile is None, uses config defaults (original behaviour).
    Returns the conclusion dict with extra fields: detective, forzato.
    """
    case_dir = Path(case_dir)

    # Parameters from profile or config defaults
    detective_name = profile["nome"]        if profile else "detective"
    temperature    = profile["temperature"] if profile else config.DETECTIVE_TEMPERATURE
    style          = profile.get("stile", "") if profile else ""
    notes_file     = f"note_{detective_name}.json"
    log_path       = case_dir / f"detective_log_{detective_name}.json"

    # System prompt — append detective style if present
    system_prompt = SYSTEM_PROMPT
    if style:
        system_prompt += f"\n\nYour investigative style: {style}"

    # Initialise log and interrogation histories
    log_path.write_text("[]", encoding="utf-8")
    histories = tools.init_session(case_dir)

    # Message list — this is the detective's memory
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": f"The case is in folder {case_dir}. Begin the investigation."},
    ]

    # Inject notes from previous detectives (if any exist)
    previous_notes = []
    for f in sorted(case_dir.glob("note_*.json")):
        if f.name != notes_file:
            content   = json.loads(f.read_text(encoding="utf-8"))
            prev_name = f.stem.replace("note_", "")
            previous_notes.append(
                f"[NOTES FROM {prev_name.upper()}]:\n{json.dumps(content, indent=2, ensure_ascii=False)}"
            )
    if previous_notes:
        messages.append({
            "role": "user",
            "content": "Before starting, read the notes from the detectives who preceded you:\n\n"
                       + "\n\n".join(previous_notes)
        })

    console.print(Panel(
        f"Investigation started — detective: [bold]{detective_name.upper()}[/bold]",
        style="bold red"
    ))

    for step in range(1, config.MAX_DETECTIVE_STEPS + 1):
        console.print(f"\n[dim]━━━ Step {step}/{config.MAX_DETECTIVE_STEPS} ━━━[/dim]")

        # ── Persistent memory compression ────────────────────────────
        # Threshold 1: message count
        messages = memory.comprimi_messaggi(
            messages,
            config.MAX_MESSAGGI_DETECTIVE,
            "detective investigation"
        )
        # Threshold 2: total characters (token proxy).
        # Triggers when messages are few but long (verbose interrogations).
        # threshold=0 forces compression regardless of count.
        total_chars = sum(len(m.get("content", "")) for m in messages)
        if total_chars > config.MAX_CHARS_DETECTIVE:
            console.print(
                f"[yellow]Payload too large ({total_chars} chars) — compressing before call...[/yellow]"
            )
            messages = memory.comprimi_messaggi(messages, 0, "detective investigation")

        # ── LLM call ─────────────────────────────────────────────────
        try:
            text = llm_client.call_llm(
                messages    = messages,
                model       = config.DETECTIVE_MODEL,
                temperature = temperature,
                max_tokens  = config.MAX_TOKENS,
            )
        except Exception as e:
            console.print(f"[red]LLM error at step {step}: {e}[/red]")
            continue

        # ── JSON parsing ─────────────────────────────────────────────
        try:
            response = extract_json(text)
        except RuntimeError as e:
            console.print(f"[red]{e}[/red]")
            continue

        # ── Print thought ─────────────────────────────────────────────
        thought = response.get("thought", "")
        console.print(Panel(thought, title="THOUGHT", style="bold yellow"))

        # ── CONCLUSION — detective has decided ────────────────────────
        if "conclusion" in response:
            console.print(Panel(
                f"Culprit: [bold]{response['conclusion']}[/bold]\n\n"
                f"{response['reason']}",
                title="CONCLUSION", style="bold yellow"
            ))
            write_log(log_path, {
                "step":       step,
                "thought":    thought,
                "conclusion": response["conclusion"],
                "reason":     response["reason"],
            })
            response["detective"] = detective_name
            response["forzato"]   = False
            return response

        # ── ACTION — detective wants to use a skill ───────────────────
        if "action" not in response:
            console.print("[red]Response has no action or conclusion — skipping.[/red]")
            continue

        action = response["action"]
        args   = response.get("args", {})

        console.print(f"[cyan]ACTION:[/cyan] {action}({args})")

        # Execute the skill
        if action not in SKILL:
            observation = f"ERROR: skill '{action}' does not exist."
        else:
            try:
                if action == "interrogate_suspect":
                    name = args.get("suspect_name", "")
                    key  = next((k for k in histories if k.lower() == name.lower()), name)
                    observation = SKILL[action](
                        args.get("case_dir", case_dir),
                        key,
                        args.get("question", ""),
                        histories[key],
                    )
                elif action == "take_note":
                    # Pass the detective-specific notes file
                    observation = tools.take_note(
                        case_dir,
                        args.get("key", ""),
                        args.get("value", ""),
                        notes_file=notes_file,
                    )
                else:
                    observation = SKILL[action](**{"case_dir": case_dir, **args})
            except Exception as e:
                observation = f"ERROR executing {action}: {e}"

        console.print(Panel(observation, title="OBSERVATION", style="cyan"))

        # ── Write log ─────────────────────────────────────────────────
        write_log(log_path, {
            "step":        step,
            "thought":     thought,
            "action":      action,
            "args":        args,
            "observation": observation,
        })

        # ── Update message list ───────────────────────────────────────
        messages.append({"role": "assistant", "content": text})
        messages.append({"role": "user",      "content": f"[OBSERVATION]: {observation}"})

    # Steps exhausted — request forced verdict
    console.print(f"[yellow]Steps exhausted — requesting forced verdict...[/yellow]")
    messages.append({
        "role": "user",
        "content": (
            "You have exhausted the available steps. "
            "Based on the evidence collected so far, "
            "issue your verdict in the CONCLUSION format. "
            "You must name one of the suspects!"
        )
    })

    messages = memory.comprimi_messaggi(
        messages,
        config.MAX_MESSAGGI_DETECTIVE,
        "final detective verdict"
    )

    text = llm_client.call_llm(
        messages    = messages,
        model       = config.DETECTIVE_MODEL,
        temperature = temperature,
        max_tokens  = config.MAX_TOKENS_FORZATO,
    )
    try:
        response = extract_json(text)
        thought  = response.get("thought", "")
        console.print(Panel(thought, title="THOUGHT", style="bold yellow"))
        console.print(Panel(
            f"Culprit: [bold]{response.get('conclusion', '?')}[/bold]\n\n"
            f"{response.get('reason', '')}",
            title="FORCED VERDICT", style="bold yellow"
        ))
        write_log(log_path, {
            "step":       config.MAX_DETECTIVE_STEPS + 1,
            "thought":    thought,
            "conclusion": response.get("conclusion", ""),
            "reason":     response.get("reason", ""),
            "forzato":    True,
        })
        response["detective"] = detective_name
        response["forzato"]   = True
        return response
    except RuntimeError:
        console.print("[red]The detective failed to produce a verdict.[/red]")
        return None


if __name__ == "__main__":
    # Accepts case path as argument: python detective_agent.py cases/caso_001
    if len(sys.argv) > 1:
        case_dir = Path(sys.argv[1])
    else:
        cases = sorted(config.CASES_DIR.glob("caso_*"))
        if not cases:
            print("Run first: python writer_agent.py")
            sys.exit(1)
        case_dir = cases[-1]

    run_detective(case_dir)
