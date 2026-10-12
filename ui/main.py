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
        self._floating = False
        self._normal_geometry = None
        self._float_lock = threading.RLock()
        self._native_frame = None

    def _set_native_frame(self, frameless):
        """Remove/restore the Windows title bar for a clean overlay; other OSes keep native chrome."""
        if not sys.platform.startswith("win") or self.window is None:
            return False
        try:
            import ctypes
            user32 = ctypes.windll.user32
            GWL_STYLE = -16
            WS_CAPTION = 0x00C00000
            SWP_NOSIZE, SWP_NOMOVE, SWP_NOZORDER, SWP_NOACTIVATE, SWP_FRAMECHANGED = 0x0001, 0x0002, 0x0004, 0x0010, 0x0020
            get_style = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
            set_style = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
            if not frameless and self._native_frame is not None:
                old_hwnd, old_style = self._native_frame
                set_style(old_hwnd, GWL_STYLE, old_style)
                user32.SetWindowPos(old_hwnd, 0, 0, 0, 0, 0,
                                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED)
                self._native_frame = None
                return True
            target_title = str(getattr(self.window, "title", "Aura") or "Aura")
            found = []
            enum_proc_type = getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE)(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)
            @enum_proc_type
            def enum_proc(hwnd, lparam):
                pid = ctypes.c_ulong(0)
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value != os.getpid():
                    return True
                buf = ctypes.create_unicode_buffer(512)
                user32.GetWindowTextW(hwnd, buf, len(buf))
                if buf.value == target_title:
                    found.append(hwnd)
                    return False
                return True
            user32.EnumWindows(enum_proc, 0)
            if not found:
                return False
            hwnd = found[0]
            if frameless:
                if self._native_frame is None:
                    self._native_frame = (hwnd, int(get_style(hwnd, GWL_STYLE)))
                old_hwnd, old_style = self._native_frame
                if hwnd != old_hwnd:
                    self._native_frame = (hwnd, int(get_style(hwnd, GWL_STYLE)))
                    old_hwnd, old_style = self._native_frame
                set_style(hwnd, GWL_STYLE, old_style & ~WS_CAPTION)
            elif self._native_frame is not None:
                old_hwnd, old_style = self._native_frame
                set_style(old_hwnd, GWL_STYLE, old_style)
                hwnd = old_hwnd
                self._native_frame = None
            else:
                return False
            user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                                SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED)
            return True
        except Exception:
            return False

    def _screen_bounds(self):
        """Return the bounds of the display currently containing the Aura window."""
        try:
            import webview
            screens = list(webview.screens or [])
            if not screens:
                raise RuntimeError("No display information")
            wx = int(getattr(self.window, "x", 0) or 0)
            wy = int(getattr(self.window, "y", 0) or 0)
            ww = int(getattr(self.window, "width", 0) or 0)
            wh = int(getattr(self.window, "height", 0) or 0)
            cx, cy = wx + ww / 2, wy + wh / 2
            for screen in screens:
                sx, sy = int(getattr(screen, "x", 0) or 0), int(getattr(screen, "y", 0) or 0)
                sw, sh = int(screen.width), int(screen.height)
                if sx <= cx < sx + sw and sy <= cy < sy + sh:
                    return sx, sy, sw, sh
            screen = screens[0]
            return int(getattr(screen, "x", 0) or 0), int(getattr(screen, "y", 0) or 0), int(screen.width), int(screen.height)
        except Exception:
            return 0, 0, 1366, 768

    def get_window_state(self):
        if self.window is None:
            return {"x": 0, "y": 0, "width": 1320, "height": 840, "floating": False}
        return {"x": int(self.window.x or 0), "y": int(self.window.y or 0),
                "width": int(self.window.width or 1320), "height": int(self.window.height or 840),
                "floating": self._floating}

    def set_floating_mode(self, payload):
        """Resize Aura into an always-on-top compact desktop player and restore it on exit."""
        payload = payload if isinstance(payload, dict) else {"enabled": bool(payload)}
        enabled = bool(payload.get("enabled", False))
        width, height = payload.get("width", 520), payload.get("height", 88)
        if self.window is None:
            raise RuntimeError("Aura's native window is not ready")
        with self._float_lock:
            if enabled:
                width = max(320, min(900, int(width or 520)))
                height = max(64, min(140, int(height or 88)))
                if not self._floating:
                    self._normal_geometry = {
                        "x": int(self.window.x or 0), "y": int(self.window.y or 0),
                        "width": int(self.window.width or 1320), "height": int(self.window.height or 840),
                        "on_top": bool(getattr(self.window, "on_top", False)),
                    }
                # Keep the same WebView/audio context alive; only the native window and its UI change.
                self._floating = True
                self.window.on_top = True
                self.window.resize(width, height)
                self._set_native_frame(True)
                sx, sy, sw, sh = self._screen_bounds()
                x = sx + max(8, sw - width - 18)
                y = sy + max(8, sh - height - 54)
                self.window.move(x, y)
                return {"ok": True, "floating": True, "width": width, "height": height, "x": x, "y": y}

            if self._floating:
                geometry = self._normal_geometry or {"x": 30, "y": 30, "width": 1320, "height": 840, "on_top": False}
                self._set_native_frame(False)
                self.window.on_top = bool(geometry.get("on_top", False))
                self.window.resize(max(720, int(geometry["width"])), max(480, int(geometry["height"])))
                self.window.move(int(geometry["x"]), int(geometry["y"]))
                self._floating = False
                self._normal_geometry = None
            return {"ok": True, "floating": False}

    def resize_floating_window(self, payload):
        payload = payload if isinstance(payload, dict) else {}
        if not self._floating or self.window is None:
            return {"ok": False, "floating": self._floating}
        width = max(320, min(900, int(payload.get("width", 520) or 520)))
        height = max(64, min(140, int(payload.get("height", 88) or 88)))
        with self._float_lock:
            self.window.resize(width, height)
        return {"ok": True, "width": width, "height": height}

    def move_floating_window(self, payload):
        payload = payload if isinstance(payload, dict) else {}
        if not self._floating or self.window is None:
            return {"ok": False, "floating": self._floating}
        sx, sy, sw, sh = self._screen_bounds()
        width, height = int(self.window.width or 520), int(self.window.height or 88)
        x = max(sx, min(int(payload.get("x", sx)), sx + sw - width))
        y = max(sy, min(int(payload.get("y", sy)), sy + sh - height))
        with self._float_lock:
            self.window.move(x, y)
        return {"ok": True, "x": x, "y": y}

    def dock_floating_window(self, payload):
        """Snap the floating player to whichever edge is closest after a drag."""
        payload = payload if isinstance(payload, dict) else {}
        if not self._floating or self.window is None:
            return {"ok": False, "floating": self._floating}
        sx, sy, sw, sh = self._screen_bounds()
        width, height = int(self.window.width or 520), int(self.window.height or 88)
        x, y = int(payload.get("x", sx)), int(payload.get("y", sy))
        gaps = {
            "left": abs(x - sx), "top": abs(y - sy),
            "right": abs((sx + sw) - (x + width)), "bottom": abs((sy + sh) - (y + height)),
        }
        edge = min(gaps, key=gaps.get)
        pad = 8
        if edge == "left": x = sx + pad
        elif edge == "right": x = sx + sw - width - pad
        x = max(sx + pad, min(x, sx + sw - width - pad))
        if edge == "top": y = sy + pad
        elif edge == "bottom": y = sy + sh - height - pad
        y = max(sy + pad, min(y, sy + sh - height - pad))
        with self._float_lock:
            self.window.move(x, y)
        return {"ok": True, "x": x, "y": y, "edge": edge}

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
    win = webview.create_window("Aura", url, js_api=api, width=1320, height=840, min_size=(300, 64),
                                background_color="#0e1220", resizable=True)
    api.window = win
    webview.start()


if __name__ == "__main__":
    main()
