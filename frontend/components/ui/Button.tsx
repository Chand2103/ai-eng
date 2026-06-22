"use client";

import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import { Loader2 } from "lucide-react";

type Variant = "primary" | "ghost" | "danger" | "outline";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  loading?: boolean;
  icon?: ReactNode;
}

const variantStyles: Record<Variant, string> = {
  primary: "bg-[#1A7A5E] text-white hover:bg-[#156b52] active:bg-#115f48",
  ghost: "bg-transparent text-[#1A1A18] hover:bg-[#E1F5EE] border border-transparent",
  danger: "bg-white text-red-600 border border-red-200 hover:bg-red-50",
  outline: "bg-transparent text-[#1A7A5E] border border-[#1A7A5E] hover:bg-[#E1F5EE]",
};

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "primary", loading, icon, disabled, children, className = "", ...props }, ref) => {
    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={`inline-flex items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold transition-all duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-[#1A7A5E]/30 disabled:opacity-50 disabled:pointer-events-none cursor-pointer ${variantStyles[variant]} ${className}`}
        {...props}
      >
        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : icon}
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";
export default Button;
