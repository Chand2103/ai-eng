"use client";

import { useRouter } from "next/navigation";

export default function IeltsRedirect() {
  const router = useRouter();
  if (typeof window !== "undefined") {
    router.replace("/conversation?mode=ielts");
  }
  return null;
}
