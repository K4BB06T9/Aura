"""Build a single-file desktop executable:  python build.py   (needs: pip install pyinstaller)"""
import os, subprocess, sys
sep = ";" if os.name == "nt" else ":"
subprocess.check_call([sys.executable, "-m", "PyInstaller", "--noconfirm", "--windowed", "--onefile", "--name", "Aura",
                       "--add-data", f"ui{sep}ui", "--collect-all", "ytmusicapi", "--collect-all", "yt_dlp", "--collect-all", "mutagen", "main.py"])
print("Done - see dist/")
