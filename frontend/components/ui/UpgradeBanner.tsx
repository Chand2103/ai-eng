"use client";

import Link from "next/link";
import { Sparkles } from "lucide-react";

interface UpgradeBannerProps {
  className?: string;
}

export default function UpgradeBanner({ className = "" }: UpgradeBannerProps) {
  return (
    <div
      className={`flex items-center justify-between gap-3 rounded-xl border border-[#1A7A5E]/20 bg-[#E1F5EE] px-4 py-3 ${className}`}
    >
      <div className="flex items-center gap-2 text-sm text-[#1A1A18]">
        <Sparkles className="h-4 w-4 text-[#1A7A5E]" />
        <span>
          You&apos;re on the free plan.{" "}
          <Link href="/subscription" className="font-semibold text-[#1A7A5E] hover:underline">
            Upgrade to Pro
          </Link>{" "}
          to unlock all features.
        </span>
      </div>
    </div>
  );
}
