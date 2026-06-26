import { create } from "zustand";

export interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  isAudio?: boolean;
  isComplete?: boolean;
}

interface ChatState {
  messages: Message[];
  isConnected: boolean;
  isRecording: boolean;
  error: string | null;
  currentTool: string | null;

  // Actions
  addMessage: (role: "user" | "assistant", content: string, isAudio: boolean, isComplete?: boolean) => void;
  markLastAssistantMessageComplete: () => void;
  setConnected: (status: boolean) => void;
  setRecording: (status: boolean) => void;
  setError: (error: string | null) => void;
  setCurrentTool: (tool: string | null) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isConnected: false,
  isRecording: false,
  error: null,
  currentTool: null,

  addMessage: (role, content, isAudio, isComplete = true) =>
    set((state) => {
      // Append to the last assistant message if it's not complete yet
      if (role === "assistant" && state.messages.length > 0) {
        const lastMsg = state.messages[state.messages.length - 1];
        if (lastMsg.role === "assistant" && !lastMsg.isComplete) {
          const updated = [...state.messages];
          updated[updated.length - 1] = {
            ...lastMsg,
            content: lastMsg.content + " " + content,
            isComplete,
          };
          return { messages: updated };
        }
      }
      return {
        messages: [
          ...state.messages,
          { role, content, timestamp: new Date(), isAudio, isComplete },
        ],
      };
    }),

  markLastAssistantMessageComplete: () =>
    set((state) => {
      if (state.messages.length === 0) return state;
      const lastMsg = state.messages[state.messages.length - 1];
      if (lastMsg.role === "assistant" && !lastMsg.isComplete) {
        const updated = [...state.messages];
        updated[updated.length - 1] = { ...lastMsg, isComplete: true };
        return { messages: updated };
      }
      return state;
    }),

  setConnected: (status) => set({ isConnected: status }),
  setRecording: (status) => set({ isRecording: status }),
  setError: (error) => set({ error }),
  setCurrentTool: (currentTool) => set({ currentTool }),
  clearMessages: () => set({ messages: [] }),
}));
