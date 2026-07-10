#!/usr/bin/env python3
"""
Vast.ai PyWorker for the inference-engine TTS server.

This script is the **entrypoint** of the serverless Docker image.  It:

1. Starts the TTS HTTP server (``tts_server.py``) as a subprocess on port 8080.
2. Blocks until the server prints ``OmniVoice loaded``.
3. Launches the Vast PyWorker which registers with Vast's infrastructure and
   proxies /tts requests to the local server.

Usage (inside the container)::

    python worker.py

Environment variables
---------------------
TTS_SERVER_PORT    Port for the TTS HTTP server (default 8080).
WORKER_PORT        Port for the Vast worker to listen on (default 8081).
"""

import os
import sys
import time
import logging
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

TTS_SERVER_PORT = int(os.getenv("TTS_SERVER_PORT", "8080"))


def start_tts_server() -> subprocess.Popen:
    """Launch ``tts_server.py`` and return the process handle."""
    logger.info("Starting TTS server...")
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "tts_server:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(TTS_SERVER_PORT),
            "--log-level",
            "info",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return proc


def wait_for_ready(proc: subprocess.Popen, marker: str = "OmniVoice loaded") -> None:
    """Read server stdout until *marker* appears, then return."""
    for line in iter(proc.stdout.readline, b""):
        decoded = line.decode(errors="replace").rstrip()
        print(decoded)
        if marker in decoded:
            logger.info("TTS server is ready.")
            return


def main():
    # 1. Start the TTS server
    server_proc = start_tts_server()

    # 2. Wait for model load to finish
    wait_for_ready(server_proc)

    # 3. Start Vast PyWorker (blocking)
    from vastai import Worker, WorkerConfig, HandlerConfig, BenchmarkConfig, LogActionConfig

    handler = HandlerConfig(
        route="/tts",
        method="POST",
        health_route="/health",
    )

    benchmark = BenchmarkConfig(
        generator_payload={
            "text": "Hello, this is a benchmark test for the TTS system.",
            "ref_audio": "ref-aud.wav",
            "ref_text": "Hi, This is alice, how are you doing today?",
            "voice_id": 1,
        },
        workload_calculator=lambda payload: len(payload.get("text", "")),
    )

    log_action = LogActionConfig(on_load="OmniVoice loaded")

    config = WorkerConfig(
        handlers=[handler],
        benchmark=benchmark,
        log_action=log_action,
    )

    logger.info("Starting Vast PyWorker...")
    worker = Worker(config=config)
    worker.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Shutting down.")
