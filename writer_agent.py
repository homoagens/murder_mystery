# writer_agent.py — generates a Murder Mystery case from a brief.
# This is an ACTOR: single LLM call, no loop, no autonomous decisions.

import re
import json
from pathlib import Path

import config
import llm_client
import live


def _fix_json(raw: str) -> str:
    """Applies common fixes to LLM output before json.loads."""
    # remove trailing commas before } or ]
    raw = re.sub(r",\s*([}\]])", r"\1", raw)
    # remove line comments  // ...
    raw = re.sub(r"//[^\n]*", "", raw)
    # remove block comments /* ... */
    raw = re.sub(r"/\*.*?\*/", "", raw, flags=re.DOTALL)
    return raw


def extract_json(text):
    """
    Extracts the first complete JSON object from text by counting braces.
    Tries json.loads directly; if it fails, applies _fix_json and retries.
    """
    start = text.index("{")
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
                candidate = text[start:i+1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    return json.loads(_fix_json(candidate))

    raise ValueError("No balanced JSON found in text.")


def run_writer(brief=None):
    """
    Generates a complete case from a brief and saves it to cases/caso_NNN/.
    Returns the Path of the created folder.
    """

    # ── Collect parameters ───────────────────────────────────────────
    if brief is None:
        print("Describe the case to generate (press Enter for defaults):\n")

        ambientazione = input("Setting [signorile villa, 1930s]: ").strip()
        if not ambientazione:
            ambientazione = "villa signorile anni '30"

        n = input("Number of suspects [4]: ").strip()
        numero_sospettati = int(n) if n.isdigit() else 4

        crimine = input("Type of crime [omicidio]: ").strip()
        if not crimine:
            crimine = "omicidio"

        difficolta = input("Difficulty (facile/media/difficile) [media]: ").strip()
        if not difficolta:
            difficolta = "media"

        lingua = input("Language to write in [English]: ").strip()
        if not lingua:
            lingua = "English"

        # Extra fields — optional, omitted if empty
        atmosfera = input("Atmosphere/tone [press Enter to skip]: ").strip()
        tema      = input("Main theme [press Enter to skip]: ").strip()
        vincolo   = input("Narrative constraint [press Enter to skip]: ").strip()

    else:
        ambientazione     = brief.get("ambientazione",     "villa signorile anni '30")
        numero_sospettati = brief.get("numero_sospettati", 4)
        crimine           = brief.get("crimine",           "omicidio")
        difficolta        = brief.get("difficolta",        "media")
        lingua            = brief.get("lingua",            "English")
        atmosfera         = brief.get("atmosfera",         "")
        tema              = brief.get("tema",              "")
        vincolo           = brief.get("vincolo_narrativo", "")

    # ── Prompt ───────────────────────────────────────────────────────
    system_prompt = """You are a writer of Italian mystery stories. Generate a complete Murder Mystery case.
Reply ONLY with valid JSON, no text before or after.
Be fast: do NOT write any reasoning, planning, or <think>/<reasoning> block before
the JSON. Output the JSON object directly.

The structure must be exactly this:
{
  "caso": {
    "titolo": "...",
    "vittima": "...",
    "ambientazione": "...",
    "data_crimine": "..."
  },
  "sospettati": [
    {
      "nome": "...",
      "eta": 0,
      "ruolo": "...",
      "movente": "...",
      "alibi": "...",
      "alibi_verificabile": false,
      "carattere": "...",
      "sa_qualcosa": true,
      "mente": false,
      "cosa_nasconde": "..."
    }
  ],
  "indizi": [
    {
      "oggetto": "...",
      "location": "...",
      "rilevanza": "..."
    }
  ],
  "testimonianze": [
    {
      "testimone": "...",
      "dichiarazione": "..."
    }
  ],
  "soluzione": {
    "colpevole": "...",
    "spiegazione": "..."
  },
  "narrativa": "Write 4 paragraphs in detective novel style. Paragraph 1: describe the setting with sensory details (lights, smells, atmosphere). Paragraph 2: introduce the victim and the social context. Paragraph 3: describe the discovery of the crime with narrative tension. Paragraph 4: introduce the suspects with one sentence each suggesting their character. DO NOT reveal the culprit. Use the exact names of the characters defined in 'sospettati'. Write the narrative in the same language used in this request."
}

NOTE: the "cosa_nasconde" field must contain the character's real secret,
even if mente:false (in that case it can be an embarrassing detail unrelated
to the crime). Only those with mente:true hide something relevant."""

    user_prompt = (
        f"Generate a case with these characteristics:\n"
        f"- Setting: {ambientazione}\n"
        f"- Number of suspects: {numero_sospettati}\n"
        f"- Type of crime: {crimine}\n"
        f"- Difficulty: {difficolta}\n"
        f"- Language: {lingua}\n"
        f"\nWrite ALL the case content — every field value and the narrative — "
        f"in {lingua}. Keep the JSON keys exactly as specified (do not translate "
        f"the keys), but all the text values must be written in {lingua}.\n"
    )
    extra = {
        "Atmosphere/tone":      atmosfera,
        "Main theme":           tema,
        "Narrative constraint": vincolo,
    }
    extra_fields = {k: v for k, v in extra.items() if v}
    if extra_fields:
        user_prompt += "\nAdditional instructions:\n"
        for k, v in extra_fields.items():
            user_prompt += f"- {k}: {v}\n"

    user_prompt += "\nRemember: reply ONLY with valid JSON."

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_prompt},
    ]

    # ── LLM call with retry ───────────────────────────────────────────
    MAX_ATTEMPTS = 3
    data         = None
    last_error   = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        if attempt == 1:
            print("\nWriter working...")
        else:
            print(f"\nRetrying ({attempt}/{MAX_ATTEMPTS}) — malformed JSON: {last_error}")

        live.stream_begin("writer")
        try:
            text = llm_client.call_llm(
                messages    = messages,
                model       = config.WRITER_MODEL,
                temperature = config.WRITER_TEMPERATURE,
                max_tokens  = config.MAX_TOKENS,
                timeout     = config.WRITER_TIMEOUT,
                on_token    = live.token_cb,
            )
        finally:
            live.stream_end()

        try:
            data = extract_json(text)
            break  # parsing OK
        except (ValueError, json.JSONDecodeError) as e:
            last_error = str(e)
            # Append the error to guide the retry
            messages.append({"role": "assistant", "content": text})
            messages.append({"role": "user", "content":
                f"The JSON you generated is not valid: {e}\n"
                "Reply ONLY with valid JSON, no text before or after, "
                "no trailing commas, no comments."})

    if data is None:
        raise RuntimeError(
            f"The writer did not produce valid JSON after {MAX_ATTEMPTS} attempts: "
            f"{last_error}\n{text[:300]}"
        )

    if config.DEBUG:
        print("Keys found:", list(data.keys()))
        print("Full JSON:", json.dumps(data, indent=2, ensure_ascii=False)[:1000])

    # ── Validate required blocks ──────────────────────────────────────
    required = ["caso", "sospettati", "indizi", "testimonianze", "soluzione", "narrativa"]
    missing  = [b for b in required if b not in data]
    if missing:
        raise RuntimeError(f"Incomplete JSON — missing blocks: {missing}")

    # ── Save files ────────────────────────────────────────────────────
    # Auto-numbering: find the last caso_NNN and increment
    existing = sorted(config.CASES_DIR.glob("caso_*"))
    number   = len(existing) + 1
    case_dir = config.CASES_DIR / f"caso_{number:03d}"
    case_dir.mkdir(parents=True, exist_ok=True)

    (case_dir / "caso.json").write_text(
        json.dumps(data["caso"], indent=2, ensure_ascii=False), encoding="utf-8")

    (case_dir / "sospettati.json").write_text(
        json.dumps(data["sospettati"], indent=2, ensure_ascii=False), encoding="utf-8")

    (case_dir / "indizi.json").write_text(
        json.dumps(data["indizi"], indent=2, ensure_ascii=False), encoding="utf-8")

    (case_dir / "testimonianze.json").write_text(
        json.dumps(data["testimonianze"], indent=2, ensure_ascii=False), encoding="utf-8")

    # Solution is saved separately — the detective never sees it
    (case_dir / "soluzione.json").write_text(
        json.dumps(data["soluzione"], indent=2, ensure_ascii=False), encoding="utf-8")

    (case_dir / "storia.txt").write_text(
        data["narrativa"], encoding="utf-8")

    # ── Print summary ─────────────────────────────────────────────────
    caso = data["caso"]
    print(f"\nCase generated: {caso['titolo']}")
    print(f"Victim: {caso['vittima']}")
    print(f"Setting: {caso['ambientazione']}")
    print(f"\nSuspects:")
    for s in data["sospettati"]:
        label = " (LYING)" if s.get("mente") else ""
        print(f"  - {s['nome']}, {s['eta']} — {s['ruolo']}{label}")
    print(f"\nCase dir: {case_dir}")

    return case_dir


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--brief", type=str, default=None,
                        help="JSON brief (for use by web server)")
    args = parser.parse_args()
    brief = json.loads(args.brief) if args.brief else None
    run_writer(brief=brief)
