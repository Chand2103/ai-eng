"use client";

import { Suspense, useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { ArrowLeft, Clock, Home, RotateCcw } from "lucide-react";
import { useVoiceChat } from "@/hooks/useVoiceChat";
import Avatar from "@/components/ui/Avatar";
import MicButton from "@/components/ui/MicButton";
import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";
import { formatDuration } from "@/lib/utils";
import withAuth from "@/components/auth/withAuth";

function getStatusText(status: string): string {
  switch (status) {
    case "idle":
    case "connected":
      return "Tap to speak";
    case "connecting":
      return "Connecting...";
    case "recording":
      return "Listening...";
    case "processing":
      return "Processing...";
    case "playing response":
      return "AI is speaking...";
    case "LLM error":
    case "TTS error":
      return "Something went wrong";
    case "no speech detected":
      return "No speech detected";
    case "connection error":
    case "disconnected":
      return "Connection lost";
    default:
      return status;
  }
}

function ConversationContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const mode = searchParams.get("mode") || "free-talk";
  const topic = searchParams.get("topic") || null;

  const { status, latency, startRecording, stopRecording, disconnect } = useVoiceChat();
  const [showEndModal, setShowEndModal] = useState(false);
  const [sessionStart] = useState(() => Date.now());
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (showEndModal) return;
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - sessionStart) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, [sessionStart, showEndModal]);

  const modeLabel =
    mode === "free-talk"
      ? "Free Talk"
      : mode === "roleplay"
      ? `Roleplay: ${topic || "Unknown"}`
      : mode === "ielts"
      ? "IELTS Prep"
      : "Conversation";

  const isAiSpeaking = status === "playing response";
  const isRecording = status === "recording";

  const handleEnd = () => {
    disconnect();
    setShowEndModal(true);
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col bg-[#F8F7F4]">
      <div className="flex items-center justify-between border-b border-[#E2E2DC] bg-white px-4 py-3">
        <button
          onClick={() => router.push("/practice")}
          className="flex items-center gap-1.5 text-sm font-medium text-[#6B6B66] hover:text-[#1A1A18] transition-colors duration-150 cursor-pointer"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>
        <span className="text-sm font-semibold text-[#1A1A18]">{modeLabel}</span>
        <Button variant="danger" onClick={handleEnd} className="px-4 py-2 text-xs">
          End session
        </Button>
      </div>

      <div className="flex flex-1 flex-col items-center justify-center gap-6 px-4">
        <Avatar isSpeaking={isAiSpeaking} />
        <p className="text-sm font-medium text-[#6B6B66]">{getStatusText(status)}</p>

        {latency !== null && (
          <p className="text-xs text-[#6B6B66]">
            Round-trip latency: {latency.toFixed(2)}s
          </p>
        )}

        <div className="mt-4 h-32 w-full max-w-lg overflow-y-auto rounded-xl border border-[#E2E2DC] bg-white p-4">
          <p className="text-center text-xs text-[#6B6B66]">
            Conversation transcript will appear here
          </p>
        </div>
      </div>

      <div className="flex flex-col items-center gap-2 border-t border-[#E2E2DC] bg-white px-4 py-6">
        <MicButton
          isRecording={isRecording}
          onMouseDown={startRecording}
          onMouseUp={stopRecording}
          onTouchStart={startRecording}
          onTouchEnd={stopRecording}
        />
      </div>

      <Modal open={showEndModal} onClose={() => setShowEndModal(false)} title="Session complete!">
        <div className="flex flex-col items-center gap-4 py-2">
          <div className="flex items-center gap-2 text-sm text-[#6B6B66]">
            <Clock className="h-4 w-4" />
            Duration: {formatDuration(elapsed)}
          </div>
          <div className="flex w-full gap-3">
            <Button
              variant="outline"
              className="flex-1"
              icon={<RotateCcw className="h-4 w-4" />}
              onClick={() => {
                setShowEndModal(false);
                window.location.reload();
              }}
            >
              Practice again
            </Button>
            <Button
              variant="primary"
              className="flex-1"
              icon={<Home className="h-4 w-4" />}
              onClick={() => router.push("/practice")}
            >
              Back to home
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

function ConversationPage() {
  return (
    <Suspense fallback={<div className="flex h-[calc(100vh-4rem)] items-center justify-center">Loading...</div>}>
      <ConversationContent />
    </Suspense>
  );
}

export default withAuth(ConversationPage);
