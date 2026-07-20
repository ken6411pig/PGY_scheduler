"""GitHub Pages 排班介面的本機 CP-SAT 求解器。

雙擊後會只在本機 127.0.0.1:8765 提供服務，供 GitHub Pages 網頁呼叫。
"""
from __future__ import annotations

import base64
import importlib.util
import json
import os
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path

HOST, PORT = "127.0.0.1", 8765
PAGES_ORIGIN = "https://ken6411pig.github.io"
PAGES_URL = "https://ken6411pig.github.io/PGY_scheduler/"


def load_scheduler():
    os.environ["ER_SCHEDULER_LOCAL_AGENT"] = "1"
    path = Path(__file__).with_name("排班器.py")
    spec = importlib.util.spec_from_file_location("er_scheduler", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("找不到排班器.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["er_scheduler"] = module
    spec.loader.exec_module(module)
    return module


scheduler = load_scheduler()


def allowed_origin(origin: str | None) -> bool:
    return origin in {PAGES_ORIGIN, "http://localhost", "http://127.0.0.1"}


def payload_with_tolerance(raw: bytes, tolerance: int) -> dict:
    payload = scheduler.make_payload(BytesIO(raw))
    profiles = {
        0: {"penalty": 200, "target": 0, "target_weight": 0},
        25: {"penalty": 15, "target": 1, "target_weight": 50},
        50: {"penalty": 10, "target": 2, "target_weight": 50},
        75: {"penalty": 5, "target": 4, "target_weight": 45},
        100: {"penalty": -5, "target": 6, "target_weight": 35},
    }
    profile = profiles.get(tolerance, profiles[50])
    payload["double_shift_penalty"] = profile["penalty"]
    payload["desired_double_shifts"] = profile["target"]
    payload["desired_double_shifts_weight"] = profile["target_weight"]
    return payload


class LocalSolverHandler(BaseHTTPRequestHandler):
    server_version = "ER-Scheduler-Local-Agent/1.0"

    def log_message(self, fmt: str, *args) -> None:
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    def send_cors_headers(self, origin: str | None) -> None:
        if origin and allowed_origin(origin):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Expose-Headers", "Content-Disposition, Content-Type")
            # Chrome 的 Private Network Access 預檢與實際回應皆保留此標頭。
            self.send_header("Access-Control-Allow-Private-Network", "true")

    def send_json(self, status: int, body: dict, origin: str | None = None) -> None:
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_cors_headers(origin)
        self.end_headers()
        self.wfile.write(encoded)

    def send_file(self, content: bytes, content_type: str, filename: str, origin: str | None) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_cors_headers(origin)
        self.end_headers()
        self.wfile.write(content)

    def read_request(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if not 0 < length <= 15 * 1024 * 1024:
            raise ValueError("Excel 檔案大小需介於 1 byte 至 15 MB")
        return json.loads(self.rfile.read(length).decode("utf-8"))

    @staticmethod
    def raw_workbook(request: dict) -> bytes:
        return base64.b64decode(request["workbook_base64"], validate=True)

    def do_OPTIONS(self) -> None:
        origin = self.headers.get("Origin")
        if not allowed_origin(origin):
            self.send_json(403, {"error": "不允許的網站來源"})
            return
        self.send_json(200, {"status": "allowed"}, origin)

    def do_GET(self) -> None:
        origin = self.headers.get("Origin")
        if self.path == "/health":
            self.send_json(200, {"status": "ready", "service": "急診排班器本機求解器"}, origin)
        else:
            self.send_json(404, {"error": "找不到路徑"}, origin)

    def do_POST(self) -> None:
        origin = self.headers.get("Origin")
        if not allowed_origin(origin):
            self.send_json(403, {"error": "不允許的網站來源"})
            return
        try:
            request = self.read_request()
            if self.path == "/preview":
                raw = self.raw_workbook(request)
                payload = payload_with_tolerance(raw, int(request.get("tolerance", 50)))
                self.send_json(200, {"payload": payload, "rows": scheduler.preview_rows(payload)}, origin)
            elif self.path == "/solve":
                raw = self.raw_workbook(request)
                tolerance = int(request.get("tolerance", 50))
                payload = payload_with_tolerance(raw, tolerance)
                options, note = scheduler.collect_best_schedules(payload, maximum=20)
                first = options[0]
                if first["status"] not in {"OPTIMAL", "FEASIBLE"}:
                    self.send_json(422, {"status": first["status"], "warnings": first.get("warnings", [])}, origin)
                    return
                stats, violations = scheduler.validate_result(payload, first)
                self.send_json(200, {
                    "status": first["status"], "objective": first["objective"],
                    "solve_time_seconds": sum(item["solve_time_seconds"] for item in options),
                    "options": options, "note": note, "payload": payload,
                    "stats": stats, "violations": violations,
                }, origin)
            elif self.path == "/export/excel":
                raw = self.raw_workbook(request)
                content = scheduler.export_workbook(raw, request["result"], request["payload"])
                self.send_file(content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "CP-SAT班表.xlsx", origin)
            elif self.path == "/export/word":
                content = scheduler.export_docx(request["payload"], request["result"])
                self.send_file(content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "急診值班表.docx", origin)
            else:
                self.send_json(404, {"error": "找不到路徑"}, origin)
        except Exception as exc:
            self.send_json(400, {"error": str(exc)}, origin)


def main() -> None:
    print("急診排班器本機求解器已啟動。請保持此視窗開啟。")
    print(f"僅接受 GitHub Pages 網頁：{PAGES_URL}")
    if "--no-browser" not in sys.argv:
        webbrowser.open(PAGES_URL)
    server = ThreadingHTTPServer((HOST, PORT), LocalSolverHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n本機求解器已停止。")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
