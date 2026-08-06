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
    case "roleplay complete":
      return "Roleplay complete!";
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
  const topicId = searchParams.get("topicId") || null;

  const { status, latency, adviceText, micDisabled, roleplayEnded, feedbackText, feedbackReady, startRecording, stopRecording, disconnect, translateAndPlaySinhala, endRoleplay, restartRoleplay } = useVoiceChat({
    mode,
    topicId: topicId || undefined,
  });
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
      ? "IELTS Speaking Test"
      : "Conversation";

  const isAiSpeaking = status === "playing response";
  const isRecording = status === "recording";
  const isRoleplay = mode === "roleplay";
  const isIelts = mode === "ielts";

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

        <div className="mt-4 w-full max-w-lg space-y-2">
          <div className="h-40 overflow-y-auto rounded-xl border border-[#E2E2DC] bg-white p-4">
            {roleplayEnded && feedbackReady ? (
              isIelts && feedbackReady.overall_band !== undefined ? (
                /* IELTS feedback */
                <div className="space-y-2 text-xs leading-relaxed text-[#1A1A18]">
                  <div className="flex items-center justify-between border-b border-[#F0F0EA] pb-1">
                    <p className="font-semibold">Overall band score</p>
                    <span className="font-semibold">{feedbackReady.overall_band}</span>
                  </div>
                  {(
                    [
                      ["fluency_coherence", "Fluency & Coherence"],
                      ["lexical_resource", "Lexical Resource"],
                      ["grammatical_range_accuracy", "Grammar Range & Accuracy"],
                      ["pronunciation", "Pronunciation"],
                    ] as const
                  ).map(([key, label]) => {
                    const c = feedbackReady[key];
                    if (!c || typeof c !== "object") return null;
                    return (
                      <div key={key}>
                        <div className="flex items-center justify-between">
                          <p className="font-semibold">{label}</p>
                          <span>{c.score}</span>
                        </div>
                        <p className="text-[#6B6B66]">{c.reasoning}</p>
                      </div>
                    );
                  })}
                  {feedbackReady.summary_feedback && (
                    <p className="border-t border-[#F0F0EA] pt-1">{feedbackReady.summary_feedback}</p>
                  )}
                  {feedbackReady.top_improvement_areas && feedbackReady.top_improvement_areas.length > 0 && (
                    <div>
                      <p className="font-semibold">Areas to improve</p>
                      <ul className="list-inside list-disc space-y-0.5">
                        {feedbackReady.top_improvement_areas.map((a, i) => (
                          <li key={i}>{a}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ) : (
                /* Roleplay feedback */
                <div className="space-y-2 text-xs leading-relaxed text-[#1A1A18]">
                  <div className="flex items-center justify-between border-b border-[#F0F0EA] pb-1">
                    <p className="font-semibold">Overall score</p>
                    <span className="font-semibold">
                      {feedbackReady.overall_score ?? "-"}
                      {typeof feedbackReady.overall_score === "number" ? "/10" : ""}
                    </span>
                  </div>
                  {feedbackReady.overall_comment && <p>{feedbackReady.overall_comment}</p>}
                  {feedbackReady.strengths && feedbackReady.strengths.length > 0 && (
                    <div>
                      <p className="font-semibold">Strengths</p>
                      <ul className="list-inside list-disc space-y-0.5">
                        {feedbackReady.strengths.map((s, i) => (
                          <li key={i}>{s}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {feedbackReady.grammar_issues && feedbackReady.grammar_issues.length > 0 && (
                    <div>
                      <p className="font-semibold">Things to improve</p>
                      <ul className="list-inside list-disc space-y-0.5">
                        {feedbackReady.grammar_issues.map((g, i) => (
                          <li key={i}>
                            {g.quote} → {g.correction}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {feedbackReady.vocabulary && <p>{feedbackReady.vocabulary}</p>}
                  {feedbackReady.fluency && <p>{feedbackReady.fluency}</p>}
                  {feedbackReady.encouragement && (
                    <p className="font-medium text-[#1A7A5E]">
                      {feedbackReady.encouragement}
                    </p>
                  )}
                </div>
              )
            ) : roleplayEnded && feedbackText ? (
              <p className="text-xs leading-relaxed text-[#1A1A18]">{feedbackText}</p>
            ) : adviceText ? (
              <p className="text-xs leading-relaxed text-[#1A1A18]">{adviceText}</p>
            ) : (
              <p className="text-center text-xs text-[#6B6B66]">
                Conversation transcript will appear here
              </p>
            )}
          </div>
          {adviceText && !isRoleplay && !isIelts && (
            <button
              onClick={translateAndPlaySinhala}
              className="w-full cursor-pointer rounded-lg bg-[#1A1A18] px-4 py-2 text-xs font-medium text-white transition-colors hover:bg-[#33332E]"
            >
              Get response in Sinhala
            </button>
          )}
        </div>
      </div>

      <div className="flex flex-col items-center gap-3 border-t border-[#E2E2DC] bg-white px-4 py-6">
        {isRoleplay && !roleplayEnded && (
          <button
            onClick={endRoleplay}
            className="cursor-pointer rounded-full border border-[#1A7A5E] px-4 py-1.5 text-xs font-medium text-[#1A7A5E] transition-colors hover:bg-[#1A7A5E] hover:text-white"
          >
            End roleplay and get feedback
          </button>
        )}
        <MicButton
          isRecording={isRecording}
          disabled={micDisabled}
          label={roleplayEnded ? (isIelts ? "Start test again" : "Start roleplay again") : undefined}
          onPressStart={roleplayEnded ? restartRoleplay : startRecording}
          onPressEnd={roleplayEnded ? undefined : stopRecording}
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
