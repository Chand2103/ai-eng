"use client";

import { forwardRef, type InputHTMLAttributes, useState } from "react";
import { Eye, EyeOff } from "lucide-react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, type, className = "", ...props }, ref) => {
    const [showPassword, setShowPassword] = useState(false);
    const isPassword = type === "password";
    const inputType = isPassword && showPassword ? "text" : type;

    return (
      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-[#1A1A18]">{label}</label>
        <div className="relative">
          <input
            ref={ref}
            type={inputType}
            className={`w-full rounded-xl border px-4 py-3 text-sm text-[#1A1A18] placeholder:text-[#6B6B66] outline-none transition-all duration-150 bg-white focus:border-[#1A7A5E] focus:ring-2 focus:ring-[#1A7A5E]/20 ${
              error ? "border-red-300 focus:border-red-400 focus:ring-red-200" : "border-[#E2E2DC]"
            } ${isPassword ? "pr-12" : ""} ${className}`}
            {...props}
          />
          {isPassword && (
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-[#6B6B66] hover:text-[#1A1A18] cursor-pointer"
              tabIndex={-1}
            >
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          )}
        </div>
        {error && <p className="text-xs text-red-500">{error}</p>}
      </div>
    );
  }
);

Input.displayName = "Input";
export default Input;
