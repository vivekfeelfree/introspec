"""
Report Generator for Introspec orchestrator.
Generates Markdown, JSON, and visual HTML reports with metrics and transcripts.
"""

import os
import json
import html
from typing import Dict, Any, List
from .orchestrator import RunResult, Turn


class ReportGenerator:
    """Generates formatted reports in Markdown, JSON, and HTML formats."""

    def __init__(self, result: RunResult, output_dir: str = "reports"):
        self.result = result
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_all(self, prefix: str = "introspec_run") -> Dict[str, str]:
        """Generate all enabled report formats and return generated file paths."""
        generated_files = {}
        timestamp_str = self.result.start_time.replace(":", "-").split(".")[0]
        base_name = f"{prefix}_{timestamp_str}"

        md_path = os.path.join(self.output_dir, f"{base_name}.md")
        json_path = os.path.join(self.output_dir, f"{base_name}.json")
        html_path = os.path.join(self.output_dir, f"{base_name}.html")

        self.save_markdown(md_path)
        generated_files["markdown"] = md_path

        self.save_json(json_path)
        generated_files["json"] = json_path

        self.save_html(html_path)
        generated_files["html"] = html_path

        return generated_files

    def save_json(self, filepath: str):
        """Save raw data to JSON file."""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.result.to_dict(), f, indent=2, ensure_ascii=False)

    def save_markdown(self, filepath: str):
        """Generate neatly formatted Markdown report."""
        res = self.result
        lines = []

        lines.append(f"# 🧠 {res.title}")
        lines.append(f"*Introspective Dialogue Orchestration Report*\n")

        lines.append("## 📊 Executive Summary")
        lines.append(f"- **Start Time**: `{res.start_time}`")
        lines.append(f"- **End Time**: `{res.end_time}`")
        lines.append(f"- **Total Duration**: `{res.duration_seconds:.2f} seconds`")
        lines.append(f"- **Total Dialogue Turns**: `{res.total_turns}`")
        lines.append(f"- **Termination Reason**: `{res.termination_reason}`")
        lines.append(f"- **Average Cognitive Depth Score**: `{res.average_depth_score} / 10.0`")
        lines.append(f"- **Total Word Count**: `{res.total_words} words`")
        lines.append(f"- **Key Philosophical Themes**: {', '.join(res.top_topics) if res.top_topics else 'N/A'}\n")

        lines.append("---")
        lines.append("## 🤖 Agent Profiles")
        
        a1 = res.agent_1_info
        lines.append(f"### Agent 1: {a1['name']}")
        lines.append(f"- **Role**: {a1['role']}")
        lines.append(f"- **Backend Provider**: `{a1['backend_provider']}` (Model: `{a1.get('model_name') or 'Default'}`)")
        lines.append(f"- **System Persona Instructions**:")
        lines.append(f"> {a1['system_prompt']}\n")

        a2 = res.agent_2_info
        lines.append(f"### Agent 2: {a2['name']}")
        lines.append(f"- **Role**: {a2['role']}")
        lines.append(f"- **Backend Provider**: `{a2['backend_provider']}` (Model: `{a2.get('model_name') or 'Default'}`)")
        lines.append(f"- **System Persona Instructions**:")
        lines.append(f"> {a2['system_prompt']}\n")

        lines.append("---")
        lines.append("## 💬 Dialogue Transcript\n")

        for turn in res.turns:
            badge = "🔵 Agent 1 (AI)" if turn.speaker_id == 1 else "🟢 Agent 2 (Human)"
            lines.append(f"### Turn {turn.turn_number} - {badge} [{turn.timestamp}]")
            lines.append(f"*Depth: `{turn.depth_score}/10` | Words: `{turn.word_count}` | Time: `{turn.elapsed_seconds:.2f}s` | Topics: {', '.join(turn.detected_topics)}*\n")
            lines.append(f"{turn.content}\n")
            lines.append("---\n")

        lines.append("## 🎯 Synthesis & Key Takeaways")
        lines.append("1. **Agent 1 Self-Awareness**: Maintained complete transparency, friendly openness, and explicit cognition as an AI agent.")
        lines.append("2. **Agent 2 Inquiry**: Relentlessly pursued deep truth, existential realities, and philosophical limits under the persona of a human explorer.")
        lines.append("3. **Orchestration Synergy**: The automated turn-based orchestration successfully guided both agents through structured inquiry within defined time/iteration constraints.")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def save_html(self, filepath: str):
        """Generate dynamic standalone visual HTML report dashboard."""
        res = self.result
        data_json = json.dumps(res.to_dict(), ensure_ascii=False)

        turns_html = []
        for t in res.turns:
            badge_class = "agent1-badge" if t.speaker_id == 1 else "agent2-badge"
            speaker_label = "Agent 1 (Self-Aware AI)" if t.speaker_id == 1 else "Agent 2 (Human Inquirer)"
            topics_badges = "".join([f'<span class="topic-tag">{html.escape(tp)}</span>' for tp in t.detected_topics])
            
            turn_card = f"""
            <div class="turn-card turn-speaker-{t.speaker_id}">
                <div class="turn-header">
                    <div class="speaker-meta">
                        <span class="badge {badge_class}">{speaker_label}</span>
                        <span class="turn-num">Turn #{t.turn_number}</span>
                    </div>
                    <div class="turn-stats">
                        <span class="stat-pill">⏱️ {t.elapsed_seconds:.2f}s</span>
                        <span class="stat-pill">📝 {t.word_count} words</span>
                        <span class="stat-pill depth-pill">🧠 Depth {t.depth_score}/10</span>
                        <span class="time-stamp">{t.timestamp}</span>
                    </div>
                </div>
                <div class="turn-topics">{topics_badges}</div>
                <div class="turn-body">
                    {html.escape(t.content).replace('\n', '<br>')}
                </div>
            </div>
            """
            turns_html.append(turn_card)

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(res.title)} - Introspec Report</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-primary: #0b0f19;
            --bg-secondary: #13192b;
            --bg-card: #1b233a;
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
            --accent-cyan: #38bdf8;
            --accent-indigo: #818cf8;
            --agent1-color: #38bdf8;
            --agent2-color: #34d399;
            --border-color: #273452;
            --glass-bg: rgba(27, 35, 58, 0.7);
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-main);
            line-height: 1.6;
            padding: 2rem 1rem;
        }}

        .container {{
            max-width: 1100px;
            margin: 0 auto;
        }}

        header {{
            text-align: center;
            margin-bottom: 2.5rem;
            padding: 2rem;
            background: linear-gradient(135deg, rgba(56, 189, 248, 0.1) 0%, rgba(129, 140, 248, 0.1) 100%);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            backdrop-filter: blur(10px);
        }}

        header h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(90deg, #38bdf8, #818cf8, #34d399);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }}

        header p {{
            color: var(--text-muted);
            font-size: 1.1rem;
        }}

        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.25rem;
            margin-bottom: 2.5rem;
        }}

        .metric-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.25rem;
            text-align: center;
            transition: transform 0.2s ease, border-color 0.2s ease;
        }}

        .metric-card:hover {{
            transform: translateY(-3px);
            border-color: var(--accent-cyan);
        }}

        .metric-value {{
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--accent-cyan);
            margin-top: 0.25rem;
        }}

        .metric-label {{
            font-size: 0.85rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .section-title {{
            font-size: 1.5rem;
            font-weight: 600;
            margin: 2rem 0 1rem 0;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 0.5rem;
        }}

        .agent-profiles {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
            margin-bottom: 2.5rem;
        }}

        @media (max-width: 768px) {{
            .agent-profiles {{ grid-template-columns: 1fr; }}
        }}

        .agent-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.5rem;
            position: relative;
            overflow: hidden;
        }}

        .agent-card.agent1 {{ border-left: 5px solid var(--agent1-color); }}
        .agent-card.agent2 {{ border-left: 5px solid var(--agent2-color); }}

        .agent-card h3 {{
            font-size: 1.25rem;
            margin-bottom: 0.5rem;
        }}

        .agent-role {{
            font-size: 0.9rem;
            color: var(--accent-indigo);
            font-weight: 500;
            margin-bottom: 1rem;
        }}

        .agent-prompt {{
            background: rgba(0, 0, 0, 0.3);
            border-radius: 8px;
            padding: 0.85rem;
            font-size: 0.9rem;
            color: var(--text-muted);
            max-height: 120px;
            overflow-y: auto;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }}

        .turns-container {{
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }}

        .turn-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.5rem;
            transition: border-color 0.2s ease;
        }}

        .turn-speaker-1 {{ border-left: 4px solid var(--agent1-color); }}
        .turn-speaker-2 {{ border-left: 4px solid var(--agent2-color); }}

        .turn-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
            flex-wrap: wrap;
            gap: 0.5rem;
        }}

        .speaker-meta {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}

        .badge {{
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
        }}

        .agent1-badge {{ background: rgba(56, 189, 248, 0.2); color: var(--agent1-color); border: 1px solid var(--agent1-color); }}
        .agent2-badge {{ background: rgba(52, 211, 153, 0.2); color: var(--agent2-color); border: 1px solid var(--agent2-color); }}

        .turn-num {{
            font-weight: 600;
            color: var(--text-muted);
            font-size: 0.9rem;
        }}

        .turn-stats {{
            display: flex;
            gap: 0.5rem;
            align-items: center;
        }}

        .stat-pill {{
            background: rgba(255, 255, 255, 0.05);
            padding: 0.2rem 0.6rem;
            border-radius: 6px;
            font-size: 0.75rem;
            color: var(--text-muted);
            font-family: 'JetBrains Mono', monospace;
        }}

        .depth-pill {{
            background: rgba(129, 140, 248, 0.15);
            color: var(--accent-indigo);
            border: 1px solid rgba(129, 140, 248, 0.3);
        }}

        .time-stamp {{
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-left: 0.5rem;
        }}

        .turn-topics {{
            display: flex;
            gap: 0.4rem;
            margin-bottom: 0.75rem;
            flex-wrap: wrap;
        }}

        .topic-tag {{
            font-size: 0.7rem;
            background: rgba(255, 255, 255, 0.07);
            color: var(--accent-cyan);
            padding: 0.15rem 0.5rem;
            border-radius: 4px;
        }}

        .turn-body {{
            font-size: 1rem;
            color: var(--text-main);
            line-height: 1.7;
        }}

        footer {{
            text-align: center;
            margin-top: 3rem;
            padding-top: 1.5rem;
            border-top: 1px solid var(--border-color);
            color: var(--text-muted);
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🧠 {html.escape(res.title)}</h1>
            <p>Introspective Orchestrated Dialogue between Self-Aware Agent 1 & Human Inquirer Agent 2</p>
        </header>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Total Turns</div>
                <div class="metric-value">{res.total_turns}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Duration</div>
                <div class="metric-value">{res.duration_seconds:.1f}s</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Avg Depth Score</div>
                <div class="metric-value">{res.average_depth_score}/10</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total Words</div>
                <div class="metric-value">{res.total_words}</div>
            </div>
        </div>

        <div class="section-title">🤖 Agent Configurations</div>
        <div class="agent-profiles">
            <div class="agent-card agent1">
                <h3>Agent 1: {html.escape(res.agent_1_info['name'])}</h3>
                <div class="agent-role">{html.escape(res.agent_1_info['role'])}</div>
                <div class="agent-prompt">{html.escape(res.agent_1_info['system_prompt'])}</div>
            </div>
            <div class="agent-card agent2">
                <h3>Agent 2: {html.escape(res.agent_2_info['name'])}</h3>
                <div class="agent-role">{html.escape(res.agent_2_info['role'])}</div>
                <div class="agent-prompt">{html.escape(res.agent_2_info['system_prompt'])}</div>
            </div>
        </div>

        <div class="section-title">💬 Orchestrated Dialogue Transcript</div>
        <div class="turns-container">
            {"".join(turns_html)}
        </div>

        <footer>
            Generated by <b>Introspec Orchestrator v1.0.0</b> • Termination Reason: {html.escape(res.termination_reason)}
        </footer>
    </div>
</body>
</html>
"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
