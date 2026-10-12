"""Aura - lightweight desktop music player. Run:  python main.py   (or --browser to use your browser)"""
import argparse
import os
import subprocess
import sys
import threading
import webbrowser

from backend import server


class Api:
    """Exposed to the UI as window.pywebview.api"""

    def __init__(self):
        self.window = None

    def pick_folder(self):
        import webview
        kind = webview.FileDialog.FOLDER if hasattr(webview, "FileDialog") else webview.FOLDER_DIALOG
        res = self.window.create_file_dialog(kind)
        return res[0] if res else None

    def open_path(self, path):
        if sys.platform.startswith("win"):
            os.startfile(path)  # noqa
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--browser", action="store_true", help="open in your default browser instead of a native window")
    ap.add_argument("--port", type=int, default=0)
    args = ap.parse_args()
    _, port = server.start(args.port)
    url = f"http://127.0.0.1:{port}/"
    try:
        if args.browser:
            raise ImportError
        import webview
    except ImportError:
        print(f"Aura running at {url}  (Ctrl+C to quit)")
        webbrowser.open(url)
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            return
        return
    api = Api()
    win = webview.create_window("Aura", url, js_api=api, width=1320, height=840, min_size=(980, 640),
                                background_color="#0e1220")
    api.window = win
    webview.start()


if __name__ == "__main__":
    main()
