"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { APP_NAME } from "@/lib/constants";
import Button from "@/components/ui/Button";
import { Menu, X, ChevronDown, LogOut } from "lucide-react";
import { useState, useRef, useEffect } from "react";

export default function Navbar() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const handleLogout = async () => {
    await logout();
    setDropdownOpen(false);
    setMobileOpen(false);
    router.push("/");
  };

  const initial = user?.displayName?.charAt(0)?.toUpperCase() || user?.email?.charAt(0)?.toUpperCase() || "?";

  return (
    <nav className="sticky top-0 z-40 border-b border-[#E2E2DC] bg-white/95 backdrop-blur-sm">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
        <Link href="/" className="text-xl font-bold tracking-tight text-[#1A1A18]">
          {APP_NAME}
        </Link>

        {/* Desktop nav */}
        <div className="hidden items-center gap-4 sm:flex">
          <Link
            href="/practice"
            className="text-sm font-medium text-[#6B6B66] hover:text-[#1A1A18] transition-colors duration-150"
          >
            Practice
          </Link>
          {user ? (
            <>
              <Link href="/subscription">
                <Button variant="primary" className="px-4 py-2 text-xs">
                  Upgrade
                </Button>
              </Link>
              <div className="relative" ref={dropdownRef}>
                <button
                  onClick={() => setDropdownOpen(!dropdownOpen)}
                  className="flex items-center gap-2 cursor-pointer"
                >
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#E1F5EE] text-sm font-semibold text-[#1A7A5E]">
                    {initial}
                  </div>
                  <ChevronDown className={`h-3.5 w-3.5 text-[#6B6B66] transition-transform duration-150 ${dropdownOpen ? "rotate-180" : ""}`} />
                </button>
                {dropdownOpen && (
                  <div className="absolute right-0 top-full mt-2 w-48 rounded-xl border border-[#E2E2DC] bg-white p-2 shadow-sm">
                    <div className="border-b border-[#E2E2DC] px-3 py-2">
                      <p className="text-sm font-medium text-[#1A1A18] truncate">{user.displayName || "User"}</p>
                      <p className="text-xs text-[#6B6B66] truncate">{user.email}</p>
                    </div>
                    <button
                      onClick={handleLogout}
                      className="mt-1 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors duration-150 cursor-pointer"
                    >
                      <LogOut className="h-4 w-4" />
                      Sign out
                    </button>
                  </div>
                )}
              </div>
            </>
          ) : (
            <>
              <Link
                href="/login"
                className="text-sm font-medium text-[#6B6B66] hover:text-[#1A1A18] transition-colors duration-150"
              >
                Sign in
              </Link>
              <Link href="/register">
                <Button variant="primary" className="px-4 py-2 text-xs">
                  Get started
                </Button>
              </Link>
            </>
          )}
        </div>

        {/* Mobile hamburger */}
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="sm:hidden text-[#1A1A18] cursor-pointer"
        >
          {mobileOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="border-t border-[#E2E2DC] bg-white px-4 py-4 sm:hidden">
          <div className="flex flex-col gap-3">
            <Link
              href="/practice"
              onClick={() => setMobileOpen(false)}
              className="text-sm font-medium text-[#6B6B66] hover:text-[#1A1A18]"
            >
              Practice
            </Link>
            {user ? (
              <>
                <div className="flex items-center gap-2 border-b border-[#E2E2DC] pb-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#E1F5EE] text-sm font-semibold text-[#1A7A5E]">
                    {initial}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-[#1A1A18]">{user.displayName || "User"}</p>
                    <p className="text-xs text-[#6B6B66]">{user.email}</p>
                  </div>
                </div>
                <Link
                  href="/subscription"
                  onClick={() => setMobileOpen(false)}
                  className="text-sm font-medium text-[#6B6B66] hover:text-[#1A1A18]"
                >
                  Subscription
                </Link>
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-2 text-sm font-medium text-red-500 text-left cursor-pointer"
                >
                  <LogOut className="h-4 w-4" />
                  Sign out
                </button>
              </>
            ) : (
              <>
                <Link
                  href="/login"
                  onClick={() => setMobileOpen(false)}
                  className="text-sm font-medium text-[#6B6B66] hover:text-[#1A1A18]"
                >
                  Sign in
                </Link>
                <Link
                  href="/register"
                  onClick={() => setMobileOpen(false)}
                  className="text-sm font-medium text-[#1A7A5E]"
                >
                  Get started
                </Link>
              </>
            )}
          </div>
        </div>
      )}
    </nav>
  );
}
