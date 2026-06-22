"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { FirebaseError } from "firebase/app";
import { APP_NAME } from "@/lib/constants";
import { useAuth } from "@/context/AuthContext";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import { isValidEmail } from "@/lib/utils";
import { LogIn } from "lucide-react";

const FIREBASE_ERRORS: Record<string, string> = {
  "auth/wrong-password": "Incorrect password",
  "auth/user-not-found": "No account found with this email",
  "auth/invalid-credential": "Invalid email or password",
  "auth/invalid-email": "Invalid email address",
  "auth/too-many-requests": "Too many attempts. Try again later.",
};

function getFirebaseMessage(code: string): string {
  return FIREBASE_ERRORS[code] || "Something went wrong. Please try again.";
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, loginWithGoogle } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const newErrors: Record<string, string> = {};
    if (!email.trim()) newErrors.email = "Email is required";
    else if (!isValidEmail(email)) newErrors.email = "Invalid email address";
    if (!password) newErrors.password = "Password is required";
    setErrors(newErrors);
    if (Object.keys(newErrors).length > 0) return;

    setLoading(true);
    try {
      await login(email, password);
      const redirect = searchParams.get("redirect") || "/practice";
      router.push(redirect);
    } catch (err) {
      if (err instanceof FirebaseError) {
        setErrors({ form: getFirebaseMessage(err.code) });
      } else {
        setErrors({ form: "Login failed. Please try again." });
      }
    } finally {
      setLoading(false);
    }
  };

  const handleGoogle = async () => {
    try {
      await loginWithGoogle();
      const redirect = searchParams.get("redirect") || "/practice";
      router.push(redirect);
    } catch (err) {
      if (err instanceof FirebaseError && err.code === "auth/popup-closed-by-user") {
        return;
      }
      if (err instanceof FirebaseError) {
        setErrors({ form: getFirebaseMessage(err.code) });
      } else {
        setErrors({ form: "Google sign-in failed." });
      }
    }
  };

  return (
    <div className="flex min-h-[calc(100vh-4rem)] items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm">
        <h1 className="mb-2 text-center text-2xl font-bold text-[#1A1A18]">{APP_NAME}</h1>
        <p className="mb-8 text-center text-sm text-[#6B6B66]">Sign in to your account</p>

        {errors.form && (
          <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
            {errors.form}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <Input
            label="Email"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            error={errors.email}
          />
          <Input
            label="Password"
            type="password"
            placeholder="Enter your password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            error={errors.password}
          />
          <div className="text-right">
            <button type="button" className="text-xs text-[#6B6B66] hover:text-[#1A7A5E] cursor-pointer">
              Forgot password?
            </button>
          </div>
          <Button type="submit" variant="primary" loading={loading} className="w-full">
            Sign in
          </Button>
        </form>

        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-[#E2E2DC]" />
          </div>
          <div className="relative flex justify-center text-xs text-[#6B6B66]">
            <span className="bg-[#F8F7F4] px-2">or</span>
          </div>
        </div>

        <Button variant="outline" className="w-full" icon={<LogIn className="h-4 w-4" />} onClick={handleGoogle}>
          Sign in with Google
        </Button>

        <p className="mt-6 text-center text-sm text-[#6B6B66]">
          Don&apos;t have an account?{" "}
          <Link href="/register" className="font-medium text-[#1A7A5E] hover:underline">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="flex min-h-[calc(100vh-4rem)] items-center justify-center">Loading...</div>}>
      <LoginForm />
    </Suspense>
  );
}
