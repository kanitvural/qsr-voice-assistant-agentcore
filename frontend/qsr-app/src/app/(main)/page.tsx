"use client";

import { useState, useEffect, useRef } from "react";
import { VoiceButton } from "@/components/VoiceButton";
import { ChatBubble } from "@/components/ChatBubble";
import { ToolExecutionBanner } from "@/components/ToolExecutionBanner";
import { useChatStore } from "@/store/useChatStore";
import { useAgentCore } from "@/hooks/useAgentCore";
import { motion, AnimatePresence } from "framer-motion";
import { Send, X } from "lucide-react";

export default function ChatInterface() {
  const { messages, isRecording, error, currentTool } = useChatStore();
  const { startRecording, stopRecording, sendTextMessage } = useAgentCore();
  
  const [inputText, setInputText] = useState("");
  const [showTextInput, setShowTextInput] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSendText = () => {
    if (!inputText.trim()) return;
    sendTextMessage(inputText);
    setInputText("");
    setShowTextInput(false);
  };

  return (
    <>
      <ToolExecutionBanner toolName={currentTool} />
      
      {error && (
        <div className="bg-red-500 px-6 py-3 text-sm font-medium text-white shadow-sm">
          ⚠️ {error}
        </div>
      )}

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-8">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
          {messages.length === 0 && (
            <div className="mt-20 flex flex-col items-center text-center">
              <div className="mb-6 flex h-24 w-24 items-center justify-center rounded-full bg-white shadow-xl">
                <span className="text-4xl">🎙️</span>
              </div>
              <h1 className="text-2xl font-bold text-qsr-dark">Welcome to Voice Ordering</h1>
              <p className="mt-2 text-gray-500">Tap the microphone to start your order</p>
            </div>
          )}

          {messages.map((msg, idx) => (
            <ChatBubble key={idx} {...msg} />
          ))}
          <div ref={messagesEndRef} className="h-24" /> {/* Padding for bottom floaters */}
        </div>
      </div>

      {/* Floating Controls */}
      <div className="absolute bottom-6 left-0 right-0 flex justify-center px-6">
        <div className="relative flex w-full max-w-7xl items-center justify-end">
          
          <AnimatePresence>
            {showTextInput && (
              <motion.div
                initial={{ opacity: 0, scale: 0.9, x: 20 }}
                animate={{ opacity: 1, scale: 1, x: 0 }}
                exit={{ opacity: 0, scale: 0.9, x: 20 }}
                className="z-20 flex w-full max-w-md items-center gap-2 rounded-full bg-white p-2 shadow-2xl mr-4"
              >
                <input
                  type="text"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyPress={(e) => e.key === "Enter" && handleSendText()}
                  placeholder="Type your message..."
                  className="flex-1 bg-transparent px-4 py-2 text-qsr-dark outline-none placeholder:text-gray-400"
                  autoFocus
                />
                <button
                  onClick={handleSendText}
                  disabled={!inputText.trim()}
                  className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-qsr-red text-white transition-transform active:scale-95 disabled:opacity-50"
                >
                  <Send size={18} />
                </button>
                <button
                  onClick={() => setShowTextInput(false)}
                  className="ml-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gray-100 text-gray-500 transition-colors hover:bg-gray-200"
                >
                  <X size={18} />
                </button>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Voice Action */}
          <div className="z-10 flex items-center gap-4">
            {!showTextInput && (
              <button
                onClick={() => setShowTextInput(true)}
                className="flex h-12 w-12 items-center justify-center rounded-full bg-white text-gray-600 shadow-xl transition-transform hover:scale-105 active:scale-95"
              >
                ⌨️
              </button>
            )}
            
            <VoiceButton
              isRecording={isRecording}
              onClick={isRecording ? stopRecording : startRecording}
            />
          </div>
        </div>
      </div>
    </>
  );
}
