"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Check, Sparkles, Lock } from "lucide-react";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import PageWrapper from "@/components/layout/PageWrapper";
import { getAuthInstance } from "@/lib/firebase";
import withAuth from "@/components/auth/withAuth";

const FEATURES = [
  "Unlimited conversation sessions",
  "All roleplay scenarios",
  "IELTS exam practice",
  "Priority AI responses",
  "Conversation history",
];

function SubscriptionPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handlePayment = async () => {
    setLoading(true);
    setError("");

    try {
      const idToken = await getAuthInstance().currentUser!.getIdToken();
      const res = await fetch("/api/payment/create-session", {
        method: "POST",
        headers: { Authorization: `Bearer ${idToken}` },
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || "Failed to create session");
      }
      const { signature, dataString } = await res.json();

      const dp = new (await import("directpay-ipg-js")).Init({
        signature,
        dataString,
        stage: process.env.NEXT_PUBLIC_DIRECTPAY_STAGE || "DEV",
        container: "directpay_container",
      });

      await dp.doInAppCheckout();
      router.push("/subscription/success");
    } catch (err: unknown) {
      console.error(err);
      const msg = err instanceof Error ? err.message : "Payment failed. Please try again.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageWrapper>
      <div id="directpay_container" className="hidden" />
      <div className="grid gap-8 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <h1 className="text-3xl font-bold tracking-tight text-[#1A1A18] sm:text-4xl">Upgrade to Pro</h1>
          <p className="mt-2 text-[#6B6B66]">Unlock premium features and accelerate your English journey.</p>

          <Card className="relative mt-8 border-[#1A7A5E]/30">
            <Badge className="absolute -top-2.5 right-4 bg-[#1A7A5E] text-white border-[#1A7A5E]">
              Most popular
            </Badge>
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-[#1A7A5E]" />
              <h2 className="text-xl font-bold text-[#1A1A18]">SpeakUp Pro</h2>
            </div>
            <div className="mt-4 flex items-baseline gap-1">
              <span className="text-4xl font-bold text-[#1A1A18]">$9.99</span>
              <span className="text-sm text-[#6B6B66]">/ month</span>
            </div>
            <ul className="mt-6 flex flex-col gap-3">
              {FEATURES.map((f) => (
                <li key={f} className="flex items-center gap-3 text-sm text-[#1A1A18]">
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[#E1F5EE]">
                    <Check className="h-3 w-3 text-[#1A7A5E]" />
                  </span>
                  {f}
                </li>
              ))}
            </ul>
          </Card>
        </div>

        <div className="lg:col-span-2">
          <div className="sticky top-24">
            <Card>
              <h3 className="text-lg font-semibold text-[#1A1A18]">Order Summary</h3>
              <div className="mt-4 space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-[#6B6B66]">SpeakUp Pro</span>
                  <span className="font-medium text-[#1A1A18]">$9.99/mo</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#6B6B66]">Subtotal</span>
                  <span className="font-medium text-[#1A1A18]">$9.99</span>
                </div>
                <div className="border-t border-[#E2E2DC] pt-3">
                  <div className="flex justify-between text-base font-semibold">
                    <span>Total</span>
                    <span>$9.99</span>
                  </div>
                </div>
              </div>

              {error && (
                <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
                  {error}
                </div>
              )}

              <Button
                variant="primary"
                className="mt-6 w-full"
                loading={loading}
                disabled={loading}
                onClick={handlePayment}
              >
                {loading ? "Processing..." : "Proceed to payment"}
              </Button>
              <p className="mt-3 flex items-center justify-center gap-1.5 text-xs text-[#6B6B66]">
                <Lock className="h-3 w-3" />
                Secure checkout via DirectPay
              </p>
              <p className="mt-2 text-center text-xs text-[#6B6B66]">
                Cancel anytime. No hidden fees.
              </p>
            </Card>
          </div>
        </div>
      </div>
    </PageWrapper>
  );
}

export default withAuth(SubscriptionPage);
