"""Bounded non-microphone WebSocket load helper."""

import json
import os

from websocket import create_connection


def run_once() -> None:
    target = os.getenv("VOICE_LOAD_URL", "ws://127.0.0.1:8000/api/v1/voice/ws")
    api_key = os.getenv("VOICE_LOAD_API_KEY", "<CLIENT_API_KEY>")
    socket = create_connection(target, header=[f"X-API-Key: {api_key}"], timeout=10)
    try:
        socket.send(
            json.dumps(
                {
                    "type": "session.start",
                    "protocol_version": "1.0",
                    "language": "en-IN",
                    "audio": {
                        "format": "pcm_s16le",
                        "sample_rate": 16000,
                        "channels": 1,
                        "frame_duration_ms": 20,
                    },
                }
            )
        )
        socket.recv()
        for _ in range(10):
            socket.send_binary(b"\xff\x7f" * 320)
        socket.send(json.dumps({"type": "audio.commit"}))
        while True:
            event = socket.recv()
            if isinstance(event, str) and '"type":"assistant.audio.end"' in event.replace(" ", ""):
                break
        socket.send(json.dumps({"type": "session.end"}))
    finally:
        socket.close()


if __name__ == "__main__":
    run_once()
