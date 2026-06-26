"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getStoredSession, clearSession } from "@/lib/cognito";
import { LogOut } from "lucide-react";

export default function MainLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const { session, credentials } = getStoredSession();
    if (!session || !credentials) {
      router.replace("/login");
    } else {
      setIsAuthenticated(true);
    }
  }, [router]);

  const handleSignOut = () => {
    clearSession();
    router.replace("/login");
  };

  if (!isAuthenticated) return null; // Avoid rendering until auth is confirmed

  return (
    <div className="flex min-h-screen flex-col bg-qsr-light">
      {/* Premium Dark Header */}
      <header className="sticky top-0 z-50 flex shrink-0 items-center justify-between bg-qsr-dark px-6 py-4 text-white shadow-md">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-qsr-red text-xl shadow-lg shadow-qsr-red/20">
            🎙️
          </div>
          <div>
            <h2 className="text-lg font-semibold tracking-tight">QSR Voice AI</h2>
            <p className="text-xs text-white/60">Omnichannel Assistant</p>
          </div>
        </div>
        
        <button
          onClick={handleSignOut}
          className="flex items-center gap-2 rounded-xl border border-white/20 bg-white/10 px-4 py-2 text-sm font-medium transition-colors hover:bg-white/20 active:scale-95"
        >
          <LogOut size={16} />
          <span className="hidden sm:inline">Sign Out</span>
        </button>
      </header>

      {/* Main Content Area */}
      <main className="relative flex flex-1 flex-col overflow-hidden">
        {children}
      </main>
    </div>
  );
}
