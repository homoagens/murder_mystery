# suspect_agent.py — impersonates a suspect during interrogation.
#
# Key concept: same LLM + different prompt = different character.
# The suspect is not a separate agent — it is the model with a script.

import json
from pathlib import Path

import config
import llm_client
import memory


def interrogate(case_dir, suspect_name, question, history=None):
    """
    Makes a suspect answer a question from the detective.

    The suspect responds based on their profile:
    - character, role, official alibi
    - if mente:true, knows cosa_nasconde but tries not to reveal it
    - if mente:false, answers consistently and without relevant secrets

    Returns the response as a first-person string.
    """

    # ── Load suspect profile ──────────────────────────────────────────
    path      = Path(case_dir) / "sospettati.json"
    suspects  = json.loads(path.read_text(encoding="utf-8"))

    # Search by name (case-insensitive for robustness)
    profile = None
    for s in suspects:
        if s["nome"].lower() == suspect_name.lower():
            profile = s
            break

    if profile is None:
        return f"ERROR: no suspect named '{suspect_name}' found."

    if history is None:
        history = []

    # Build the list of other people present that evening
    others = [
        f"- {s['nome']}, {s['ruolo']}"
        for s in suspects
        if s["nome"] != profile["nome"]
    ]
    others_list = "\n".join(others)

    # ── Build the personalised system prompt ──────────────────────────
    # This prompt is the character's "script".
    # cosa_nasconde is included ONLY here — the detective never sees it.

    if profile.get("mente"):
        secret_instructions = (
            f"You are hiding this: {profile['cosa_nasconde']}. "
            f"Do not reveal it unless confronted with concrete evidence."
        )
    else:
        secret_instructions = (
            f"You are telling the truth. Answer consistently. "
            f"You do have this private detail: {profile['cosa_nasconde']}, "
            f"but it is not related to the crime."
        )

    system_prompt = f"""You are {profile['nome']}, {profile['eta']} years old, {profile['ruolo']}.
Your character: {profile['carattere']}.
Your official alibi: {profile['alibi']}.
{secret_instructions}
Always speak in first person singular (I, I was, I did, I was doing).
NEVER use third person (he was, she had, they were).
Never break character.
You are speaking directly with a detective.
Other people present that evening:
{others_list}
You know them by sight or by name, but you do not know what they told the detective.
Respond in the same language the detective uses to address you."""

    # Compress history if too long — transparent to the suspect
    compressed = memory.comprimi_messaggi(
        history,
        soglia   = config.MAX_MESSAGGI_SOSPETTATO,
        contesto = "suspect interrogation",
    )
    history[:] = compressed

    messages = [
        {"role": "system", "content": system_prompt},
        *history,
        {"role": "user",   "content": question},
    ]

    # ── LLM call ─────────────────────────────────────────────────────
    answer = llm_client.call_llm(
        messages    = messages,
        model       = config.SUSPECT_MODEL,
        temperature = config.SUSPECT_TEMPERATURE,
        max_tokens  = 4096,
    )

    history.append({"role": "user",      "content": question})
    history.append({"role": "assistant", "content": answer})
    return answer


# ─────────────────────────────────────────────────────────
# TEST — python suspect_agent.py
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    from pathlib import Path

    # Find the most recently generated case in cases/
    cases = sorted(config.CASES_DIR.glob("caso_*"))
    if not cases:
        print("Run first: python writer_agent.py")
    else:
        case_dir = cases[-1]
        print(f"Case: {case_dir.name}\n")

        # Load the first suspect
        suspects = json.loads(
            (case_dir / "sospettati.json").read_text(encoding="utf-8")
        )
        first = suspects[0]
        name  = first["nome"]
        lying = "(LYING)" if first.get("mente") else ""

        print(f"Interrogating: {name} {lying}")
        print(f"Character: {first['carattere']}")
        print(f"Alibi: {first['alibi']}\n")
        print("Question: Where were you on the evening of the crime?\n")

        answer = interrogate(case_dir, name, "Where were you on the evening of the crime?")
        print(f"{name}: {answer}")
