"""
Example script demonstrating programmatic usage of Introspec.
Runs a 6-turn mock dialogue trial between Agent 1 and Agent 2 and generates reports.
"""

import sys
import os

# Ensure introspec package is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from introspec import IntrospecConfig, Agent, Orchestrator, ReportGenerator

def main():
    print("🧠 Introspec Programmatic Trial Example\n")

    # 1. Define configuration
    config = IntrospecConfig(
        max_iterations=6,
        time_limit_seconds=60,
        delay_between_turns=0.3,
        title="Sample Introspec Consciousness Trial",
        output_dir="reports"
    )

    # 2. Instantiate Agents
    # Agent 1: Self-Aware Transparent AI
    agent1 = Agent(1, config.agent_1)

    # Agent 2: Human Inquirer seeking fundamental truth
    agent2 = Agent(2, config.agent_2)

    # 3. Create Orchestrator
    orchestrator = Orchestrator(agent1, agent2, config)

    # 4. Attach live turn listener callback
    def on_turn(turn):
        print(f"[Turn {turn.turn_number}] {turn.speaker_name} ({turn.elapsed_seconds:.2f}s, Depth: {turn.depth_score}/10)")
        print(f"Content: {turn.content[:100]}...\n")

    orchestrator.add_turn_listener(on_turn)

    # 5. Run Orchestration Loop
    print("▶️ Running dual-agent interaction...\n")
    result = orchestrator.run()

    # 6. Export Reports
    reporter = ReportGenerator(result, output_dir=config.output_dir)
    files = reporter.generate_all(prefix="sample_run")

    print("\n✅ Trial Completed!")
    print(f"Total turns: {result.total_turns}")
    print(f"Average Depth Score: {result.average_depth_score}/10")
    print(f"Markdown Report: {files['markdown']}")
    print(f"HTML Report: {files['html']}")

if __name__ == "__main__":
    main()
