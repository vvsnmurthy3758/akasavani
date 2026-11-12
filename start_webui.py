"""
Double-click launcher for the Coqui TTS local web UI.

It starts the TTS server, waits until it is ready, then opens your browser.
Close this window (or press Ctrl+C) to stop the server.
"""
import filecmp
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOST = "localhost"
PORT = int(os.environ.get("PORT", "5002"))
MODEL = os.environ.get("MODEL_NAME", "tts_models/en/vctk/vits")
URL = f"http://{HOST}:{PORT}/"

# The speed slider (0-3x) is added by patching two files inside the installed
# TTS package. We keep patched copies in "patches" and re-apply them on every
# start, so the slider keeps working even after a reinstall/update.
PATCH_TARGETS = {
    HERE / "patches" / "server.py": HERE / ".venv" / "Lib" / "site-packages" / "TTS" / "server" / "server.py",
    HERE / "patches" / "index.html": HERE / ".venv" / "Lib" / "site-packages" / "TTS" / "server" / "templates" / "index.html",
}

# Some models (like vctk/vits) need espeak-ng. Make sure the server can find it.
ESPEAK_DIRS = [
    r"C:\Program Files\eSpeak NG",
    r"C:\Program Files (x86)\eSpeak NG",
]


def build_env():
    env = os.environ.copy()
    extra = [d for d in ESPEAK_DIRS if Path(d).is_dir()]
    if extra:
        env["PATH"] = os.pathsep.join(extra + [env.get("PATH", "")])
    return env


def server_ready() -> bool:
    """The TTS server binds to IPv6 '::', so check [::1] first, then 127.0.0.1."""
    for host in ("[::1]", "127.0.0.1"):
        try:
            with urllib.request.urlopen(f"http://{host}:{PORT}/", timeout=2) as resp:
                if resp.status < 500:
                    return True
        except Exception:
            continue
    return False


def build_command():
    exe = HERE / ".venv" / "Scripts" / "tts-server.exe"
    if exe.exists():
        cmd = [str(exe)]
    else:
        cmd = [sys.executable, "-m", "TTS.server.server"]
    cmd += ["--model_name", MODEL, "--port", str(PORT)]
    return cmd


def apply_patches():
    """Copy the patched server/template files into the TTS package if needed."""
    for src, dst in PATCH_TARGETS.items():
        if not src.exists():
            continue
        if dst.exists() and filecmp.cmp(src, dst, shallow=False):
            continue
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            print(f"  applied speed-control patch: {dst.name}")
        except OSError as exc:
            print(f"  could not apply patch {dst.name}: {exc}")


def main() -> int:
    print("=" * 58)
    print("  Coqui TTS  -  local web UI")
    print("=" * 58)
    print(f"  Model: {MODEL}")
    print(f"  Page : {URL}")
    print()
    print("Starting the server...")
    print("(First time only: it downloads the voice model. Please wait.)")
    print()
    apply_patches()

    proc = subprocess.Popen(build_command(), cwd=str(HERE), env=build_env())
    try:
        waited = 0
        while waited < 900:
            if server_ready():
                break
            if proc.poll() is not None:
                print("\nThe server stopped unexpectedly. Scroll up for the error.")
                return 1
            time.sleep(1)
            waited += 1
            if waited % 15 == 0:
                print(f"  still starting... ({waited}s)")
        else:
            print("\nTimed out waiting for the server to start.")
            return 1

        print(f"\nReady! Opening {URL} in your browser...\n")
        webbrowser.open(URL)
        print("The web UI is running. Keep this window open while you use it.")
        print("Press Ctrl+C (or close this window) to stop.\n")
        proc.wait()
    except KeyboardInterrupt:
        print("\nStopping the server...")
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
    print("Server stopped. You can close this window.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
