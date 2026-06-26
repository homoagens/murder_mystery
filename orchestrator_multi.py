# orchestrator_multi.py — orchestrates four detectives with different profiles + final jury.
# The orchestrator does not reason about the case: it only knows who to call and in what order.

import json
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

import config
import writer_agent
import detective_agent
import jury

console = Console()

PROFILES = [
    {
        "nome":        "methodical",
        "temperature": 0.15,
        "stile":       "Follow only physical evidence and verifiable alibis. Ignore emotions.",
    },
    {
        "nome":        "aggressive",
        "temperature": 0.85,
        "stile":       "Interrogate suspects immediately. Look for contradictions in their answers.",
    },
    {
        "nome":        "skeptical",
        "temperature": 0.35,
        "stile":       "Question everything. Use cross_check obsessively. Look for the hidden lie.",
    },
    {
        "nome":        "lateral",
        "temperature": 0.7,
        "stile":       "Explore non-obvious hypotheses and indirect connections between clues. Look for hidden patterns, but never conclude without verifying them with evidence, alibis, or cross_check.",
    },
]


def pick_case():
    cases = sorted(config.CASES_DIR.glob("caso_*"))
    console.print("\n[bold]── Case selection ──[/bold]")
    console.print("  [cyan]N[/cyan] — generate a new case")
    if cases:
        for i, c in enumerate(cases, 1):
            console.print(f"  [cyan]{i}[/cyan] — {c.name}")
    choice = input("\nChoice: ").strip().upper()
    if choice == "N":
        return writer_agent.run_writer()
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(cases):
            return cases[idx]
    console.print("[red]Invalid choice.[/red]")
    sys.exit(1)


def evaluate(case_dir, verdict):
    solution_path = Path(case_dir) / "soluzione.json"
    if not solution_path.exists():
        return
    solution     = json.loads(solution_path.read_text(encoding="utf-8"))
    real_culprit = solution["colpevole"].strip().lower()
    jury_culprit = verdict["conclusion"].strip().lower()
    correct = (real_culprit in jury_culprit or jury_culprit in real_culprit)
    if correct:
        console.print(Panel(
            f"CORRECT\nCulprit: {solution['colpevole']}",
            style="bold green"
        ))
    else:
        console.print(Panel(
            f"WRONG\n"
            f"Jury:          {verdict['conclusion']}\n"
            f"Real culprit:  {solution['colpevole']}\n\n"
            f"Explanation: {solution.get('spiegazione', '')}",
            style="bold red"
        ))


def run(case_dir=None):
    if case_dir is None:
        case_dir = pick_case()
    case_dir = Path(case_dir)

    console.print(Panel(
        f"Case: [bold]{case_dir.name}[/bold]\n4 detectives in sequence + final jury",
        style="bold blue"
    ))

    conclusions = []
    for profile in PROFILES:
        console.print(f"\n[bold magenta]━━━ Detective: {profile['nome'].upper()} ━━━[/bold magenta]")
        result = detective_agent.run_detective(case_dir, profile)
        if result:
            conclusions.append(result)

    if not conclusions:
        console.print("[red]No detective produced a verdict.[/red]")
        return

    # Verdict summary before the jury
    console.print(Panel(
        "\n".join(
            f"{c['detective'].upper()}: {c['conclusion']}"
            + (" [forced]" if c.get("forzato") else "")
            for c in conclusions
        ),
        title="VERDICT SUMMARY", style="bold magenta"
    ))

    # Jury
    console.print(f"\n[bold]━━━ Jury ━━━[/bold]")
    verdict = jury.chiedi_giuria(conclusions)
    console.print(Panel(
        f"Verdict: [bold]{verdict['conclusion']}[/bold]\n"
        f"Consensus: {verdict.get('consenso', '?')}\n\n"
        f"{verdict['reason']}",
        title="FINAL VERDICT", style="bold cyan"
    ))

    evaluate(case_dir, verdict)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(case_dir=sys.argv[1])
    else:
        run()
