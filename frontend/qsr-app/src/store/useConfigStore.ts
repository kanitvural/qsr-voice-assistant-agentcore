import { create } from "zustand";

export interface AppConfig {
  region: string;
  userPoolId: string;
  clientId: string;
  identityPoolId: string;
  websocketUrl: string;
  runtimeArn: string;
}

interface ConfigState {
  config: AppConfig | null;
  isLoading: boolean;
  error: string | null;
  loadConfig: () => Promise<void>;
}

export const useConfigStore = create<ConfigState>((set, get) => ({
  config: null,
  isLoading: true,
  error: null,
  loadConfig: async () => {
    // If already loaded, do nothing
    if (get().config) return;

    try {
      set({ isLoading: true, error: null });
      const response = await fetch("/config.json");
      
      if (!response.ok) {
        throw new Error(`Failed to load config: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      const config: AppConfig = {
        region: data.NEXT_PUBLIC_REGION || "us-east-1",
        userPoolId: data.NEXT_PUBLIC_USER_POOL_ID || "",
        clientId: data.NEXT_PUBLIC_CLIENT_ID || "",
        identityPoolId: data.NEXT_PUBLIC_IDENTITY_POOL_ID || "",
        websocketUrl: data.NEXT_PUBLIC_WEBSOCKET_URL || "",
        runtimeArn: data.NEXT_PUBLIC_RUNTIME_ARN || "",
      };

      set({ config, isLoading: false });
    } catch (error: any) {
      console.error("Error loading config.json:", error);
      set({ error: error.message, isLoading: false });
    }
  },
}));
