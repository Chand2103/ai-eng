import type { ReactNode } from "react";

interface PageWrapperProps {
  children: ReactNode;
  className?: string;
}

export default function PageWrapper({ children, className = "" }: PageWrapperProps) {
  return (
    <div className={`mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 sm:py-12 ${className}`}>
      {children}
    </div>
  );
}
