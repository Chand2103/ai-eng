"use client";

import Link from "next/link";
import { MessageSquare, Theater, GraduationCap, ArrowRight } from "lucide-react";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import PageWrapper from "@/components/layout/PageWrapper";
import UpgradeBanner from "@/components/ui/UpgradeBanner";
import { useAuth } from "@/context/AuthContext";

const MODES = [
  {
    icon: MessageSquare,
    title: "Free Talk",
    description: "Chat about anything — travel, work, hobbies. No script, just conversation.",
    href: "/practice/free-talk",
    tags: ["Beginner friendly", "Open topic"],
  },
  {
    icon: Theater,
    title: "Roleplay",
    description: "Practice real scenarios: job interviews, shopping, restaurants, and more.",
    href: "/practice/roleplay",
    tags: ["Scenario-based", "Structured"],
  },
  {
    icon: GraduationCap,
    title: "IELTS Prep",
    description: "Speaking part 1, 2 & 3 practice with AI examiner feedback.",
    href: "/practice/ielts",
    tags: ["Exam focused", "Band scoring"],
  },
];

export default function PracticePage() {
  const { user, subscriptionActive } = useAuth();

  const resolveHref = (href: string) => {
    if (!user) return `/login?redirect=${encodeURIComponent(href)}`;
    return href;
  };

  return (
    <PageWrapper>
      {user && !subscriptionActive && <UpgradeBanner className="mb-6" />}
      <h1 className="text-3xl font-bold tracking-tight text-[#1A1A18] sm:text-4xl">Practice</h1>
      <p className="mt-2 text-[#6B6B66]">Choose a mode to start improving your English.</p>

      <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {MODES.map((mode) => {
          const Icon = mode.icon;
          return (
            <Link key={mode.title} href={resolveHref(mode.href)}>
              <Card hover className="group flex h-full flex-col">
                <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-[#E1F5EE]">
                  <Icon className="h-7 w-7 text-[#1A7A5E]" />
                </div>
                <h3 className="text-xl font-semibold text-[#1A1A18]">{mode.title}</h3>
                <p className="mt-2 flex-1 text-sm text-[#6B6B66]">{mode.description}</p>
                <div className="mt-4 flex flex-wrap gap-2">
                  {mode.tags.map((tag) => (
                    <Badge key={tag} className="bg-[#E1F5EE] text-[#1A7A5E] border-[#1A7A5E]/20">
                      {tag}
                    </Badge>
                  ))}
                </div>
                <div className="mt-4 flex items-center gap-1 text-sm font-medium text-[#1A7A5E]">
                  Get started <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
                </div>
              </Card>
            </Link>
          );
        })}
      </div>
    </PageWrapper>
  );
}
