import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AgentScope — AI Agent Failure Analyzer",
  description: "Datadog for AI Agents. Analyze execution traces, detect loops, hallucinations, and cost hotspots.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
