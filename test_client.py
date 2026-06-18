#!/usr/bin/env python3
"""
Standalone test client for the voice-agent WebSocket server.

Usage:
    python test_client.py --url ws://localhost:8000/ws/test --audio input1.wav
    python test_client.py --host localhost --port 8000 --session demo --audio input1.wav

Environment variables:
    VOICE_AGENT_URL   WebSocket URL (overridden by --url)
    VOICE_AGENT_HOST  Server host (default: localhost)
    VOICE_AGENT_PORT  Server port (default: 8000)
"""

import argparse
import os
import time
import wave

import websockets
import soundfile as sf


def build_url(args) -> str:
    if args.url:
        return args.url
    host = args.host or os.getenv("VOICE_AGENT_HOST", "localhost")
    port = args.port or int(os.getenv("VOICE_AGENT_PORT", "8000"))
    session = args.session or "test"
    return f"ws://{host}:{port}/ws/{session}"


def main():
    parser = argparse.ArgumentParser(
        description="Send a WAV file to the voice-agent WebSocket server and save the response."
    )
    parser.add_argument(
        "--url",
        default=os.getenv("VOICE_AGENT_URL"),
        help="Full WebSocket URL (e.g. ws://localhost:8000/ws/test)",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("VOICE_AGENT_HOST", "localhost"),
        help="Server host",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("VOICE_AGENT_PORT", "8000")),
        help="Server port",
    )
    parser.add_argument(
        "--session",
        default="test",
        help="Session ID to use in the WebSocket path",
    )
    parser.add_argument(
        "--audio",
        required=True,
        help="Path to the input WAV file to send",
    )
    parser.add_argument(
        "--output",
        default="response.wav",
        help="Path to write the returned audio",
    )
    args = parser.parse_args()

    url = build_url(args)
    print(f"Connecting to {url} ...")

    with open(args.audio, "rb") as f:
        audio_bytes = f.read()

    print(f"Sending {len(audio_bytes)} bytes from {args.audio}")

    start = time.time()

    async def run():
        async with websockets.connect(url) as ws:
            await ws.send(audio_bytes)
            print("Audio sent, waiting for response...")

            response = await ws.recv()
            latency = time.time() - start

            if isinstance(response, str):
                print(f"Server returned text: {response}")
            else:
                with open(args.output, "wb") as out:
                    out.write(response)
                print(f"Saved {len(response)} response bytes to {args.output}")

            print(f"Round-trip latency: {latency:.3f}s")

    import asyncio
    asyncio.run(run())


if __name__ == "__main__":
    main()
