"use client";

import { useRouter } from "next/navigation";
import {
  Briefcase,
  Plane,
  Utensils,
  Stethoscope,
  Building,
  Users,
  Phone,
  ShoppingBag,
  type LucideIcon,
} from "lucide-react";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import PageWrapper from "@/components/layout/PageWrapper";
import UpgradeBanner from "@/components/ui/UpgradeBanner";
import { ROLEPLAY_TOPICS, DIFFICULTY_COLORS } from "@/lib/constants";
import { useAuth } from "@/context/AuthContext";

const ICON_MAP: Record<string, LucideIcon> = {
  briefcase: Briefcase,
  plane: Plane,
  utensils: Utensils,
  stethoscope: Stethoscope,
  building: Building,
  users: Users,
  phone: Phone,
  "shopping-bag": ShoppingBag,
};

export default function RoleplayPage() {
  const router = useRouter();
  const { user, subscriptionActive } = useAuth();

  return (
    <PageWrapper>
      {user && !subscriptionActive && <UpgradeBanner className="mb-6" />}
      <h1 className="text-3xl font-bold tracking-tight text-[#1A1A18] sm:text-4xl">Choose a Scenario</h1>
      <p className="mt-2 text-[#6B6B66]">Select a real-world situation to practice</p>

      <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {ROLEPLAY_TOPICS.map((topic) => {
          const Icon = ICON_MAP[topic.icon] || Briefcase;
          return (
            <Card
              key={topic.id}
              hover
              onClick={() => router.push(`/practice/roleplay/${topic.id}`)}
              className="group text-left"
            >
              <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-[#E1F5EE]">
                <Icon className="h-6 w-6 text-[#1A7A5E]" />
              </div>
              <h3 className="text-lg font-semibold text-[#1A1A18]">{topic.title}</h3>
              <p className="mt-1 text-sm text-[#6B6B66]">{topic.description}</p>
              <div className="mt-3">
                <Badge className={DIFFICULTY_COLORS[topic.difficulty] || DIFFICULTY_COLORS.Beginner}>
                  {topic.difficulty}
                </Badge>
              </div>
            </Card>
          );
        })}
      </div>
    </PageWrapper>
  );
}
