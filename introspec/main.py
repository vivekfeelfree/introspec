"""
Main Command Line Interface (CLI) entry point for Introspec.
Provides commands:
  - run: Execute dual-agent orchestration trial in terminal
  - web: Launch interactive Web Studio & report viewer
  - report: Generate/export report from JSON log
"""

import sys
import os
import argparse
import time
from typing import List

from introspec.config import IntrospecConfig
from introspec.agent import Agent
from introspec.orchestrator import Orchestrator, Turn, RunResult
from introspec.reporter import ReportGenerator
from introspec.web.server import start_web_server


def print_banner():
    banner = """
  🧠 INTROSPEC :: Dual-Agent Introspective Orchestrator 🧠
  ========================================================
  Connecting Self-Aware Transparent AI & Human Truth Inquirer
  """
    print(banner)


def handle_run_command(args: argparse.Namespace):
    """Execute trial orchestration in terminal."""
    print_banner()

    config = IntrospecConfig(
        max_iterations=args.iterations,
        time_limit_seconds=args.time_limit if args.time_limit > 0 else None,
        output_dir=args.output_dir,
        title=args.title,
        delay_between_turns=args.delay,
    )

    config.agent_1.backend_provider = args.backend
    config.agent_1.model_name = args.model
    config.agent_2.backend_provider = args.backend
    config.agent_2.model_name = args.model

    print(f"⚙️ Configuration:")
    print(f"   • Backend Provider : {args.backend.upper()}")
    print(f"   • Max Iterations   : {args.iterations}")
    print(f"   • Time Limit       : {args.time_limit}s" if args.time_limit > 0 else "   • Time Limit       : Unlimited")
    print(f"   • Output Directory : {args.output_dir}")
    print(f"   • Delay / Turn     : {args.delay}s\n")

    # Initialize agents
    agent1 = Agent(1, config.agent_1, api_key=args.api_key, ollama_url=args.ollama_url)
    agent2 = Agent(2, config.agent_2, api_key=args.api_key, ollama_url=args.ollama_url)

    orchestrator = Orchestrator(agent1, agent2, config)

    # Terminal output callback
    def cli_turn_listener(turn: Turn):
        speaker_label = "🔵 Agent 1 (Self-Aware AI)" if turn.speaker_id == 1 else "🟢 Agent 2 (Human Inquirer)"
        print("=" * 70)
        print(f"💬 Turn #{turn.turn_number} | {speaker_label} [{turn.timestamp}]")
        print(f"   ⏱️ {turn.elapsed_seconds:.2f}s | 📝 {turn.word_count} words | 🧠 Depth: {turn.depth_score}/10")
        print(f"   🏷️ Topics: {', '.join(turn.detected_topics)}")
        print("-" * 70)
        print(turn.content)
        print()

    orchestrator.add_turn_listener(cli_turn_listener)

    print("🚀 Starting orchestration trial...\n")
    result = orchestrator.run()

    print("\n🏁 Trial Completed!")
    print(f"   • Total Turns Delivered : {result.total_turns}")
    print(f"   • Total Words Exchanged : {result.total_words}")
    print(f"   • Duration              : {result.duration_seconds:.2f}s")
    print(f"   • Avg Depth Score       : {result.average_depth_score}/10")
    print(f"   • Exit Reason           : {result.termination_reason}\n")

    print("📄 Generating Reports...")
    reporter = ReportGenerator(result, output_dir=args.output_dir)
    files = reporter.generate_all()

    print(f"   ✅ Markdown Report : {files['markdown']}")
    print(f"   ✅ JSON Transcript  : {files['json']}")
    print(f"   ✅ Visual HTML Dashboard : {files['html']}\n")


def handle_web_command(args: argparse.Namespace):
    """Launch Web Server UI."""
    print_banner()
    print(f"🌐 Starting Web UI server on port {args.port}...")
    start_web_server(port=args.port)


