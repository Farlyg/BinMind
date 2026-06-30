"""BinMind entry point.

Default: open a native desktop window (pywebview) backed by a local Flask
server. Use ``--web`` to open in the system browser instead. The .exe built
with PyInstaller runs this same file.
"""
import argparse
import logging
import os
import socket
import sys
import threading
import time
import webbrowser

from binmind import APP_NAME, __version__
from binmind.paths import user_data_dir
from binmind.server import create_app


def _safe_console():
    """Make console output UTF-8 and crash-proof.

    Windows consoles default to a legacy code page (e.g. cp1251) that can't
    encode '→' or Cyrillic, and a windowed PyInstaller .exe has no stdout at
    all. Both would otherwise blow up on a plain print().
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def cprint(*args):
    try:
        print(*args, flush=True)
    except Exception:
        pass


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _wait_for_port(port: int, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), 0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def _setup_logging():
    log_file = os.path.join(user_data_dir(), "binmind.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8")],
    )


def main():
    _safe_console()
    parser = argparse.ArgumentParser(prog=APP_NAME, description=f"{APP_NAME} {__version__}")
    parser.add_argument("--web", action="store_true", help="Открыть в браузере вместо окна")
    parser.add_argument("--port", type=int, default=0, help="Порт (0 = выбрать свободный)")
    parser.add_argument("--debug", action="store_true", help="Режим отладки Flask")
    args = parser.parse_args()

    _setup_logging()
    port = args.port or _free_port()
    url = f"http://127.0.0.1:{port}"
    app = create_app()

    if args.web:
        cprint(f"{APP_NAME} {__version__} -> {url}  (Ctrl+C to quit)")
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
        app.run(host="127.0.0.1", port=port, debug=args.debug, use_reloader=False)
        return

    def serve():
        app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False, threaded=True)

    threading.Thread(target=serve, daemon=True).start()
    if not _wait_for_port(port):
        logging.error("Сервер не запустился на порту %s", port)

    try:
        import webview
    except ImportError:
        cprint("pywebview not installed - opening in browser. Install: pip install pywebview")
        webbrowser.open(url)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            return

    webview.create_window(
        f"{APP_NAME} — AI Reverse Engineering",
        url,
        width=1320,
        height=860,
        min_size=(960, 640),
        background_color="#0a0b10",
    )
    webview.start()


if __name__ == "__main__":
    sys.exit(main())
