"use client";

import { useEffect, useRef, useState } from "react";

const DEFAULT_URL = "ws://74.48.78.46:58604/ws/demo";

export default function Home() {
  const [serverUrl, setServerUrl] = useState(DEFAULT_URL);
  const [status, setStatus] = useState("idle");
  const [transcription, setTranscription] = useState("");
  const [responseText, setResponseText] = useState("");
  const [latency, setLatency] = useState<number | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const startTimeRef = useRef<number>(0);

  // Connect once on mount
  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const connect = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setStatus("connecting");
    const ws = new WebSocket(serverUrl);
    ws.binaryType = "arraybuffer";

    ws.onopen = () => {
      setStatus("connected");
    };

    ws.onmessage = (event) => {
      if (typeof event.data === "string") {
        // Server sent a text status/error message
        if (event.data.startsWith("[STT error")) {
          setStatus("STT error");
        } else if (event.data.startsWith("[LLM error")) {
          setStatus("LLM error");
        } else if (event.data.startsWith("[TTS error")) {
          setStatus("TTS error");
        } else if (event.data === "[no speech detected]") {
          setStatus("no speech detected");
        }
      } else {
        // Server sent audio bytes
        const wavBlob = new Blob([event.data], { type: "audio/wav" });
        const url = URL.createObjectURL(wavBlob);
        const audio = new Audio(url);
        audio.play();
        setLatency((performance.now() - startTimeRef.current) / 1000);
        setStatus("playing response");
      }
    };

    ws.onerror = () => {
      setStatus("connection error");
    };

    ws.onclose = () => {
      setStatus("disconnected");
      wsRef.current = null;
    };

    wsRef.current = ws;
  };

  const startRecording = async () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      connect();
    }

    audioChunksRef.current = [];
    setTranscription("");
    setResponseText("");
    setLatency(null);
    setStatus("recording");

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunksRef.current.push(event.data);
      }
    };

    mediaRecorder.onstop = async () => {
      const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
      const arrayBuffer = await audioBlob.arrayBuffer();

      // Server expects WAV bytes. Browsers record WebM, so we convert via
      // an offline AudioContext to a raw PCM buffer, then wrap it in a WAV
      // header before sending.
      const wavBytes = await convertWebmToWav(arrayBuffer);

      startTimeRef.current = performance.now();
      wsRef.current?.send(wavBytes);
      setStatus("waiting for response...");
    };

    mediaRecorder.start();
    mediaRecorderRef.current = mediaRecorder;
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    mediaRecorderRef.current?.stream.getTracks().forEach((t) => t.stop());
    setStatus("processing");
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 bg-zinc-50 p-6 text-zinc-900">
      <h1 className="text-3xl font-bold">Voice Agent</h1>

      <div className="flex w-full max-w-md flex-col gap-4">
        <label className="flex flex-col gap-1 text-sm font-medium">
          WebSocket URL
          <input
            type="text"
            value={serverUrl}
            onChange={(e) => setServerUrl(e.target.value)}
            className="rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm outline-none focus:border-blue-500"
          />
        </label>

        <div className="flex items-center justify-between rounded-lg border border-zinc-200 bg-white px-4 py-3">
          <span className="text-sm font-medium">Status</span>
          <span className="text-sm capitalize text-zinc-600">{status}</span>
        </div>

        <button
          onMouseDown={startRecording}
          onMouseUp={stopRecording}
          onTouchStart={startRecording}
          onTouchEnd={stopRecording}
          className="rounded-full bg-blue-600 px-6 py-4 text-lg font-semibold text-white shadow transition hover:bg-blue-700 active:scale-95"
        >
          Hold to Speak
        </button>

        {latency !== null && (
          <p className="text-center text-sm text-zinc-600">
            Round-trip latency: {latency.toFixed(2)}s
          </p>
        )}

        {transcription && (
          <div className="rounded-lg border border-zinc-200 bg-white p-4">
            <p className="text-xs font-semibold uppercase text-zinc-500">You said</p>
            <p className="text-sm">{transcription}</p>
          </div>
        )}

        {responseText && (
          <div className="rounded-lg border border-zinc-200 bg-white p-4">
            <p className="text-xs font-semibold uppercase text-zinc-500">AI</p>
            <p className="text-sm">{responseText}</p>
          </div>
        )}
      </div>
    </main>
  );
}

/**
 * Convert a WebM/Opus ArrayBuffer to a mono 16-bit PCM WAV ArrayBuffer.
 * The server (faster-whisper) accepts WAV bytes, so this client-side
 * conversion avoids forcing the backend to decode WebM.
 */
async function convertWebmToWav(webmBuffer: ArrayBuffer): Promise<ArrayBuffer> {
  const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
  const audioBuffer = await audioCtx.decodeAudioData(webmBuffer.slice(0));

  // Mix to mono and resample to 16 kHz (whisper's preferred rate).
  const targetSampleRate = 16000;
  const offlineCtx = new OfflineAudioContext(
    1,
    Math.ceil(audioBuffer.duration * targetSampleRate),
    targetSampleRate
  );
  const source = offlineCtx.createBufferSource();
  source.buffer = audioBuffer;
  source.connect(offlineCtx.destination);
  source.start();

  const rendered = await offlineCtx.startRendering();
  const samples = rendered.getChannelData(0);

  // Float32 -> 16-bit PCM
  const pcm = new Int16Array(samples.length);
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }

  return encodeWav(pcm, targetSampleRate, 1);
}

function encodeWav(
  samples: Int16Array,
  sampleRate: number,
  numChannels: number
): ArrayBuffer {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  const writeString = (offset: number, str: string) => {
    for (let i = 0; i < str.length; i++) {
      view.setUint8(offset + i, str.charCodeAt(i));
    }
  };

  writeString(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * numChannels * 2, true);
  view.setUint16(32, numChannels * 2, true);
  view.setUint16(34, 16, true); // bits per sample
  writeString(36, "data");
  view.setUint32(40, samples.length * 2, true);

  for (let i = 0; i < samples.length; i++) {
    view.setInt16(44 + i * 2, samples[i], true);
  }

  return buffer;
}
