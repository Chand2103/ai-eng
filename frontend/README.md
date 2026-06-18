# Voice Agent Frontend

A minimal Next.js frontend for the voice-agent WebSocket server.

## Features

- Hold-to-speak button that records from the microphone.
- Converts browser-recorded WebM audio to WAV in the browser.
- Sends WAV bytes over WebSocket to the backend.
- Plays the AI's spoken response automatically when it arrives.
- Shows connection status and round-trip latency.

## Run locally

Make sure the backend server is running (e.g. `python server.py` on localhost:8000 or on Vast with an SSH tunnel).

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Connect to Vast instance

If the backend is on a Vast manual instance, set the WebSocket URL in the UI to:

```
ws://localhost:8000/ws/demo
```

(assuming you have an SSH tunnel: `ssh -p <port> root@<host> -L 8000:localhost:8000`).

For a remote server with HTTPS/WSS, use the full WSS URL.

## Notes

- The browser records audio as WebM/Opus, but the backend expects WAV. The frontend converts to mono 16-bit PCM WAV at 16 kHz before sending.
- The page uses the Web Audio API, which requires a secure context (HTTPS or localhost).
