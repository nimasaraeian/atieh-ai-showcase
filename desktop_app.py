import threading
import time
import webview
import uvicorn


def run_server():
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="warning"
    )


if __name__ == "__main__":
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    time.sleep(2)

    webview.create_window(
        "Atieh AI",
        "http://127.0.0.1:8000",
        width=1400,
        height=900,
        min_size=(1100, 700)
    )

    webview.start()