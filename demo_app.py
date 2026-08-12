"""Local demo UI for the Northstar RAG evaluation lab.

Run ``python demo_app.py`` and open http://127.0.0.1:8000.
The server binds to localhost by default and never sends the API key to clients.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from domain_assistant import DomainAssistant
from template import RAGASEvaluator, rerank_by_overlap

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "demo"
GOLDEN_PATH = ROOT / "golden_dataset.json"
ACTUAL_PATH = ROOT / "artifacts" / "actual_answers.json"
BENCHMARK_PATH = ROOT / "artifacts" / "benchmark_results.json"
CORPUS_DIR = ROOT / "data" / "student_services"
MAX_QUESTION_LENGTH = 2_000

_assistant: DomainAssistant | None = None
_assistant_lock = threading.Lock()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_demo_data() -> dict[str, Any]:
    """Load and join golden cases, recorded answers, and benchmark scores."""
    golden = _read_json(GOLDEN_PATH)["qa_pairs"]
    actual_doc = _read_json(ACTUAL_PATH)
    benchmark = _read_json(BENCHMARK_PATH)
    actual_by_id = {row["id"]: row for row in actual_doc["answers"]}
    result_by_id = {row["id"]: row for row in benchmark["results"]}
    cases = []
    for pair in golden:
        actual = actual_by_id[pair["id"]]
        result = result_by_id[pair["id"]]
        cases.append(
            {
                **result,
                "expected_answer": pair["expected_answer"],
                "gold_contexts": pair["contexts"],
                "retrieved_contexts": actual["retrieved_contexts"],
            }
        )
    return {
        "summary": benchmark["summary"],
        "cases": cases,
        "agent": actual_doc["agent"],
        "generated_at": actual_doc["generated_at"],
    }


def rerank_case(case_id: str) -> dict[str, Any]:
    """Rerank one recorded trace and calculate before/after metrics."""
    golden = _read_json(GOLDEN_PATH)["qa_pairs"]
    actual = _read_json(ACTUAL_PATH)["answers"]
    pair = next((row for row in golden if row["id"] == case_id), None)
    trace = next((row for row in actual if row["id"] == case_id), None)
    if pair is None or trace is None:
        raise KeyError(f"Unknown case ID: {case_id}")

    chunks = trace["retrieved_contexts"]
    texts = [chunk["text"] for chunk in chunks]
    reranked_texts = rerank_by_overlap(texts, pair["question"])
    positions: dict[str, list[dict[str, Any]]] = {}
    for chunk in chunks:
        positions.setdefault(chunk["text"], []).append(chunk)
    reranked_chunks = [positions[text].pop(0) for text in reranked_texts]
    evaluator = RAGASEvaluator()
    expected = pair["expected_answer"]
    return {
        "id": case_id,
        "before": {
            "recall": evaluator.evaluate_context_recall(texts, expected),
            "precision": evaluator.evaluate_context_precision(texts, expected),
            "chunks": chunks,
        },
        "after": {
            "recall": evaluator.evaluate_context_recall(reranked_texts, expected),
            "precision": evaluator.evaluate_context_precision(
                reranked_texts, expected
            ),
            "chunks": reranked_chunks,
        },
    }


def _get_assistant() -> DomainAssistant:
    global _assistant
    with _assistant_lock:
        if _assistant is None:
            _assistant = DomainAssistant.from_corpus(CORPUS_DIR)
    return _assistant


def ask_live(question: str) -> dict[str, Any]:
    """Ask the live RAG assistant and return its answer and retrieval trace."""
    clean = question.strip()
    if not clean:
        raise ValueError("Question is required")
    if len(clean) > MAX_QUESTION_LENGTH:
        raise ValueError(f"Question must be at most {MAX_QUESTION_LENGTH} characters")
    response = _get_assistant().answer_with_trace(clean)
    return {
        "question": response.question,
        "answer": response.actual_answer,
        "retrieved_contexts": [
            {
                "source_doc": chunk.source_doc,
                "chunk_id": chunk.chunk_id,
                "score": chunk.score,
                "text": chunk.text,
            }
            for chunk in response.retrieved_chunks
        ],
    }


class DemoHandler(BaseHTTPRequestHandler):
    server_version = "NorthstarDemo/1.0"

    def _json_response(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _error(self, message: str, status: HTTPStatus) -> None:
        self._json_response({"error": message}, status)

    def _read_body(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("Invalid Content-Length") from exc
        if length <= 0 or length > 20_000:
            raise ValueError("Invalid request body size")
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("JSON body must be an object")
        return payload

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        path = urlparse(self.path).path
        if path == "/api/health":
            self._json_response({"status": "ok"})
            return
        if path == "/api/data":
            try:
                self._json_response(load_demo_data())
            except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                self._error(str(exc), HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        self._serve_static(path)

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        try:
            payload = self._read_body()
            path = urlparse(self.path).path
            if path == "/api/ask":
                question = payload.get("question")
                if not isinstance(question, str):
                    raise ValueError("question must be a string")
                self._json_response(ask_live(question))
                return
            if path == "/api/rerank":
                case_id = payload.get("id")
                if not isinstance(case_id, str):
                    raise ValueError("id must be a string")
                self._json_response(rerank_case(case_id))
                return
            self._error("API endpoint not found", HTTPStatus.NOT_FOUND)
        except KeyError as exc:
            self._error(str(exc), HTTPStatus.NOT_FOUND)
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            self._error(str(exc), HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # OpenAI/network errors become a safe API error.
            self._error(str(exc), HTTPStatus.INTERNAL_SERVER_ERROR)

    def _serve_static(self, request_path: str) -> None:
        relative = "index.html" if request_path == "/" else unquote(request_path.lstrip("/"))
        candidate = (STATIC_DIR / relative).resolve()
        try:
            candidate.relative_to(STATIC_DIR.resolve())
        except ValueError:
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if not candidate.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = candidate.read_bytes()
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[demo] {self.address_string()} - {format % args}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), DemoHandler)
    url = f"http://{args.host}:{server.server_port}"
    print(f"Northstar demo running at {url}")
    print("Press Ctrl+C to stop.")
    if not args.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping demo server.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
