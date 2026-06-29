<h2 align="center">🔪 Murder Mystery</h2>

<p align="center">
  <em>A murder. A locked room of suspects. The truth, hidden in the files.</em>
</p>

<p align="center">
  AI writes the case  ·  AI detectives solve it  ·  AI suspects lie to your face  ·  Or play detective yourself
</p>

<p align="center">
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-c0392b?style=flat-square" alt="License"></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-3776ab?style=flat-square" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/frontend-vanilla%20JS%2C%20no%20build-43a047?style=flat-square" alt="No build step">
  <img src="https://img.shields.io/badge/provider-any%20OpenAI--compatible-f97316?style=flat-square" alt="Any provider">
</p>

---

Murder Mystery is a **playground for LLMs** — a complete Italian noir where AI models play every role at once: the **writer** who invents the case, the **detectives** who investigate it, and the **suspects** who lie (or tell the truth) under interrogation.

Watch the models reason their way to a verdict in real time — or step in yourself and try to crack the case before they do.

> It's a game, a benchmark, and a teaching tool in one. Pit models against each other on the same mystery and see which one actually reasons.

---

## ✦ What it does

**🖋 Writer agent** generates a complete case from a brief: victim, setting, suspects with secrets and alibis, physical clues, witness statements, and a narrative opening in the style of a classic *giallo* — in the language you pick (English, Italiano, Español, Français…). Every case is unique.

**🕵 Multi-detective pipeline** runs four AI detectives with different reasoning styles in sequence. Each reads the evidence, interrogates suspects, cross-checks testimonies, and reaches a verdict. A final **jury** weighs all four conclusions and names the guilty party.

**🎮 Human game mode** lets you play detective yourself — the same files the AI sees, the same suspects to interrogate (each one a live LLM call staying in character), the same goal: accuse the right person before you run out of ideas.

---

## 🎲 Modes

### 🤖 AI mode — watch the models work
Generate a case, hit **Run**, and watch four detectives reason through the evidence live — token by token, including the model's own thinking as it streams. The log shows every thought, every skill call, every deduction. At the end, a verdict card shows the jury's culprit and reasoning.

### 🔎 Human mode — play the detective
Hit **Gioca** on any case and you get:

- The narrative opening (read it carefully — details matter)
- A list of suspects you can interrogate at any time
- A file browser: clues, testimonies, the full suspect dossier
- A notepad for your deductions
- A cross-check tool to compare two documents side by side
- An accusation screen when you're ready to name the killer

Your score is the number of steps it took. The fewer, the sharper the detective.

---

## ⚡ Quickstart

**`install` → `configure` → `start`.** Three scripts, run in that order — this is the one and only supported pipeline, the same on every machine. Run them from the `murder_mystery/` folder.

| Step | Windows | Linux / macOS | What it does |
|---|---|---|---|
| **1** | `install.bat` | `./install.sh` | Creates `venv/` and installs dependencies |
| **2** | `configure.bat` | `./configure.sh` | Interactive prompts → points it at your LLM and writes `.env` |
| **3** | `start.bat` | `./start.sh` | Launches the web UI and opens your browser |

The UI opens at **http://localhost:7860**. Re-run step **2** any time to change provider/models; just run step **3** to play again.

> **Linux / macOS, first run only** — make the scripts executable:
> ```bash
> chmod +x install.sh configure.sh start.sh
> ```

<details>
<summary>Manual setup / CLI mode (advanced — prefer the three scripts above)</summary>

```bash
cd murder_mystery
pip install -r requirements.txt
cp .env.example .env       # then edit .env with your LLM credentials
python -m app.run          # → http://0.0.0.0:7860
```

CLI mode:

```bash
python writer_agent.py           # generate a case interactively
python orchestrator_multi.py     # run the AI detectives on the latest case
```

</details>

---

## 🔌 Provider configuration

Murder Mystery speaks any **OpenAI-compatible** endpoint, plus native Anthropic. Edit `.env` or use the in-app settings panel (the gear icon in the header — switch provider, set models per role, paste keys, save; it rewrites `.env` and reloads in place).

**Ollama (local, free — default)**
```env
LLM_PROVIDER=openai
LLM_BASE_URL=http://localhost:11434/v1
DEFAULT_MODEL=llama3.2
```

**OpenAI**
```env
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-...
WRITER_MODEL=gpt-4o
DETECTIVE_MODEL=gpt-4o-mini
SUSPECT_MODEL=gpt-4o-mini
```

**Anthropic**
```env
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-...
WRITER_MODEL=claude-opus-4-5
DETECTIVE_MODEL=claude-haiku-4-5
SUSPECT_MODEL=claude-haiku-4-5
```

**Groq, OpenRouter, DeepSeek, Mistral, vLLM…** — any OpenAI-compatible endpoint:
```env
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_API_KEY=gsk_...
DETECTIVE_MODEL=llama-3.3-70b-versatile
```

Use a different model per role: `WRITER_MODEL` for creative writing (high temp), `DETECTIVE_MODEL` for logical reasoning (low temp), `SUSPECT_MODEL` for character roleplay (mid temp). Each falls back to `DEFAULT_MODEL` if unset. Mix providers freely.

---

## 🗂 Architecture

```
writer_agent.py          single LLM call → full case JSON (in your chosen language) → saves to cases/caso_NNN/
orchestrator_multi.py    runs 4 detective profiles → jury aggregation → verdetto.json (the recorded verdict)
detective_agent.py       ReAct loop: THOUGHT → ACTION (skill) → OBSERVATION → verdict
suspect_agent.py         single LLM call per question, with history + memory compression
tools.py                 skills: list_files, read_file, cross_check, take_note, interrogate_suspect
memory.py                two-threshold compression (message count + character count)
llm_client.py            provider-agnostic client (OpenAI / Anthropic / custom), with live token streaming
live.py                  bridges model tokens → the web UI so you watch it think and write in real time
app/__init__.py          Flask: SSE streaming for AI pipeline, direct tool calls for human mode
```

Cases live in `cases/caso_NNN/` — and the engine enforces fair play:

| File | Visible to detective |
|---|---|
| `caso.json` | ✅ yes |
| `sospettati.json` | ✅ yes (secrets stripped) |
| `indizi.json` | ✅ yes |
| `testimonianze.json` | ✅ yes |
| `storia.txt` | ✅ yes |
| `soluzione.json` | ❌ no — the answer key (written at generation, used only to grade) |
| `verdetto.json` | ❌ no — the recorded verdict (marks the case solved in the UI) |
| `note_detective.json` | ✅ yes — written by the detective |

Web UI port defaults to `7860` — override with `WEB_PORT=8080` in `.env` or `--port 8080`.

---

## 🌱 Part of Homo Agens

Murder Mystery is part of **[Homo Agens](https://github.com/homoagens)** — an open-source effort exploring autonomous agents, local inference, and a simple thesis:

> The model matters less than the architecture around it.
> Memory, tools, transparency, and execution control are what turn an LLM into something that actually gets things done.

---

## 📬 Contact

If you work on agents, local AI, open-source tooling, or developer experience — let's talk.

[Email](mailto:homoagens1@gmail.com) &nbsp;·&nbsp; [X / Twitter](https://x.com/homoagens1)

---

## License

[MIT](./LICENSE)
