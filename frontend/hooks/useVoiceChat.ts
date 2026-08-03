"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { DEFAULT_WS_URL } from "@/lib/constants";
import { createSessionId, parseFeedback } from "@/lib/utils";

export type VoiceStatus =
  | "idle"
  | "connecting"
  | "connected"
  | "recording"
  | "processing"
  | "playing response"
  | "roleplay complete"
  | "LLM error"
  | "TTS error"
  | "no speech detected"
  | "connection error"
  | "disconnected"
  | "worklet error"
  | "recording error";

interface UseVoiceChatOptions {
  url?: string;
  mode?: string;
  topicId?: string;
  sessionId?: string;
  onTranscription?: (text: string) => void;
  onResponseText?: (text: string) => void;
}

export function useVoiceChat(options?: UseVoiceChatOptions) {
  const [status, setStatus] = useState<VoiceStatus>("idle");
  const [latency, setLatency] = useState<number | null>(null);
  const [transcription, setTranscription] = useState("");
  const [responseText, setResponseText] = useState("");
  const [adviceText, setAdviceText] = useState("");

  const isRoleplay = options?.mode === "roleplay";
  const [micDisabled, setMicDisabled] = useState(isRoleplay);
  const awaitingOpeningRef = useRef(isRoleplay);
  const [roleplayEnded, setRoleplayEnded] = useState(false);
  const roleplayEndedRef = useRef(false);
  const [feedbackText, setFeedbackText] = useState("");
  const feedbackReady = parseFeedback(feedbackText);
  // True once the roleplay ending has been triggered (manual button or
  // [roleplay_complete]): subsequent text messages from the socket are
  // the feedback JSON report, not regular advice.
  const feedbackPendingRef = useRef(false);

  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const startTimeRef = useRef<number>(0);
  // Synchronous press state: set true on pointer down, false on pointer up,
  // so a quick tap can't race an async mic setup (see startRecording).
  const recordingRef = useRef(false);
  // Track every live worklet node + media stream so stop/cleanup never
  // misses an orphaned one (leaked nodes kept pumping audio to AWS).
  const workletNodesRef = useRef<Set<AudioWorkletNode>>(new Set());
  const mediaStreamsRef = useRef<Set<MediaStream>>(new Set());
  const [sessionId, setSessionId] = useState(() => options?.sessionId || createSessionId());
  const [wsUrl, setWsUrl] = useState(() => options?.url || buildConversationUrl(options?.mode, options?.topicId, sessionId));
  const urlRef = useRef(wsUrl);

  // Called once the roleplay reaches its end and the socket has delivered
  // the feedback. Either the user clicked "End roleplay and get feedback"
  // or the backend sent the completion marker and then closed the socket
  // after the feedback (JSON text + spoken audio).
  const completeRoleplay = useCallback((fallbackFeedback?: string) => {
    roleplayEndedRef.current = true;
    feedbackPendingRef.current = false;
    setRoleplayEnded(true);
    setMicDisabled(false);
    setStatus("roleplay complete");
    wsRef.current?.close();
    if (fallbackFeedback) setFeedbackText(fallbackFeedback);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      wsRef.current?.close();
      audioContextRef.current?.close();
      stopAllAudioSources(workletNodesRef, mediaStreamsRef);
    };
  }, []);

  const connect = useCallback(() => {
    // Only open a fresh socket when there is none, or the previous one is
    // fully closed. A CONNECTING/OPEN/CLOSING socket means a connection is
    // already in flight — creating another would duplicate the backend
    // handler (and the roleplay opening).
    if (wsRef.current && wsRef.current.readyState !== WebSocket.CLOSED) return;

    setStatus("connecting");
    if (isRoleplay) {
      awaitingOpeningRef.current = true;
      setMicDisabled(true);
    }
    const ws = new WebSocket(urlRef.current);
    ws.binaryType = "arraybuffer";

    ws.onopen = () => {
      setStatus("connected");
    };

    ws.onmessage = (event) => {
      if (typeof event.data === "string") {
        const msg = event.data;
        if (msg.startsWith("[LLM error")) {
          setStatus("LLM error");
        } else if (msg.startsWith("[TTS error")) {
          setStatus("TTS error");
        } else if (msg === "[no speech detected]") {
          setStatus("no speech detected");
        } else if (msg === "[roleplay_complete]") {
          // The persona wrapped up the scene on its own. The backend will
          // now stream the feedback and then close the socket — keep it
          // open so the feedback messages arrive.
          feedbackPendingRef.current = true;
          setMicDisabled(true);
          setStatus("roleplay complete");
        } else if (feedbackPendingRef.current) {
          // Raw JSON feedback report (or a [feedback ...] notice).
          setFeedbackText(msg);
          setStatus("roleplay complete");
        } else {
          setAdviceText(msg);
        }
        if (awaitingOpeningRef.current) {
          awaitingOpeningRef.current = false;
          setMicDisabled(false);
        }
      } else {
        const wavBlob = new Blob([event.data], { type: "audio/wav" });
        const url = URL.createObjectURL(wavBlob);
        const audio = new Audio(url);
        audio.onended = () => {
          if (awaitingOpeningRef.current) {
            awaitingOpeningRef.current = false;
            setMicDisabled(false);
          }
          setStatus("connected");
        };
        audio.play();
        setLatency((performance.now() - startTimeRef.current) / 1000);
        setStatus("playing response");
      }
    };

    ws.onerror = () => {
      setStatus("connection error");
      if (awaitingOpeningRef.current) {
        awaitingOpeningRef.current = false;
        setMicDisabled(false);
      }
    };

    ws.onclose = () => {
      // Only clear the ref if this socket is still the live one — a
      // restarted roleplay may have already replaced it.
      if (wsRef.current === ws) wsRef.current = null;
      if (feedbackPendingRef.current) {
        // The backend streamed the feedback and closed the socket — the
        // roleplay ending flow is complete.
        completeRoleplay();
      } else if (!roleplayEndedRef.current) {
        setStatus("disconnected");
      }
      if (awaitingOpeningRef.current) {
        awaitingOpeningRef.current = false;
        setMicDisabled(false);
      }
      // A dead socket must never keep streaming mic audio.
      recordingRef.current = false;
      stopAllAudioSources(workletNodesRef, mediaStreamsRef);
    };

    wsRef.current = ws;
  }, [isRoleplay, completeRoleplay]);

  // Roleplays are auto-started: connect on mount so the opening line
  // can be generated and played before the mic becomes usable.
  useEffect(() => {
    if (isRoleplay) {
      setTimeout(connect, 0);
    }
  }, [connect, isRoleplay]);

  const startRecording = useCallback(async () => {
    // Re-entry guard: a second press while already recording must not stack
    // another worklet node / mic stream (that leaked audio to AWS).
    if (recordingRef.current) return;
    recordingRef.current = true;

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

    // If an opening line is still playing (roleplay reconnect after an
    // error), hold off recording until it finishes.
    if (awaitingOpeningRef.current) {
      await new Promise((resolve) => {
        const checkOpening = () => {
          if (!awaitingOpeningRef.current) {
            resolve(true);
          } else {
            setTimeout(checkOpening, 100);
          }
        };
        checkOpening();
      });
    }

    // Released while connecting / waiting for the opening.
    if (!recordingRef.current) return;

    setTranscription("");
    setResponseText("");
    setLatency(null);
    setStatus("recording");

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!recordingRef.current) {
        // Released while the mic was being opened — stop immediately.
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      mediaStreamsRef.current.add(stream);

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
          recordingRef.current = false;
          stream.getTracks().forEach((track) => track.stop());
          mediaStreamsRef.current.delete(stream);
          setStatus("worklet error");
          return;
        }
      }

      if (!recordingRef.current) {
        // Released while the worklet was loading.
        stream.getTracks().forEach((track) => track.stop());
        mediaStreamsRef.current.delete(stream);
        return;
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

      workletNodesRef.current.add(workletNode);
      startTimeRef.current = performance.now();
    } catch {
      recordingRef.current = false;
      setStatus("recording error");
    }
  }, [connect]);

  const stopRecording = useCallback(async () => {
    if (!recordingRef.current) return;
    recordingRef.current = false;

    // Snapshot + clear first: a press starting during the flush must keep
    // its own node/stream tracked instead of having it swept up here.
    const nodesToStop = Array.from(workletNodesRef.current);
    workletNodesRef.current.clear();
    const streamsToStop = Array.from(mediaStreamsRef.current);
    mediaStreamsRef.current.clear();

    // Flush + disconnect every captured worklet node (normally just one,
    // but a previously leaked node is stopped here too).
    for (const node of nodesToStop) {
      await flushWorkletNode(node);
      try {
        node.disconnect();
      } catch {
        // already disconnected
      }
    }

    for (const stream of streamsToStop) {
      stream.getTracks().forEach((track) => track.stop());
    }

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(new Uint8Array(0));
    }

    setStatus("processing");
  }, []);

  const disconnect = useCallback(() => {
    void stopRecording();
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

  const endRoleplay = useCallback(async () => {
    await stopRecording();
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      // The backend will stream the feedback (JSON + spoken audio), then
      // close the socket, which finalises the ending via completeRoleplay.
      feedbackPendingRef.current = true;
      setMicDisabled(true);
      setStatus("roleplay complete");
      wsRef.current.send(END_ROLEPLAY_COMMAND);
    } else {
      completeRoleplay(
        "The connection was lost before feedback could be generated."
      );
    }
  }, [stopRecording, completeRoleplay]);

  const restartRoleplay = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    roleplayEndedRef.current = false;
    feedbackPendingRef.current = false;
    const newId = createSessionId();
    setSessionId(newId);
    const newUrl = options?.url || buildConversationUrl(options?.mode, options?.topicId, newId);
    setWsUrl(newUrl);
    urlRef.current = newUrl;
    setTranscription("");
    setResponseText("");
    setAdviceText("");
    setFeedbackText("");
    setLatency(null);
    setRoleplayEnded(false);
    awaitingOpeningRef.current = true;
    setMicDisabled(true);
    connect();
  }, [connect, options]);

  return {
    status,
    latency,
    transcription,
    responseText,
    adviceText,
    feedbackText,
    feedbackReady,
    sessionId,
    micDisabled,
    roleplayEnded,
    connect,
    startRecording,
    stopRecording,
    disconnect,
    translateAndPlaySinhala,
    endRoleplay,
    restartRoleplay,
  };
}

