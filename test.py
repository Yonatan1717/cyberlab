
import subprocess

proc = subprocess.Popen(
    ["cmd.exe", "/Q", "/D"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    errors="replace",
    bufsize=1
)

try:
    proc.stdin.write("echo TEST_OK\r\n")
    proc.stdin.write("echo __FERDIG__\r\n")
    proc.stdin.flush()

    for line in proc.stdout:
        print(repr(line))

        if line.strip().endswith("__FERDIG__"):
            break

finally:
    if proc.poll() is None:
        proc.kill()
    proc.wait()
