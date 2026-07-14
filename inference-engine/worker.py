#!/usr/bin/env python3
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
TTS_LOG_FILE = os.getenv("TTS_LOG_FILE", "/tmp/tts_server.log")


def start_tts_server() -> subprocess.Popen:
    logger.info("Starting TTS server...")
    log_fh = open(TTS_LOG_FILE, "wb")
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "tts_server:app",
            "--host", "0.0.0.0",
            "--port", str(TTS_SERVER_PORT),
            "--log-level", "info",
        ],
        stdout=log_fh,
        stderr=subprocess.STDOUT,
    )
    return proc


def wait_for_ready(proc: subprocess.Popen, marker: str = "OmniVoice loaded", timeout: int = 600) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        ret = proc.poll()
        if ret is not None:
            logger.error("TTS server exited prematurely (code %s). Dumping log:", ret)
            _dump_log()
            raise RuntimeError(f"TTS server exited with code {ret} before printing '{marker}'")
        if os.path.exists(TTS_LOG_FILE):
            with open(TTS_LOG_FILE, "r") as f:
                content = f.read()
                if marker in content:
                    logger.info("TTS server is ready.")
                    return
        time.sleep(1)
    logger.error("TTS server did not become ready within %ss. Dumping log:", timeout)
    _dump_log()
    raise RuntimeError(f"TTS server did not print '{marker}' within {timeout}s")


def _dump_log() -> None:
    if os.path.exists(TTS_LOG_FILE):
        with open(TTS_LOG_FILE, "r") as f:
            for line in f.readlines()[-50:]:
                logger.error("  | %s", line.rstrip())


def main():
    proc = start_tts_server()
    wait_for_ready(proc)

    from vastai import Worker, WorkerConfig, HandlerConfig, BenchmarkConfig, LogActionConfig

    handler = HandlerConfig(
        route="/tts",
        allow_parallel_requests=False,
        workload_calculator=lambda payload: float(len(payload.get("text", ""))),
        benchmark_config=BenchmarkConfig(
            generator=lambda: {
                "text": "Hello, this is a benchmark test for the TTS system.",
                "ref_audio": "ref-aud.wav",
                "ref_text": "Hi, This is alice, how are you doing today?",
                "voice_id": 1,
            },
            runs=4,
            concurrency=1,
        ),
    )

    config = WorkerConfig(
        model_server_url="http://127.0.0.1",
        model_server_port=TTS_SERVER_PORT,
        model_log_file=TTS_LOG_FILE,
        handlers=[handler],
        log_action_config=LogActionConfig(
            on_load="OmniVoice loaded",
        ),
    )

    logger.info("Starting Vast PyWorker...")
    worker = Worker(config=config)
    worker.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Shutting down.")