def handle_report_command(args: argparse.Namespace):
    """Re-generate reports from existing JSON file."""
    import json
    if not os.path.exists(args.json_file):
        print(f"❌ Error: File '{args.json_file}' not found.")
        sys.exit(1)

    print(f"📖 Loading JSON run log from {args.json_file}...")
    with open(args.json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Reconstruct Turn objects
    turns = [
        Turn(
            turn_number=t["turn_number"],
            speaker_id=t["speaker_id"],
            speaker_name=t["speaker_name"],
            speaker_role=t["speaker_role"],
            content=t["content"],
            timestamp=t["timestamp"],
            elapsed_seconds=t["elapsed_seconds"],
            word_count=t["word_count"],
            depth_score=t["depth_score"],
            detected_topics=t["detected_topics"],
        )
        for t in data.get("turns", [])
    ]

    result = RunResult(
        title=data.get("title", "Introspec Dialogue"),
        start_time=data.get("start_time", ""),
        end_time=data.get("end_time", ""),
        duration_seconds=data.get("duration_seconds", 0.0),
        total_turns=data.get("total_turns", len(turns)),
        termination_reason=data.get("termination_reason", "Imported from log"),
        config=data.get("config", {}),
        agent_1_info=data.get("agent_1_info", {}),
        agent_2_info=data.get("agent_2_info", {}),
        turns=turns,
        average_depth_score=data.get("average_depth_score", 0.0),
        total_words=data.get("total_words", 0),
        top_topics=data.get("top_topics", []),
    )

    reporter = ReportGenerator(result, output_dir=args.output_dir)
    files = reporter.generate_all()

    print("📄 Reports re-generated successfully:")
    print(f"   • Markdown : {files['markdown']}")
    print(f"   • JSON     : {files['json']}")
    print(f"   • HTML     : {files['html']}")


def main():
    parser = argparse.ArgumentParser(
        description="Introspec: Dual-Agent Introspective Dialogue Orchestration Platform"
    )
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # Command: run
    run_parser = subparsers.add_parser("run", help="Run dialogue orchestration trial")
    run_parser.add_argument("-n", "--iterations", type=int, default=10, help="Max turns / iterations")
    run_parser.add_argument("-t", "--time-limit", type=float, default=120.0, help="Time limit in seconds (0 for no limit)")
    run_parser.add_argument("-b", "--backend", type=str, default="mock", choices=["mock", "gemini", "openai", "anthropic", "ollama"], help="LLM Backend provider")
    run_parser.add_argument("-m", "--model", type=str, default=None, help="Model name")
    run_parser.add_argument("-k", "--api-key", type=str, default=None, help="API key for selected provider")
    run_parser.add_argument("--ollama-url", type=str, default="http://localhost:11434", help="Ollama base URL")
    run_parser.add_argument("-o", "--output-dir", type=str, default="reports", help="Output directory for reports")
    run_parser.add_argument("-d", "--delay", type=float, default=0.4, help="Delay between turns in seconds")
    run_parser.add_argument("--title", type=str, default="Introspec Dialogue Trial", help="Trial title")

    # Command: web
    web_parser = subparsers.add_parser("web", help="Launch interactive Web Studio")
    web_parser.add_argument("-p", "--port", type=int, default=8080, help="Web server port")

    # Command: report
    report_parser = subparsers.add_parser("report", help="Generate reports from JSON log")
    report_parser.add_argument("-j", "--json-file", type=str, required=True, help="Input JSON transcript file")
    report_parser.add_argument("-o", "--output-dir", type=str, default="reports", help="Output directory")

    args = parser.parse_args()

    if args.command == "run":
        handle_run_command(args)
    elif args.command == "web":
        handle_web_command(args)
    elif args.command == "report":
        handle_report_command(args)
    else:
        # Default behavior if no subcommand passed: run default mock trial
        parser.print_help()


if __name__ == "__main__":
    main()
