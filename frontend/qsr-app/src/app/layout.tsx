import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

import { Providers } from "@/components/Providers";
import { ConfigProvider } from "@/components/ConfigProvider";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AI QSR Voice Assistant",
  description: "Next-generation quick service restaurant voice assistant powered by Amazon Bedrock and AgentCore",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-[#1a1a2e] text-white antialiased min-h-screen`}>
        <ConfigProvider>
          <Providers>
            {children}
          </Providers>
        </ConfigProvider>
      </body>
    </html>
  );
}
