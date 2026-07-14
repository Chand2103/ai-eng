#!/usr/bin/env python3
"""
Test script for the Vast serverless TTS endpoint.

Usage:
    python test_endpoint.py --endpoint-name inference-tts-ep --api-key YOUR_VAST_API_KEY

The script:
  1. Calls Vast's /route endpoint to get a live worker URL.
  2. POSTs a TTS request to the worker wrapped in {auth_data, payload}.
  3. Saves the returned WAV to output.wav.
"""

import argparse
import sys
import time

import httpx

ROUTE_URL = "https://run.vast.ai/route/"


def main():
    parser = argparse.ArgumentParser(description="Test Vast serverless TTS endpoint")
    parser.add_argument("--endpoint-name", required=True, help="Vast endpoint name")
    parser.add_argument("--api-key", required=True, help="Vast.ai API key")
    parser.add_argument("--text", default="Hello, this is a test of the text to speech system. How are you doing today?")
    parser.add_argument("--voice-id", type=int, default=1, help="Voice ID (1 = Alice)")
    parser.add_argument("--output", default="output.wav", help="Output WAV file")
    parser.add_argument("--max-retries", type=int, default=12, help="Max retries for cold start (12 = ~120s)")
    args = parser.parse_args()

    # 1. Get worker URL + auth_data
    print(f"Routing to endpoint '{args.endpoint_name}'...")

    for attempt in range(1, args.max_retries + 1):
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    ROUTE_URL,
                    headers={
                        "Authorization": f"Bearer {args.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"endpoint": args.endpoint_name, "cost": 100},
                )
                resp.raise_for_status()
                data = resp.json()
                if "url" not in data:
                    print(f"  No worker ready yet (attempt {attempt}/{args.max_retries}, status={data.get('status', '?')}), waiting 10s...")
                    time.sleep(10)
                    continue
                worker_url = data["url"].rstrip("/")
                auth_data = {
                    "signature": data["signature"],
                    "cost": data.get("cost", 100),
                    "endpoint": data.get("endpoint", args.endpoint_name),
                    "reqnum": data["reqnum"],
                    "url": data["url"],
                    "request_idx": data.get("reqnum", 0),
                }
                break
        except httpx.HTTPStatusError as e:
            print(f"  Route error: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"  Route error: {e}")
            sys.exit(1)
    else:
        print("  Max retries reached — no worker became available.")
        sys.exit(1)

    print(f"  Worker URL: {worker_url}")

    # 2. Call TTS via PyWorker (wrapped in auth_data + payload)
    print(f"Calling /tts with voice_id={args.voice_id}...")
    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(
                f"{worker_url}/tts",
                json={
                    "auth_data": auth_data,
                    "payload": {
                        "text": args.text,
                        "ref_audio": "ref-aud.wav",
                        "ref_text": "Hi, This is alice, how are you doing today?",
                        "voice_id": args.voice_id,
                    },
                },
            )
            if resp.status_code != 200:
                print(f"  Status: {resp.status_code}")
                print(f"  Response: {resp.text[:500]}")
            resp.raise_for_status()
            wav_bytes = resp.content
    except Exception as e:
        print(f"  TTS call failed: {e}")
        sys.exit(1)

    # 3. Save
    with open(args.output, "wb") as f:
        f.write(wav_bytes)
    print(f"  Saved {len(wav_bytes)} bytes to '{args.output}'")
    print("  Done!")


if __name__ == "__main__":
    main()
