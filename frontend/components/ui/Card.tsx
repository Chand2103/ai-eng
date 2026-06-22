import type { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  onClick?: () => void;
}

export default function Card({ children, className = "", hover = false, onClick }: CardProps) {
  const Tag = onClick ? "button" : "div";
  return (
    <Tag
      onClick={onClick}
      className={`rounded-xl border border-[#E2E2DC] bg-white p-6 transition-all duration-150 ease-in-out ${
        hover ? "hover:border-[#1A7A5E]/30 hover:shadow-sm cursor-pointer" : ""
      } ${onClick ? "cursor-pointer text-left w-full" : ""} ${className}`}
    >
      {children}
    </Tag>
  );
}
