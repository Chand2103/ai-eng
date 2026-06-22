"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CheckCircle, Loader2 } from "lucide-react";
import Button from "@/components/ui/Button";
import { useAuth } from "@/context/AuthContext";

export default function SuccessPage() {
  const { user, subscriptionActive } = useAuth();
  const [polling, setPolling] = useState(true);

  useEffect(() => {
    if (!user) return;

    let attempts = 0;
    const maxAttempts = 5;
    const interval = setInterval(() => {
      attempts++;
      // subscriptionActive is updated via Firestore onSnapshot in AuthContext
      if (subscriptionActive) {
        setPolling(false);
        clearInterval(interval);
        return;
      }
      if (attempts >= maxAttempts) {
        setPolling(false);
        clearInterval(interval);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [user, subscriptionActive]);

  return (
    <div className="flex min-h-[calc(100vh-4rem)] flex-col items-center justify-center px-4 text-center">
      {polling ? (
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-12 w-12 animate-spin text-[#1A7A5E]" />
          <h1 className="text-2xl font-bold text-[#1A1A18]">Confirming payment...</h1>
          <p className="text-sm text-[#6B6B66]">Please wait while we verify your payment.</p>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[#E1F5EE]">
            <CheckCircle className="h-10 w-10 text-[#1A7A5E]" />
          </div>
          <h1 className="text-2xl font-bold text-[#1A1A18]">Payment successful!</h1>
          <p className="max-w-sm text-sm text-[#6B6B66]">
            Your SpeakUp Pro subscription is now active. You&apos;ll receive a confirmation email shortly.
          </p>
          <Link href="/practice">
            <Button variant="primary" className="mt-4 px-8 py-4 text-base">
              Start practising
            </Button>
          </Link>
        </div>
      )}
    </div>
  );
}
