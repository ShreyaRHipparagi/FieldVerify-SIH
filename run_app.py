"""
FieldVerify AI Application Launcher
Gets local Wi-Fi IP address, finds an open port, prints clear Local and Network URLs in terminal,
and launches Streamlit server for Laptop & Mobile device access.
Works seamlessly from terminal, VS Code, or IDE runners.
"""

import socket
import sys
import os
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


def get_local_wifi_ip():
    """Gets the active local IPv4 address of the computer on the Wi-Fi network."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def find_free_port(start_port=8501, max_tries=20):
    """Checks if start_port is available; if not, finds the next available port."""
    for port in range(start_port, start_port + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue
    return start_port


def main():
    wifi_ip = get_local_wifi_ip()
    port = find_free_port(8501)

    print("\n" + "=" * 72)
    print("  [+] FIELDVERIFY AI - SERVER STARTING...")
    print("=" * 72)
    print(f"\n  [LAPTOP LOCAL ACCESS]   : http://localhost:{port}")
    print(f"  [MOBILE WI-FI ACCESS]   : http://{wifi_ip}:{port}")
    print("\n" + "=" * 72)
    print("  Note: Connect your Mobile Phone to the SAME Wi-Fi network as this laptop")
    print("  and open the Mobile Wi-Fi URL in Chrome / Safari to take live photos!\n" + "=" * 72 + "\n")

    app_path = str(PROJECT_ROOT / "app.py")
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        app_path,
        "--server.address", "0.0.0.0",
        "--server.port", str(port),
        "--server.headless", "true"
    ]

    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", "")

    try:
        subprocess.run(cmd, cwd=str(PROJECT_ROOT), env=env)
    except KeyboardInterrupt:
        print("\n[+] FieldVerify AI Server stopped gracefully.")


if __name__ == "__main__":
    main()
