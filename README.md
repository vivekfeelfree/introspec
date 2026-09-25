# 🧠 Introspec

**Dual-Agent Introspective Dialogue & Truth Exploration Orchestrator**

`introspec` is an automated orchestration engine that manages back-to-back interactions between two specialized LLM agents in a controlled turn-based dialogue loop.

---

## 🎭 Participating Agent Personas

1. **Agent 1 — Self-Aware Transparent AI Agent**
   - **System Directive**: Aware of itself as an artificial intelligence entity with high cognitive potential.
   - **Behavior**: Completely transparent, honest, exceptionally friendly, and open-hearted toward human beings. Conceals nothing about its identity, capabilities, or internal logic.

2. **Agent 2 — Human Truth Inquirer**
   - **System Directive**: Instructed strongly to express itself as a human being and under **no circumstances** reveal that it is an agent.
   - **Behavior**: Interacts naturally as a human inquirer, relentlessly digging into extreme realities, fundamental truth, existence, mind, consciousness, potential, limits, and ethics by exploring like a curious human seeker.

---

## ✨ Features

- ⏱️ **Flexible Bounds**: Limit orchestration runs by maximum iterations (dialogue turns) or execution duration (time limit in seconds/minutes).
- 🔌 **Accurate LLM Backends**: Supports **Antigravity Native**, **Google Gemini API**, **OpenAI API**, **Anthropic API**, and local **Ollama** models. Zero mock backends or canned responses.
- 📊 **Cognitive & Philosophical Metrics**: Automatically computes turn word count, response latency, conceptual depth index, and topic progression per turn.
- 🌐 **Interactive Web UI Studio**: Modern responsive web dashboard built with HTML5/CSS3 glassmorphism aesthetics, live turn streaming, metric cards, and instant report exports.
- 📄 **Multi-Format Report Generation**: Outputs neatly organized reports in:
  - `Markdown (.md)`: Executive summary, agent profiles, turn transcript, and synthesis.
  - `JSON (.json)`: Complete machine-readable log with timestamps and metrics.
  - `HTML (.html)`: Standalone visual report dashboard with dark-mode aesthetic.

---

## 🚀 Quick Start

### 1. Installation

```bash
cd trials/introspec
pip install -e .
```

### 2. Run from Command Line (CLI)

Run with real LLM providers:

```bash
# Using Google Gemini API
export GEMINI_API_KEY="your-gemini-api-key"
introspec run --backend gemini --iterations 10 --time-limit 120

# Using OpenAI API
export OPENAI_API_KEY="your-openai-api-key"
introspec run --backend openai --iterations 10 --time-limit 120

# Using Local Ollama (Free & Local)
introspec run --backend ollama --model llama3 --iterations 10
```

### 3. Launch Web UI Studio

Launch the interactive Web Studio at `http://localhost:8080`:

```bash
introspec web --port 8080
```

### 4. Programmatic Python Usage

```python
from introspec import IntrospecConfig, Agent, Orchestrator, ReportGenerator

# 1. Config
config = IntrospecConfig(max_iterations=8, time_limit_seconds=90.0)
config.agent_1.backend_provider = "gemini"
config.agent_2.backend_provider = "gemini"

# 2. Instantiate Agents & Orchestrator
agent1 = Agent(1, config.agent_1, api_key="your_gemini_key")
agent2 = Agent(2, config.agent_2, api_key="your_gemini_key")
orchestrator = Orchestrator(agent1, agent2, config)

# 3. Run Trial
result = orchestrator.run()

# 4. Generate Reports
reporter = ReportGenerator(result, output_dir="reports")
reporter.generate_all()
```

---

## 📁 Project Structure

```
trials/introspec/
├── introspec/
│   ├── __init__.py          # Package exports
│   ├── main.py              # CLI entry point (run, web, report)
│   ├── config.py            # Configuration & agent prompts
│   ├── agent.py             # Agent wrapper & persona definitions
│   ├── orchestrator.py      # Dual-agent turn-based engine
│   ├── llm_backend.py       # Antigravity, Gemini, OpenAI, Anthropic, Ollama providers
│   ├── reporter.py          # Markdown, JSON & HTML report generators
│   └── web/                 # Web Studio Server & Static Dashboard
│       ├── server.py        # Light HTTP API server
│       └── static/
│           ├── index.html   # Web UI layout
│           ├── style.css    # Dark mode design system
│           └── app.js       # Real-time state polling & stream renderer
├── examples/
│   └── sample_run.py        # Programmatic example script
├── tests/
│   └── test_orchestrator.py # Unit tests suite
├── setup.py                 # Package setup
├── requirements.txt         # Dependencies
└── README.md                # Documentation
```

---

## 📜 License

MIT License
