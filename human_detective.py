# human_detective.py — interactive mode: the human is the detective.
# Uses the same tools that the detective agent will use.
# Educational goal: understand the problem before automating it.

import json
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

import config
import tools
import writer_agent

console = Console()


def pick_case():
    """Asks the user whether to generate a new case or load an existing one."""
    console.print(Panel("MURDER MYSTERY — Human Detective Mode", style="bold red"))
    console.print("\n[1] Generate new case")
    console.print("[2] Load existing case\n")
    choice = Prompt.ask("Choice", choices=["1", "2"])

    if choice == "1":
        return writer_agent.run_writer()
    else:
        cases = sorted(config.CASES_DIR.glob("caso_*"))
        if not cases:
            console.print("[red]No cases available. Generate a case first.[/red]")
            return None
        console.print("\nAvailable cases:")
        for i, c in enumerate(cases):
            console.print(f"  [{i+1}] {c.name}")
        n = Prompt.ask("Case number", choices=[str(i+1) for i in range(len(cases))])
        return cases[int(n)-1]


def show_story(case_dir):
    """Displays the introductory narrative of the case."""
    story = (Path(case_dir) / "storia.txt").read_text(encoding="utf-8")
    console.print(Panel(story, title="THE CASE", style="bold yellow"))


def action_menu():
    """Displays the available actions menu."""
    console.print("\n[bold]What do you want to do?[/bold]")
    console.print("  [cyan]1[/cyan] — List available files")
    console.print("  [cyan]2[/cyan] — Read a file")
    console.print("  [cyan]3[/cyan] — Compare two files")
    console.print("  [cyan]4[/cyan] — Take a note")
    console.print("  [cyan]5[/cyan] — Interrogate a suspect")
    console.print("  [cyan]6[/cyan] — Accuse the culprit")
    console.print("  [cyan]0[/cyan] — Abandon the investigation\n")
    return Prompt.ask("Action", choices=["0","1","2","3","4","5","6"])


def detective_loop(case_dir, histories):
    """Main loop of the interactive investigation."""
    step = 0

    while True:
        step += 1
        console.print(f"\n[dim]— Step {step} —[/dim]")
        action = action_menu()

        if action == "0":
            console.print("[yellow]Investigation abandoned.[/yellow]")
            break

        elif action == "1":
            result = tools.list_files(case_dir)
            console.print(Panel(result, title="Available files", style="cyan"))

        elif action == "2":
            filename = Prompt.ask("File name")
            result   = tools.read_file(case_dir, filename)
            console.print(Panel(result, title=filename, style="cyan"))

        elif action == "3":
            file_a = Prompt.ask("First file")
            file_b = Prompt.ask("Second file")
            result = tools.cross_check(case_dir, file_a, file_b)
            console.print(Panel(result, title=f"{file_a} vs {file_b}", style="cyan"))

        elif action == "4":
            key    = Prompt.ask("Note key")
            value  = Prompt.ask("Value")
            result = tools.take_note(case_dir, key, value)
            console.print(f"[green]{result}[/green]")

        elif action == "5":
            name     = Prompt.ask("Suspect name")
            question = Prompt.ask("Question")
            # Find the suspect's history (case-insensitive)
            key = next((k for k in histories if k.lower() == name.lower()), None)
            if key is None:
                console.print(f"[red]Suspect '{name}' not found.[/red]")
                continue
            result = tools.interrogate_suspect(case_dir, key, question, histories[key])
            # Strip the prefix for human display
            text = result.replace(f"RESPONSE FROM {key}: ", "")
            console.print(Panel(text, title=f"{key}", style="yellow"))

        elif action == "6":
            accused    = Prompt.ask("Who do you accuse?")
            motivation = Prompt.ask("Why?")
            show_verdict(case_dir, accused, motivation, step)
            break


def show_verdict(case_dir, accused, motivation, step):
    """Compares the accusation with the real solution."""
    solution    = json.loads(
        (Path(case_dir) / "soluzione.json").read_text(encoding="utf-8")
    )
    real_culprit = solution["colpevole"]
    correct      = accused.lower() == real_culprit.lower()

    console.print(Panel(
        f"You accused: [bold]{accused}[/bold]\n"
        f"Motivation: {motivation}\n\n"
        f"Real culprit: [bold]{real_culprit}[/bold]\n"
        f"Explanation: {solution['spiegazione']}\n\n"
        f"Outcome: {'[green]CASE SOLVED[/green]' if correct else '[red]CASE UNSOLVED[/red]'}\n"
        f"Steps taken: {step}",
        title="FINAL VERDICT",
        style="bold green" if correct else "bold red"
    ))

    # Show the detective's notes
    notes_path = Path(case_dir) / "note_detective.json"
    if notes_path.exists():
        notes = notes_path.read_text(encoding="utf-8")
        console.print(Panel(notes, title="Your notes", style="dim"))


if __name__ == "__main__":
    case_dir = pick_case()
    if case_dir is None:
        exit()

    show_story(case_dir)
    histories = tools.init_session(case_dir)

    console.print("\n[bold]Suspects:[/bold]")
    import json
    suspects = json.loads((Path(case_dir) / "sospettati.json").read_text(encoding="utf-8"))
    for s in suspects:
        console.print(f"  - {s['nome']}, {s['eta']} — {s['ruolo']}")

    console.print("\n[dim]Use the tools to investigate. Good luck.[/dim]")
    detective_loop(case_dir, histories)
