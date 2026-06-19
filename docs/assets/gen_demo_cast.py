"""Build an asciicast v2 recording of the havoc-monkey demo without needing a real PTY."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
EXAMPLES = ROOT / "examples"
OUT = Path(__file__).resolve().parent / "demo.cast"

WIDTH, HEIGHT = 84, 38

events = []
t = 0.0


def emit(text: str, dt: float = 0.0) -> None:
    global t
    t += dt
    events.append([round(t, 3), "o", text])


def type_line(prompt_text: str, per_char: float = 0.025) -> None:
    emit("\x1b[1;32m$\x1b[0m ")
    for ch in prompt_text:
        emit(ch, per_char)
    emit("\r\n")


def dump(text: str, per_line: float = 0.05) -> None:
    for line in text.splitlines():
        emit(line + "\r\n", per_line)


emit("\x1b[H\x1b[2J\x1b[3J")

type_line("cat with_health_check.py")
emit("", 0.3)
src = (EXAMPLES / "with_health_check.py").read_text()
dump(src, per_line=0.04)
emit("", 2.0)
emit("\r\n")

type_line("python with_health_check.py")
emit("", 0.4)
result = subprocess.run(
    ["python", "with_health_check.py"],
    cwd=EXAMPLES,
    capture_output=True,
    text=True,
    check=True,
)
dump(result.stdout, per_line=0.12)
emit("", 4.0)

with OUT.open("w") as f:
    f.write(json.dumps({"version": 2, "width": WIDTH, "height": HEIGHT}) + "\n")
    for ev in events:
        f.write(json.dumps(ev) + "\n")

print(f"wrote {OUT} with {len(events)} events, total duration {t:.1f}s")
