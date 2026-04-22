import threading
import time
from io import BytesIO
from picamera2 import Picamera2
import base64

from http.server import BaseHTTPRequestHandler, HTTPServer

class CameraManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return

        self.cam = Picamera2()
        self.video_config = self.cam.create_video_configuration(
            main={"size": (640, 480)}
        )
        self.still_config = self.cam.create_still_configuration(
            main={"size": (640, 480)}
        )

        self.frame_jpeg = None
        self.http_server = None
        self.running = False
        self.lock = threading.Lock()

        self._initialized = True

    # -----------------------------
    # STREAMING
    # -----------------------------
    def start_stream(self):
        if self.running:
            return

        self.cam.configure(self.video_config)
        self.cam.start()
        self.running = True

        threading.Thread(target=self._update_stream_frames, daemon=True).start()

        self.http_server = HTTPServer(("0.0.0.0", 8000), StreamHandler)

        threading.Thread(target=self.http_server.serve_forever, daemon=True).start()

    def _update_stream_frames(self):
        while self.running:
            buf = BytesIO()
            self.cam.capture_file(buf, format="jpeg")
            buf.seek(0)

            with self.lock:
                self.frame_jpeg = buf.read()

    def get_jpeg_frame(self):
        with self.lock:
            return self.frame_jpeg
    
    def stop_stream(self):
        with self.lock:
            self.running = False
            self.cam.stop()
            if self.http_server:
                self.http_server.shutdown()
                self.http_server.server_close()
                self.http_server = None

    # -----------------------------
    # STILL CAPTURE
    # -----------------------------
    def capture_still(self):
        with self.lock:
            # Pause stream
            self.running = False
            self.cam.stop()

            # Switch to still mode
            self.cam.configure(self.still_config)
            self.cam.start()
            time.sleep(1)

            buf = BytesIO()
            self.cam.capture_file(buf, format="jpeg")
            buf.seek(0)
            data = buf.read()

            # Return to streaming mode
            self.cam.stop()
            self.cam.configure(self.video_config)
            self.cam.start()
            self.running = True

            data = base64.b64encode(data).decode("utf-8")
            filename = f"./agent/still_camera.jpg"
            with open(filename, "wb") as f:
                f.write(base64.b64decode(data))

            return data

class StreamHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/stream":
            self.send_error(404)
            return

        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=FRAME")
        self.end_headers()

        cam = CameraManager()

        while True:
            frame = cam.get_jpeg_frame()
            if frame:
                self.wfile.write(b"--FRAME\r\n")
                self.wfile.write(b"Content-Type: image/jpeg\r\n")
                self.wfile.write(f"Content-Length: {len(frame)}\r\n".encode())
                self.wfile.write(b"\r\n")
                self.wfile.write(frame)
                self.wfile.write(b"\r\n")
            time.sleep(0.03)