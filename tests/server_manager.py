import subprocess
import time
import signal
import threading
import queue
from config import SERVER_EXECUTABLE, DEFAULT_HOST, DEFAULT_PORT, STARTUP_TIMEOUT


class ServerManager:
    def __init__(self, port=DEFAULT_PORT, host=DEFAULT_HOST):
        self.port = port
        self.host = host
        self.process = None
        self.stdout_lines = []
        self.stderr_lines = []
        self.stdout_thread = None
        self.stderr_thread = None

    def _read_stream(self, stream, lines_list):
        for line in iter(stream.readline, b''):
            decoded = line.decode('utf-8', errors='replace').rstrip()
            lines_list.append(decoded)
            print(f"[SERVER] {decoded}")
        stream.close()

    def start(self):
        self.process = subprocess.Popen(
            [SERVER_EXECUTABLE, str(self.port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        
        self.stdout_thread = threading.Thread(
            target=self._read_stream,
            args=(self.process.stdout, self.stdout_lines),
            daemon=True
        )
        self.stderr_thread = threading.Thread(
            target=self._read_stream,
            args=(self.process.stderr, self.stderr_lines),
            daemon=True
        )
        self.stdout_thread.start()
        self.stderr_thread.start()
        
        time.sleep(STARTUP_TIMEOUT)
        if self.process.poll() is not None:
            raise RuntimeError("Server failed to start")

    def stop(self):
        if self.process:
            self.process.send_signal(signal.SIGTERM)
            self.process.wait(timeout=5)
            self.process = None

    def is_running(self):
        if not self.process:
            return False
        return self.process.poll() is None

    def get_base_url(self):
        return f"http://{self.host}:{self.port}"

    def get_logs(self):
        return {
            "stdout": self.stdout_lines.copy(),
            "stderr": self.stderr_lines.copy()
        }

    def print_logs(self):
        print("\n=== Server stdout ===")
        for line in self.stdout_lines:
            print(line)
        print("\n=== Server stderr ===")
        for line in self.stderr_lines:
            print(line)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
