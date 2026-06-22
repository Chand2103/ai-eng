"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Loader2, ArrowLeft } from "lucide-react";

export default function CheckoutPage() {
  const [showRedirect, setShowRedirect] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setShowRedirect(true);
      const stripeUrl = process.env.NEXT_PUBLIC_STRIPE_URL || "#";
      if (stripeUrl !== "#") {
        window.location.href = stripeUrl;
      }
    }, 1500);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="flex min-h-[calc(100vh-4rem)] flex-col items-center justify-center px-4">
      <div className="flex flex-col items-center gap-4 text-center">
        <Loader2 className="h-10 w-10 animate-spin text-[#1A7A5E]" />
        <h1 className="text-2xl font-bold text-[#1A1A18]">Redirecting to secure payment...</h1>
        <p className="text-sm text-[#6B6B66]">
          You&apos;ll be redirected to Stripe to complete your payment.
        </p>

        {showRedirect && (
          <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
            Stripe URL not configured. Set{" "}
            <code className="rounded bg-amber-100 px-1.5 py-0.5 text-xs">
              NEXT_PUBLIC_STRIPE_URL
            </code>{" "}
            in your environment variables.
          </div>
        )}

        <Link
          href="/subscription"
          className="mt-4 flex items-center gap-1.5 text-sm font-medium text-[#6B6B66] hover:text-[#1A1A18] transition-colors duration-150"
        >
          <ArrowLeft className="h-4 w-4" />
          Go back
        </Link>
      </div>
    </div>
  );
}
