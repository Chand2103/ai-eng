"use client";

import { useRouter, usePathname } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/context/AuthContext";

export default function withAuth<P extends object>(Component: React.ComponentType<P>) {
  return function Authenticated(props: P) {
    const { user, loading } = useAuth();
    const router = useRouter();
    const pathname = usePathname();

    useEffect(() => {
      if (!loading && !user) {
        router.replace(`/login?redirect=${encodeURIComponent(pathname)}`);
      }
    }, [loading, user, router, pathname]);

    if (loading || !user) {
      return (
        <div className="flex min-h-[calc(100vh-4rem)] items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-[#E2E2DC] border-t-[#1A7A5E]" />
        </div>
      );
    }

    return <Component {...props} />;
  };
}
