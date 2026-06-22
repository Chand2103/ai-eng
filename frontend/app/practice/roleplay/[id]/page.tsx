"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";
import { ROLEPLAY_TOPICS } from "@/lib/constants";

export default function RoleplaySessionPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const topic = ROLEPLAY_TOPICS.find((t) => t.id === id);

  useEffect(() => {
    if (topic) {
      router.replace(`/conversation?mode=roleplay&topic=${encodeURIComponent(topic.title)}&topicId=${id}`);
    }
  }, [topic, router, id]);

  if (!topic) {
    return (
      <div className="flex min-h-[calc(100vh-4rem)] items-center justify-center">
        <p className="text-[#6B6B66]">Scenario not found.</p>
      </div>
    );
  }

  return null;
}
