"use client";

interface AvatarProps {
  isSpeaking: boolean;
}

export default function Avatar({ isSpeaking }: AvatarProps) {
  return (
    <div className="relative flex items-center justify-center">
      <div
        className={`h-24 w-24 rounded-full bg-[#1A7A5E]/10 flex items-center justify-center transition-all duration-300 ${
          isSpeaking ? "scale-110" : "scale-100"
        }`}
      >
        <div className="h-16 w-16 rounded-full bg-[#1A7A5E]/20 flex items-center justify-center">
          <div className="h-10 w-10 rounded-full bg-[#1A7A5E]" />
        </div>
      </div>
      {isSpeaking && (
        <>
          <div className="absolute inset-0 rounded-full border-2 border-[#1A7A5E]/30 animate-ping" />
          <div className="absolute inset-0 rounded-full border border-[#1A7A5E]/20 animate-pulse" style={{ animationDelay: "0.3s" }} />
        </>
      )}
    </div>
  );
}
