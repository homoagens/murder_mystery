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
  <img src="https://img.shields.io/badge/provider-any%20OpenAI--compatible-f97316?style=flat-square" alt="Any provider">
</p>

---

Murder Mystery is a **playground for LLMs** — a noir whodunit where AI models play every role at once: the **writer** who invents the case, the **detectives** who investigate it, and the **suspects** who lie (or tell the truth) under interrogation. Watch the models reason their way to a verdict in real time, or step in yourself and crack the case before they do.

---

## ✦ What it does

**🖋 Writer** generates a complete case from a brief — victim, suspects with secrets and alibis, clues, witness statements, and a narrative opening — in the language you pick (English, Italiano, Español, Français…). Every case is unique.

**🕵 Detectives** — four AI detectives with different reasoning styles investigate in sequence: read the evidence, interrogate suspects, cross-check testimonies, conclude. A final **jury** weighs all four verdicts and names the culprit.

**🎮 You** can play detective instead — same files, same suspects to interrogate (each a live in-character LLM), same goal: accuse the right person before you run out of ideas.

In **AI mode** you watch the detectives reason live, token by token, including the model's own thinking as it streams. In **Human mode** your score is the number of steps it took — the fewer, the sharper.

---

## ⚡ Quickstart

**`install` → `configure` → `start`.** Three scripts, run in that order — the one supported pipeline, the same on every machine. Run them from the `murder_mystery/` folder.

| Step | Windows | Linux / macOS | What it does |
|---|---|---|---|
| **1** | `install.bat` | `./install.sh` | Creates `venv/` and installs dependencies |
| **2** | `configure.bat` | `./configure.sh` | Interactive prompts → points it at your LLM and writes `.env` |
| **3** | `start.bat` | `./start.sh` | Launches the web UI and opens your browser |

The UI opens at **http://localhost:7860**. Re-run step **2** to change provider/models; just run step **3** to play again.

> **Linux / macOS, first run only:** `chmod +x install.sh configure.sh start.sh`

---

## 🔌 Providers

Murder Mystery speaks any **OpenAI-compatible** endpoint. `configure` writes `.env` for you; you can also edit it directly or use the in-app settings panel (gear icon — set models per role, paste keys, save; it rewrites `.env` and reloads in place).

**Ollama** (local, free — default)
```env
LLM_PROVIDER=openai
LLM_BASE_URL=http://localhost:11434/v1
DEFAULT_MODEL=llama3.2
```

**OpenAI / Groq / OpenRouter / DeepSeek / Mistral / vLLM / LM Studio…** — same shape, different URL and key:
```env
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-...
DEFAULT_MODEL=gpt-4o-mini
```

Set a model per role with `WRITER_MODEL`, `DETECTIVE_MODEL`, `SUSPECT_MODEL` — each falls back to `DEFAULT_MODEL` if unset.

---

## 🗂 Architecture

```
app/                         Flask web layer: SSE streaming for AI pipeline, direct tool calls for human mode
web/                         single-page UI (vanilla JS, no build)
src/                         the engine
  writer_agent.py            single LLM call → full case JSON (in your chosen language) → cases/caso_NNN/
  orchestrator_multi.py      runs 4 detective profiles → jury aggregation → verdetto.json (the recorded verdict)
  detective_agent.py         ReAct loop: THOUGHT → ACTION (skill) → OBSERVATION → verdict
  suspect_agent.py           single LLM call per question, with history + memory compression
  tools.py                   skills: list_files, read_file, cross_check, take_note, interrogate_suspect
  memory.py                  two-threshold compression (message count + character count)
  llm_client.py              OpenAI-compatible client with live token streaming
  live.py                    bridges model tokens → the web UI so you watch it think and write in real time
scripts/                     extra CLI entry points (single-detective run, terminal human mode)
```

Cases live in `cases/caso_NNN/` — and the engine enforces fair play:

| File | Visible to detective |
|---|---|
| `caso.json` · `indizi.json` · `testimonianze.json` | ✅ yes |
| `sospettati.json` | ✅ yes (secrets stripped) |
| `note_detective.json` | ✅ yes — written by the detective |
| `soluzione.json` | ❌ no — the answer key, used only to grade |
| `verdetto.json` | ❌ no — the recorded verdict that marks the case solved |

Web UI port defaults to `7860` — override with `WEB_PORT=8080` in `.env` or `--port 8080`.

<details>
<summary>Manual setup / CLI mode</summary>

```bash
cd murder_mystery
pip install -r requirements.txt
cp .env.example .env       # then edit .env with your LLM credentials
python -m app.run              # web UI → http://0.0.0.0:7860

python src/writer_agent.py         # generate a case interactively
python src/orchestrator_multi.py   # run the 4 AI detectives on the latest case
python scripts/orchestrator.py     # single-detective run
python scripts/human_detective.py  # play the case from the terminal
```

</details>

---

## 🌱 Part of Homo Agens

Murder Mystery is part of **[Homo Agens](https://github.com/homoagens)** — an open-source effort exploring autonomous agents and local inference, on a simple thesis:

> The model matters less than the architecture around it.
> Memory, tools, transparency, and execution control are what turn an LLM into something that actually gets things done.

---

## 📬 Contact

If you work on agents, local AI, open-source tooling, or developer experience — let's talk.

[Email](mailto:homoagens1@gmail.com) &nbsp;·&nbsp; [X / Twitter](https://x.com/homoagens1)

## License

[MIT](./LICENSE)
