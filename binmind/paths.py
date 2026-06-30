"""Filesystem helpers that work both from source and from a PyInstaller build."""
import os
import sys

APP_DIR_NAME = "BinMind"


def resource_path(relative: str) -> str:
    """Absolute path to a bundled resource.

    When frozen by PyInstaller the data files live under ``sys._MEIPASS``;
    when running from source they live next to the project root (the parent
    of the ``binmind`` package).
    """
    base = getattr(sys, "_MEIPASS", None)
    if base is None:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


def user_data_dir() -> str:
    """Writable per-user directory for settings and chat history.

    The app may be installed read-only (or run from a temp dir when frozen),
    so anything we need to persist goes here instead of next to the binary.
    """
    if sys.platform.startswith("win"):
        root = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        root = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:
        root = os.environ.get("XDG_CONFIG_HOME") or os.path.join(
            os.path.expanduser("~"), ".config"
        )
    path = os.path.join(root, APP_DIR_NAME)
    os.makedirs(path, exist_ok=True)
    return path
