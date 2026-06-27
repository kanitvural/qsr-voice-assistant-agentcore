"use client";

import { motion } from "framer-motion";
import { Mic, Square, Loader2 } from "lucide-react";

interface VoiceButtonProps {
  isRecording: boolean;
  isConnecting?: boolean;
  onClick: () => void;
  disabled?: boolean;
}

export function VoiceButton({ isRecording, isConnecting = false, onClick, disabled = false }: VoiceButtonProps) {
  return (
    <div className="relative flex items-center justify-center">
      {/* Pulse Rings when recording - GREEN WAVE */}
      {isRecording && (
        <>
          <motion.div
            className="absolute inset-0 rounded-full bg-green-500 opacity-30"
            initial={{ scale: 0.8, opacity: 0.5 }}
            animate={{ scale: 1.8, opacity: 0 }}
            transition={{ repeat: Infinity, duration: 1.5, ease: "easeOut" }}
          />
          <motion.div
            className="absolute inset-0 rounded-full bg-green-500 opacity-20"
            initial={{ scale: 0.8, opacity: 0.5 }}
            animate={{ scale: 2.2, opacity: 0 }}
            transition={{ repeat: Infinity, duration: 1.5, ease: "easeOut", delay: 0.4 }}
          />
        </>
      )}

      {/* Main Button */}
      <motion.button
        onClick={onClick}
        disabled={disabled || isConnecting}
        whileHover={{ scale: (disabled || isConnecting) ? 1 : 1.05 }}
        whileTap={{ scale: (disabled || isConnecting) ? 1 : 0.95 }}
        className={`
          relative z-10 flex h-16 w-16 items-center justify-center rounded-full shadow-2xl transition-colors
          ${(disabled || isConnecting) ? "cursor-not-allowed bg-gray-300" : isRecording ? "bg-green-600 text-white" : "bg-qsr-red text-white"}
        `}
        style={{
          boxShadow: isRecording 
            ? "0 10px 25px -5px rgba(22, 163, 74, 0.5)" 
            : "0 10px 25px -5px rgba(228, 0, 43, 0.5)"
        }}
      >
        <motion.div
          initial={false}
          animate={{ scale: isRecording ? 0.9 : 1 }}
          transition={{ type: "spring", stiffness: 300, damping: 20 }}
        >
          {isConnecting ? (
            <Loader2 className="animate-spin text-gray-500" size={28} />
          ) : isRecording ? (
            <Square fill="currentColor" size={24} />
          ) : (
            <Mic size={28} />
          )}
        </motion.div>
      </motion.button>
    </div>
  );
}
