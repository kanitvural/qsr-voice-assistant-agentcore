"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Wrench } from "lucide-react";

interface ToolExecutionBannerProps {
  toolName: string | null;
}

export function ToolExecutionBanner({ toolName }: ToolExecutionBannerProps) {
  const getToolDisplayName = (name: string): string => {
    const toolMap: Record<string, string> = {
      'get_customer_location': 'Getting your location...',
      'qsr-backend-api___GetPreviousOrders': 'Loading previous orders...',
      'qsr-backend-api___GetNearestLocations': 'Finding nearby restaurants...',
      'qsr-backend-api___GetMenu': 'Loading menu...',
      'qsr-backend-api___AddToCart': 'Adding to cart...',
      'qsr-backend-api___PlaceOrder': 'Placing your order...',
      'qsr-backend-api___GetCustomerProfile': 'Loading your profile...',
      'qsr-backend-api___GeocodeAddress': 'Looking up address...',
      'qsr-backend-api___FindLocationAlongRoute': 'Finding locations along route...'
    };
    return toolMap[name] || `Executing ${name}...`;
  };

  return (
    <AnimatePresence>
      {toolName && (
        <motion.div
          initial={{ opacity: 0, height: 0, y: -20 }}
          animate={{ opacity: 1, height: "auto", y: 0 }}
          exit={{ opacity: 0, height: 0, y: -20 }}
          className="overflow-hidden bg-qsr-gold text-qsr-dark shadow-md"
        >
          <div className="flex items-center gap-3 px-5 py-3 text-[14px] font-semibold">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ repeat: Infinity, duration: 2, ease: "linear" }}
            >
              <Wrench size={16} />
            </motion.div>
            <span>{getToolDisplayName(toolName)}</span>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
