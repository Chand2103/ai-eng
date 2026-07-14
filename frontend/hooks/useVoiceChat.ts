"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { DEFAULT_WS_URL } from "@/lib/constants";

export type VoiceStatus =
  | "idle"
  | "connecting"
  | "connected"
  | "recording"
  | "processing"
  | "playing response"
  | "LLM error"
  | "TTS error"
  | "no speech detected"
  | "connection error"
  | "disconnected"
  | "worklet error"
  | "recording error";

interface UseVoiceChatOptions {
  url?: string;
  onTranscription?: (text: string) => void;
  onResponseText?: (text: string) => void;
}

export function useVoiceChat(options?: UseVoiceChatOptions) {
  const [status, setStatus] = useState<VoiceStatus>("idle");
  const [latency, setLatency] = useState<number | null>(null);
  const [transcription, setTranscription] = useState("");
  const [responseText, setResponseText] = useState("");
  const [adviceText, setAdviceText] = useState("");

  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioWorkletNodeRef = useRef<AudioWorkletNode | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const startTimeRef = useRef<number>(0);
  const urlRef = useRef(options?.url || DEFAULT_WS_URL);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      wsRef.current?.close();
      audioContextRef.current?.close();
    };
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setStatus("connecting");
    const ws = new WebSocket(urlRef.current);
    ws.binaryType = "arraybuffer";

    ws.onopen = () => {
      setStatus("connected");
    };

    ws.onmessage = (event) => {
      if (typeof event.data === "string") {
        if (event.data.startsWith("[LLM error")) {
          setStatus("LLM error");
        } else if (event.data.startsWith("[TTS error")) {
          setStatus("TTS error");
        } else if (event.data === "[no speech detected]") {
          setStatus("no speech detected");
        } else {
          setAdviceText(event.data);
        }
      } else {
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
  }, []);

  const startRecording = useCallback(async () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      connect();
      await new Promise((resolve) => {
        const checkConnection = () => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            resolve(true);
          } else {
            setTimeout(checkConnection, 100);
          }
        };
        checkConnection();
      });
    }

    setTranscription("");
    setResponseText("");
    setLatency(null);
    setStatus("recording");

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;

      if (!audioContextRef.current || audioContextRef.current.state === "closed") {
        const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
        audioContextRef.current = new AudioCtx();
      }

      const audioContext = audioContextRef.current;

      try {
        await audioContext.audioWorklet.addModule(
          "data:application/javascript," + encodeURIComponent(PCM_PROCESSOR_CODE)
        );
      } catch {
        try {
          await audioContext.audioWorklet.addModule("/pcm-processor.js");
        } catch {
          setStatus("worklet error");
          return;
        }
      }

      const workletNode = new AudioWorkletNode(audioContext, "pcm-processor", {
        processorOptions: { sampleRate: audioContext.sampleRate },
      });

      workletNode.port.onmessage = (event) => {
        if (event.data.type === "pcm") {
          let pcmData = event.data.pcm;
          if (audioContext.sampleRate !== 16000) {
            pcmData = resample(pcmData, audioContext.sampleRate, 16000);
          }
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(pcmData);
          }
        }
      };

      const source = audioContext.createMediaStreamSource(stream);
      source.connect(workletNode);
      workletNode.connect(audioContext.destination);

      audioWorkletNodeRef.current = workletNode;
      startTimeRef.current = performance.now();
    } catch {
      setStatus("recording error");
    }
  }, [connect]);

  const stopRecording = useCallback(async () => {
    if (audioWorkletNodeRef.current) {
      await new Promise<void>((resolve) => {
        audioWorkletNodeRef.current!.port.onmessage = (event) => {
          if (event.data.type === "flush_done") {
            resolve();
          }
        };
        audioWorkletNodeRef.current!.port.postMessage({ type: "flush" });
      });

      audioWorkletNodeRef.current.disconnect();
      audioWorkletNodeRef.current = null;
    }

    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(new Uint8Array(0));
    }

    setStatus("processing");
  }, []);

  const disconnect = useCallback(() => {
    stopRecording();
    wsRef.current?.close();
    audioContextRef.current?.close();
    setStatus("idle");
  }, [stopRecording]);

  const translateAndPlaySinhala = useCallback(async () => {
    if (!adviceText) return;
    setStatus("processing");
    const baseUrl = urlRef.current
      .replace(/^ws:/, "http:")
      .replace(/\/ws\/.*$/, "");
    try {
      const resp = await fetch(`${baseUrl}/tts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: adviceText,
          voice_id: 2,
          translate_to_si: true,
        }),
      });
      if (!resp.ok) {
        const err = await resp.text();
        console.error("Sinhala TTS failed:", err);
        return;
      }
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.play();
      setStatus("playing response");
    } catch (e) {
      console.error("Sinhala TTS error:", e);
    }
  }, [adviceText]);

  return {
    status,
    latency,
    transcription,
    responseText,
    adviceText,
    connect,
    startRecording,
    stopRecording,
    disconnect,
    translateAndPlaySinhala,
  };
}

/**
 * AudioWorklet processor for capturing raw 16-bit PCM at 16kHz.
 * Sends chunks via port messages.
 */
const PCM_PROCESSOR_CODE = `
class PCMProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super();
    this.sampleRate = options.processorOptions?.sampleRate || 44100;
    this.chunkSize = this.sampleRate / 50;
    this.buffer = [];
    this.isRunning = true;
    this.port.onmessage = (event) => {
      if (event.data.type === "flush") {
        if (this.buffer.length > 0) {
          const chunk = this.buffer.splice(0);
          const int16 = this.float32ToInt16(chunk);
          this.port.postMessage({ type: "pcm", pcm: int16 });
        }
        this.isRunning = false;
        this.port.postMessage({ type: "flush_done" });
      }
    };
  }
  process(inputs, outputs) {
    if (!this.isRunning) return false;
    const input = inputs[0];
    if (input && input.length > 0) {
      const channelData = input[0];
      for (let i = 0; i < channelData.length; i++) {
        this.buffer.push(channelData[i]);
      }
      if (this.buffer.length >= this.chunkSize) {
        const chunk = this.buffer.splice(0, this.chunkSize);
        const int16 = this.float32ToInt16(chunk);
        this.port.postMessage({ type: "pcm", pcm: int16 });
      }
    }
    return true;
  }
  float32ToInt16(float32Array) {
    const int16Array = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
      const s = Math.max(-1, Math.min(1, float32Array[i]));
      int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return int16Array.buffer;
  }
}
registerProcessor("pcm-processor", PCMProcessor);
`;

/**
 * Resample Int16Array from one sample rate to another.
 */
function resample(int16Array: ArrayBuffer, fromRate: number, toRate: number): ArrayBuffer {
  if (fromRate === toRate) return int16Array;
  const input = new Int16Array(int16Array);
  const ratio = toRate / fromRate;
  const outputLength = Math.ceil(input.length * ratio);
  const output = new Int16Array(outputLength);
  for (let i = 0; i < outputLength; i++) {
    const srcIndex = i / ratio;
    const srcIndexInt = Math.floor(srcIndex);
    const srcIndexFrac = srcIndex - srcIndexInt;
    if (srcIndexInt + 1 < input.length) {
      const sample0 = input[srcIndexInt];
      const sample1 = input[srcIndexInt + 1];
      output[i] = Math.round(sample0 * (1 - srcIndexFrac) + sample1 * srcIndexFrac);
    } else if (srcIndexInt < input.length) {
      output[i] = input[srcIndexInt];
    }
  }
  return output.buffer;
}
