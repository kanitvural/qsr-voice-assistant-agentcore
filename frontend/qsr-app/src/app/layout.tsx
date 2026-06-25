import type { Metadata } from "next";
import "./globals.css";

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
      <body>{children}</body>
    </html>
  );
}
