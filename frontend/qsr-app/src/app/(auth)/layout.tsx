"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getStoredSession } from "@/lib/cognito";
import { motion } from "framer-motion";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
    const { session } = getStoredSession();
    if (session) {
      router.replace("/"); // If already logged in, go to main
    }
  }, [router]);

  if (!isClient) return null; // Avoid hydration mismatch

  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-qsr-dark via-[#111] to-black">
      <main className="relative z-10 w-full max-w-md px-6">
        {children}
      </main>
    </div>
  );
}
