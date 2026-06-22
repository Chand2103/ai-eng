"use client";

import { type ReactNode } from "react";
import { useAuth } from "@/context/AuthContext";

export default function AuthGate({ children }: { children: ReactNode }) {
  const { loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#F8F7F4]">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-[#E2E2DC] border-t-[#1A7A5E]" />
      </div>
    );
  }

  return <>{children}</>;
}
