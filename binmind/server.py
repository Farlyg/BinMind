"""Flask backend for BinMind.

Routes split into three groups:
  * page         -> the single-page UI
  * ghidra proxy -> /upload, /jobs, /status, talking to the headless Ghidra REST
  * app API      -> /chat (SSE), /api/settings, /api/health
"""
import base64
import json

import requests
from flask import Flask, Response, jsonify, render_template, request

from .assistant import GhidraAssistant
from .config import DEFAULTS, load_settings, save_settings
from .paths import resource_path


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=resource_path("binmind/templates"),
        static_folder=resource_path("binmind/static"),
    )
    assistant = GhidraAssistant()

    def ghidra_base() -> str:
        return load_settings()["ghidra_base_url"].rstrip("/")

    @app.route("/")
    def index():
        return render_template("index.html")

    # ----- Ghidra proxy --------------------------------------------------------
    @app.route("/upload", methods=["POST"])
    def upload_file():
        if "file" not in request.files:
            return jsonify({"error": "No file part"}), 400
        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400
        try:
            encoded = base64.b64encode(file.read()).decode("utf-8")
            payload = {"file_b64": encoded, "filename": file.filename, "persist": True}
            response = requests.post(f"{ghidra_base()}/analyze_b64", json=payload, timeout=120)
            response.raise_for_status()
            return jsonify(response.json())
        except requests.exceptions.RequestException as e:
            return jsonify({"error": f"Не удалось связаться с Ghidra: {e}"}), 502
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/jobs", methods=["GET"])
    def list_jobs():
        try:
            response = requests.get(f"{ghidra_base()}/jobs", timeout=15)
            response.raise_for_status()
            return jsonify(response.json())
        except requests.exceptions.RequestException as e:
            return jsonify({"error": f"Не удалось получить список задач: {e}"}), 502

    @app.route("/status/<job_id>", methods=["GET"])
    def get_status(job_id):
        try:
            response = requests.get(f"{ghidra_base()}/status/{job_id}", timeout=15)
            response.raise_for_status()
            return jsonify(response.json())
        except requests.exceptions.RequestException as e:
            return jsonify({"error": f"Не удалось получить статус: {e}"}), 502

    # ----- app API -------------------------------------------------------------
    @app.route("/chat", methods=["POST"])
    def chat():
        data = request.get_json(silent=True) or {}
        user_message = data.get("message")
        job_id = data.get("job_id")
        if not user_message or not job_id:
            return jsonify({"error": "Нужны message и job_id"}), 400

        def generate():
            try:
                for chunk in assistant.chat_completion_stream(user_message, job_id):
                    yield f"data: {chunk}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

        return Response(generate(), mimetype="text/event-stream")

    @app.route("/chat/history/<job_id>", methods=["GET"])
    def get_chat_history(job_id):
        try:
            return jsonify(assistant.load_history(job_id))
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/settings", methods=["GET"])
    def get_settings():
        return jsonify(load_settings())

    @app.route("/api/settings", methods=["POST"])
    def update_settings():
        data = request.get_json(silent=True) or {}
        return jsonify(save_settings(data))

    @app.route("/api/health", methods=["GET"])
    def health():
        settings = load_settings()
        result = {
            "ghidra": False,
            "llm": False,
            "ghidra_base_url": settings["ghidra_base_url"],
            "llm_base_url": settings["llm_base_url"],
            "llm_model": settings["llm_model"],
        }
        try:
            r = requests.get(f"{settings['ghidra_base_url'].rstrip('/')}/jobs", timeout=3)
            result["ghidra"] = r.ok
        except Exception:
            pass
        try:
            base = settings["llm_base_url"].rstrip("/")
            headers = {"Authorization": f"Bearer {settings.get('llm_api_key') or 'x'}"}
            r = requests.get(f"{base}/models", headers=headers, timeout=4)
            result["llm"] = r.ok
        except Exception:
            pass
        return jsonify(result)

    @app.route("/api/defaults", methods=["GET"])
    def defaults():
        return jsonify(DEFAULTS)

    return app
