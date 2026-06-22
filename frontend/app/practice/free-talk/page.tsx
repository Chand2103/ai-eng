"use client";

import { useRouter } from "next/navigation";

export default function FreeTalkRedirect() {
  const router = useRouter();
  if (typeof window !== "undefined") {
    router.replace("/conversation?mode=free-talk");
  }
  return null;
}