/**
 * Build the orchestrator WebSocket URL for a conversation session.
 * Each conversation gets a unique session id in the path (no shared
 * /demo session), with mode/topic query params so the backend can pick
 * the right system prompt (e.g. a roleplay scenario).
 */
// Text command sent to the orchestrator when the student presses
// "End roleplay and get feedback". Mirrors the backend's
// END_ROLEPLAY_COMMAND.
const END_ROLEPLAY_COMMAND = "[end_roleplay]";

function buildConversationUrl(mode?: string, topicId?: string, sessionId?: string): string {
  const id = sessionId || createSessionId();
  const baseUrl = DEFAULT_WS_URL.replace(/\/ws\/[^/?]*$/, "");
  const base = `${baseUrl}/ws/${id}`;
  const params = new URLSearchParams();
  if (mode) params.set("mode", mode);
  if (topicId) params.set("topic", topicId);
  const qs = params.toString();
  return qs ? `${base}?${qs}` : base;
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

/**
 * Ask a worklet node to flush its remaining PCM buffer, resolving when the
 * node confirms (or after a 1s safety timeout).
 */
function flushWorkletNode(node: AudioWorkletNode): Promise<void> {
  return new Promise((resolve) => {
    const timer = setTimeout(resolve, 1000);
    const onMessage = (event: MessageEvent) => {
      if (event.data && event.data.type === "flush_done") {
        clearTimeout(timer);
        node.port.removeEventListener("message", onMessage);
        resolve();
      }
    };
    node.port.addEventListener("message", onMessage);
    node.port.postMessage({ type: "flush" });
  });
}

/**
 * Disconnect every tracked worklet node and stop every tracked mic stream.
 * Call sites pass the hook's refs (a module-level helper so hook effects
 * don't need it as a dependency).
 */
function stopAllAudioSources(
  workletNodes: { current: Set<AudioWorkletNode> },
  mediaStreams: { current: Set<MediaStream> }
) {
  for (const node of workletNodes.current) {
    try {
      node.disconnect();
    } catch {
      // already disconnected
    }
  }
  workletNodes.current.clear();
  for (const stream of mediaStreams.current) {
    stream.getTracks().forEach((track) => track.stop());
  }
  mediaStreams.current.clear();
}
