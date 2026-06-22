"use client";

import Link from "next/link";
import { MessageSquare, Theater, GraduationCap, ArrowRight, ChevronRight } from "lucide-react";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import { useAuth } from "@/context/AuthContext";
import { APP_TAGLINE } from "@/lib/constants";

const FEATURES = [
  {
    icon: MessageSquare,
    title: "Free Talk",
    description: "Open conversation on any topic",
    href: "/practice/free-talk",
  },
  {
    icon: Theater,
    title: "Roleplay",
    description: "Practice real-life scenarios",
    href: "/practice/roleplay",
  },
  {
    icon: GraduationCap,
    title: "IELTS Prep",
    description: "Targeted exam practice",
    href: "/practice/ielts",
  },
];

export default function Home() {
  const { user } = useAuth();

  const resolveHref = (href: string) => {
    if (!user) return `/login?redirect=${encodeURIComponent(href)}`;
    return href;
  };

  return (
    <div className="flex flex-col">
      {/* Hero */}
      <section className="relative flex flex-col items-center justify-center overflow-hidden px-4 pt-24 pb-16 text-center sm:pt-32 sm:pb-24">
        <div className="pointer-events-none absolute inset-0 -top-40 opacity-30">
          <div className="absolute left-1/2 top-1/2 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#1A7A5E] opacity-10 blur-3xl animate-hero-pulse" />
        </div>
        <h1 className="relative max-w-3xl text-4xl font-bold tracking-tight text-[#1A1A18] sm:text-5xl md:text-6xl">
          {APP_TAGLINE}
        </h1>
        <p className="relative mt-4 max-w-xl text-lg text-[#6B6B66] sm:text-xl">
          AI-powered voice practice — anytime, anywhere.
        </p>
        <div className="relative mt-8 flex flex-col items-center gap-3 sm:flex-row">
          <Link href={resolveHref("/practice")}>
            <Button variant="primary" className="px-8 py-4 text-base">
              Start Practising
            </Button>
          </Link>
          <Link href="#features">
            <Button variant="ghost" className="px-8 py-4 text-base">
              See how it works
              <ChevronRight className="h-4 w-4" />
            </Button>
          </Link>
        </div>
      </section>

      {/* Feature cards */}
      <section id="features" className="mx-auto w-full max-w-6xl px-4 pb-20 sm:px-6">
        <div className="grid gap-6 sm:grid-cols-3">
          {FEATURES.map((feature) => {
            const Icon = feature.icon;
            return (
              <Link key={feature.title} href={resolveHref(feature.href)}>
                <Card hover className="group h-full">
                  <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-[#E1F5EE]">
                    <Icon className="h-6 w-6 text-[#1A7A5E]" />
                  </div>
                  <h3 className="text-lg font-semibold text-[#1A1A18]">{feature.title}</h3>
                  <p className="mt-1 text-sm text-[#6B6B66]">{feature.description}</p>
                  <div className="mt-4 flex items-center gap-1 text-sm font-medium text-[#1A7A5E]">
                    Learn more <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
                  </div>
                </Card>
              </Link>
            );
          })}
        </div>
      </section>

      {/* Social proof */}
      <section className="border-t border-[#E2E2DC] bg-white py-12">
        <p className="text-center text-sm font-medium text-[#6B6B66]">
          Trusted by <span className="text-[#1A1A18]">10,000+</span> learners worldwide
        </p>
      </section>
    </div>
  );
}
