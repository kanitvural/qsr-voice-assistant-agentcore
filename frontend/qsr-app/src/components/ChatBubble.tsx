"use client";

import { motion } from "framer-motion";
import { Mic } from "lucide-react";

interface ChatBubbleProps {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  isAudio?: boolean;
}

export function ChatBubble({ role, content, timestamp, isAudio }: ChatBubbleProps) {
  const isUser = role === "user";

  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.3, type: "spring", bounce: 0.4 }}
      className={`flex w-full ${isUser ? "justify-end" : "justify-start"}`}
    >
      <div
        className={`
          relative max-w-[85%] px-5 py-4 shadow-xl backdrop-blur-md
          ${isUser 
            ? "rounded-2xl rounded-tr-sm bg-qsr-red text-white" 
            : "glass-panel rounded-2xl rounded-tl-sm text-qsr-dark"}
        `}
      >
        <p className="whitespace-pre-wrap text-[15px] leading-relaxed">
          {content}
        </p>
        
        <div 
          className={`
            mt-2 flex items-center gap-1.5 text-[11px] font-medium opacity-70
            ${isUser ? "justify-end text-white/80" : "justify-start text-qsr-dark/60"}
          `}
        >
          <span>
            {timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </span>
          {isAudio && <Mic size={12} />}
        </div>
      </div>
    </motion.div>
  );
}
