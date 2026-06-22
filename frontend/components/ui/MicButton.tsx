"use client";

import { Mic } from "lucide-react";
import AudioWave from "./AudioWave";

interface MicButtonProps {
  isRecording: boolean;
  onMouseDown?: () => void;
  onMouseUp?: () => void;
  onTouchStart?: () => void;
  onTouchEnd?: () => void;
}

export default function MicButton({
  isRecording,
  onMouseDown,
  onMouseUp,
  onTouchStart,
  onTouchEnd,
}: MicButtonProps) {
  return (
    <div className="flex flex-col items-center gap-3">
      <button
        onMouseDown={onMouseDown}
        onMouseUp={onMouseUp}
        onTouchStart={onTouchStart}
        onTouchEnd={onTouchEnd}
        className={`relative flex h-[72px] w-[72px] items-center justify-center rounded-full transition-all duration-150 ease-in-out active:scale-95 cursor-pointer ${
          isRecording
            ? "bg-red-500 shadow-lg shadow-red-200"
            : "bg-[#1A7A5E] shadow-sm hover:shadow-md hover:bg-[#156b52]"
        }`}
      >
        {isRecording ? (
          <div className="flex items-center gap-0.5">
            <AudioWave />
          </div>
        ) : (
          <Mic className="h-7 w-7 text-white" />
        )}
      </button>
      <span className="text-xs font-medium text-[#6B6B66]">
        {isRecording ? "Release to send" : "Tap to speak"}
      </span>
    </div>
  );
}
