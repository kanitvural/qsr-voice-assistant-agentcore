"use client";

import { useEffect } from "react";
import { useConfigStore } from "@/store/useConfigStore";
import { Loader2, AlertTriangle } from "lucide-react";

export function ConfigProvider({ children }: { children: React.ReactNode }) {
  const { config, isLoading, error, loadConfig } = useConfigStore();

  useEffect(() => {
    loadConfig();
  }, [loadConfig]);

  if (isLoading) {
    return (
      <div className="flex h-screen w-full flex-col items-center justify-center bg-[#1a1a2e] text-white">
        <Loader2 className="h-8 w-8 animate-spin text-qsr-red" />
        <p className="mt-4 text-sm text-gray-400">Loading configuration...</p>
      </div>
    );
  }

  if (error || !config) {
    return (
      <div className="flex h-screen w-full flex-col items-center justify-center bg-[#1a1a2e] text-white">
        <AlertTriangle className="h-12 w-12 text-yellow-500 mb-4" />
        <h2 className="text-xl font-bold">Configuration Error</h2>
        <p className="mt-2 text-sm text-gray-400 max-w-md text-center">
          {error || "Could not load configuration."}
        </p>
        <p className="mt-4 text-xs text-gray-500">
          Ensure config.json is present in the public folder.
        </p>
      </div>
    );
  }

  return <>{children}</>;
}
