"use client";

import type { PointerEvent as ReactPointerEvent } from "react";
import { Mic, Loader2 } from "lucide-react";
import AudioWave from "./AudioWave";

interface MicButtonProps {
  isRecording: boolean;
  disabled?: boolean;
  label?: string;
  onPressStart?: () => void;
  onPressEnd?: () => void;
}

export default function MicButton({
  isRecording,
  disabled = false,
  label,
  onPressStart,
  onPressEnd,
}: MicButtonProps) {
  const handlePointerDown = (e: ReactPointerEvent<HTMLButtonElement>) => {
    if (disabled) return;
    e.preventDefault();
    // Capture the pointer so a finger/mouse that slides off the button still
    // delivers its release event here (fixes "mic never releases" bugs).
    e.currentTarget.setPointerCapture(e.pointerId);
    onPressStart?.();
  };

  const handlePointerUp = (e: ReactPointerEvent<HTMLButtonElement>) => {
    if (e.currentTarget.hasPointerCapture(e.pointerId)) {
      e.currentTarget.releasePointerCapture(e.pointerId);
    }
    onPressEnd?.();
  };

  const handlePointerCancel = () => {
    onPressEnd?.();
  };

  return (
    <div className="flex flex-col items-center gap-3">
      <button
        onPointerDown={handlePointerDown}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerCancel}
        disabled={disabled}
        className={`relative flex h-[72px] w-[72px] items-center justify-center rounded-full transition-all duration-150 ease-in-out touch-none ${
          disabled
            ? "cursor-not-allowed bg-[#A8B7B1]"
            : "cursor-pointer active:scale-95"
        } ${
          isRecording
            ? "bg-red-500 shadow-lg shadow-red-200"
            : "bg-[#1A7A5E] shadow-sm hover:shadow-md hover:bg-[#156b52]"
        }`}
      >
        {isRecording ? (
          <div className="flex items-center gap-0.5">
            <AudioWave />
          </div>
        ) : disabled ? (
          <Loader2 className="h-7 w-7 animate-spin text-white" />
        ) : (
          <Mic className="h-7 w-7 text-white" />
        )}
      </button>
      <span className="text-xs font-medium text-[#6B6B66]">
        {isRecording ? "Release to send" : disabled ? "AI is speaking..." : label ?? "Tap to speak"}
      </span>
    </div>
  );
}
