"""
Lightweight Web Server for Introspec UI and Orchestration Control API.
Uses standard Python library http.server (no external dependencies required).
"""

import http.server
import socketserver
import json
import os
import threading
import time
import urllib.parse
from typing import Dict, Any, Optional

from introspec.config import IntrospecConfig, AgentConfig
from introspec.agent import Agent
from introspec.orchestrator import Orchestrator, RunResult, Turn
from introspec.reporter import ReportGenerator

# Global state for web orchestration engine
current_run_state: Dict[str, Any] = {
    "status": "idle",  # idle, running, completed, error
    "progress_turn": 0,
    "max_iterations": 10,
    "time_limit": 120,
    "latest_turn": None,
    "turns": [],
    "result": None,
    "generated_files": {},
    "error_message": None,
}

orchestrator_instance: Optional[Orchestrator] = None


class IntrospecHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP Request Handler for Introspec Web UI and REST API."""

    def __init__(self, *args, **kwargs):
        static_dir = os.path.join(os.path.dirname(__file__), "static")
        super().__init__(*args, directory=static_dir, **kwargs)

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path == "/api/status":
            self.send_json_response(current_run_state)
        elif path == "/api/reports":
            self.send_json_response({
                "generated_files": current_run_state.get("generated_files", {}),
                "has_result": current_run_state.get("result") is not None
            })
        elif path == "/api/logs":
            from introspec.logger import IntrospecLogger
            logs = IntrospecLogger.get_recent_logs(max_lines=100)
            self.send_json_response({"logs": logs})
        elif path.startswith("/reports/"):
            # Serve generated report files directly from output directory
            file_name = os.path.basename(path)
            output_dir = os.path.abspath(current_run_state.get("output_dir", "reports"))
            file_path = os.path.join(output_dir, file_name)
            if os.path.exists(file_path):
                self.send_response(200)
                if file_path.endswith(".html"):
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                elif file_path.endswith(".json"):
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                else:
                    self.send_header("Content-Type", "text/markdown; charset=utf-8")
                
                with open(file_path, "rb") as f:
                    content = f.read()
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return
            else:
                self.send_json_response({"error": f"Report file '{file_name}' not found"}, status=404)
                return
        else:
            # Serve static assets or default to index.html
            super().do_GET()

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            params = json.loads(body)
        except Exception:
            params = {}

        if path == "/api/start":
            if current_run_state["status"] == "running":
                self.send_json_response({"error": "Orchestration already in progress"}, status=400)
                return

            # Start run in background thread
            thread = threading.Thread(target=run_orchestration_background, args=(params,), daemon=True)
            thread.start()
            self.send_json_response({"message": "Orchestration started successfully", "status": "running"})

        elif path == "/api/stop":
            global orchestrator_instance
            if orchestrator_instance:
                orchestrator_instance.request_stop()
                self.send_json_response({"message": "Stop requested successfully"})
            else:
                self.send_json_response({"message": "No active orchestrator to stop"})

        else:
            self.send_json_response({"error": "Not Found"}, status=404)

    def send_json_response(self, data: Dict[str, Any], status: int = 200):
        body_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body_bytes)


def run_orchestration_background(params: Dict[str, Any]):
    """Background task executing the dual-agent trial."""
    global current_run_state, orchestrator_instance

    current_run_state["status"] = "running"
    current_run_state["turns"] = []
    current_run_state["progress_turn"] = 0
    current_run_state["result"] = None
    current_run_state["generated_files"] = {}
    current_run_state["error_message"] = None

    try:
        max_iters = int(params.get("max_iterations", 10))
        time_lim = float(params.get("time_limit", 120.0))
        backend_p = params.get("backend_provider", "antigravity")
        model_n = params.get("model_name", "")
        gemini_key = params.get("gemini_api_key")
        openai_key = params.get("openai_api_key")
        anthropic_key = params.get("anthropic_api_key")
        ollama_url = params.get("ollama_base_url", "http://localhost:11434")

        cfg = IntrospecConfig(
            max_iterations=max_iters,
            time_limit_seconds=time_lim,
            title=params.get("title", "Introspec Web Orchestration Trial"),
            output_dir=params.get("output_dir", "reports"),
        )

        cfg.agent_1.backend_provider = backend_p
        cfg.agent_1.model_name = model_n or None
        cfg.agent_2.backend_provider = backend_p
        cfg.agent_2.model_name = model_n or None

        # Determine appropriate API keys per agent
        key_1 = gemini_key or openai_key or anthropic_key
        key_2 = gemini_key or openai_key or anthropic_key

        agent1 = Agent(1, cfg.agent_1, api_key=key_1, ollama_url=ollama_url)
        agent2 = Agent(2, cfg.agent_2, api_key=key_2, ollama_url=ollama_url)

        orchestrator_instance = Orchestrator(agent1, agent2, cfg)

        def turn_listener(turn: Turn):
            current_run_state["progress_turn"] = turn.turn_number
            current_run_state["latest_turn"] = turn.to_dict()
            current_run_state["turns"].append(turn.to_dict())

        orchestrator_instance.add_turn_listener(turn_listener)

        result = orchestrator_instance.run()
        reporter = ReportGenerator(result, output_dir=cfg.output_dir)
        files = reporter.generate_all()

        current_run_state["status"] = "completed"
        current_run_state["result"] = result.to_dict()
        current_run_state["generated_files"] = files

    except Exception as e:
        current_run_state["status"] = "error"
        current_run_state["error_message"] = str(e)


def start_web_server(port: int = 8080):
    """Start HTTP Web Server on specified port."""
    socketserver.TCPServer.allow_reuse_address = True
    handler = IntrospecHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"🚀 Introspec Web UI running at http://localhost:{port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down Web Server.")


if __name__ == "__main__":
    start_web_server(8080)
