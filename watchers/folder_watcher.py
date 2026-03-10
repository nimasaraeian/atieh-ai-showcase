import time
import os
import requests

WATCH_FOLDER = r"C:\AtiehAI\incoming"
IMPORT_ENDPOINT = "http://127.0.0.1:8000/imports/run"

CHECK_INTERVAL = 5  # seconds


def has_files(folder):
    try:
        return any(
            os.path.isfile(os.path.join(folder, f))
            for f in os.listdir(folder)
        )
    except Exception:
        return False


def run_import():
    try:
        r = requests.post(IMPORT_ENDPOINT)
        print("Import triggered:", r.status_code)
        try:
            print(r.json())
        except Exception:
            print(r.text)
    except Exception as e:
        print("Import failed:", e)


def start_watcher():
    print("Auto Folder Watcher started...")
    print("Watching:", WATCH_FOLDER)

    while True:
        try:
            if has_files(WATCH_FOLDER):
                print("New file detected in incoming folder")
                run_import()

                # wait a bit to allow processing
                time.sleep(10)

        except Exception as e:
            print("Watcher error:", e)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    start_watcher()