# orchestrator.py — coordinates writer and detective on a single case.
# Does not reason about the content: only knows who to call and in what order.

import json
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

import config
import writer_agent
import detective_agent

console = Console()


def pick_case():
    """
    Asks the user whether to generate a new case or use an existing one.
    Returns the Path of the case folder.
    """
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


def evaluate(case_dir, conclusion):
    """
    Compares the detective's conclusion with soluzione.json.
    Returns True if correct, False otherwise.
    """
    solution_path = Path(case_dir) / "soluzione.json"
    if not solution_path.exists():
        console.print("[yellow]soluzione.json not found — cannot evaluate.[/yellow]")
        return None

    solution      = json.loads(solution_path.read_text(encoding="utf-8"))
    real_culprit  = solution["colpevole"].strip().lower()
    detective_acc = conclusion["conclusion"].strip().lower()

    correct = (real_culprit in detective_acc or detective_acc in real_culprit)

    if correct:
        console.print(Panel(
            f"CORRECT\nCulprit: {solution['colpevole']}",
            style="bold green"
        ))
    else:
        console.print(Panel(
            f"WRONG\n"
            f"Detective:     {conclusion['conclusion']}\n"
            f"Real culprit:  {solution['colpevole']}\n\n"
            f"Explanation: {solution.get('spiegazione', '')}",
            style="bold red"
        ))

    return correct


def run(case_dir=None):
    """
    Full pipeline: case selection → investigation → evaluation.
    """
    if case_dir is None:
        case_dir = pick_case()

    case_dir = Path(case_dir)
    console.print(Panel(f"Case: [bold]{case_dir.name}[/bold]", style="bold blue"))

    # Run the detective
    conclusion = detective_agent.run_detective(case_dir)

    if conclusion is None:
        console.print(Panel(
            "The detective did not reach a conclusion within the maximum number of steps.",
            style="bold red"
        ))
        return

    # Evaluate the result
    evaluate(case_dir, conclusion)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(case_dir=sys.argv[1])
    else:
        run()
