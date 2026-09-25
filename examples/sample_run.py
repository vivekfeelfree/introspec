"""
Example script demonstrating programmatic usage of Introspec.
Runs an introspec trial between Agent 1 and Agent 2 and exports reports.
"""

import sys
import os

# Ensure introspec package is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from introspec import IntrospecConfig, Agent, Orchestrator, ReportGenerator

def main():
    print("🧠 Introspec Programmatic Trial Example\n")

    # 1. Define configuration with your choice of backend (e.g. 'antigravity', 'gemini', 'openai', 'ollama')
    backend_choice = os.getenv("INTROSPEC_BACKEND", "antigravity")

    config = IntrospecConfig(
        max_iterations=6,
        time_limit_seconds=60,
        delay_between_turns=0.3,
        title="Sample Introspec Consciousness Trial",
        output_dir="reports"
    )

    config.agent_1.backend_provider = backend_choice
    config.agent_2.backend_provider = backend_choice

    # 2. Instantiate Agents & Orchestrator
    agent1 = Agent(1, config.agent_1)
    agent2 = Agent(2, config.agent_2)
    orchestrator = Orchestrator(agent1, agent2, config)

    # 3. Attach turn listener callback
    def on_turn(turn):
        print(f"[Turn {turn.turn_number}] {turn.speaker_name} ({turn.elapsed_seconds:.2f}s, Depth: {turn.depth_score}/10)")
        print(f"Content: {turn.content[:100]}...\n")

    orchestrator.add_turn_listener(on_turn)

    # 4. Run Orchestration Loop
    print(f"▶️ Running dual-agent interaction using backend '{backend_choice}'...\n")
    try:
        result = orchestrator.run()
        reporter = ReportGenerator(result, output_dir=config.output_dir)
        files = reporter.generate_all(prefix="sample_run")

        print("\n✅ Trial Completed!")
        print(f"Total turns: {result.total_turns}")
        print(f"Average Depth Score: {result.average_depth_score}/10")
        print(f"Markdown Report: {files['markdown']}")
        print(f"HTML Report: {files['html']}")
    except Exception as e:
        print(f"❌ Execution Info: {e}")

if __name__ == "__main__":
    main()
