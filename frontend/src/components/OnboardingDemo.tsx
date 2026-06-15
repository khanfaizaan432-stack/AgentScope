"use client";

import { ScanSearch, Loader2, Sparkles } from "lucide-react";

interface OnboardingDemoProps {
  onTriage: () => void;
  loading?: boolean;
}

export default function OnboardingDemo({ onTriage, loading }: OnboardingDemoProps) {
  return (
    <section className="glass-card p-6 md:p-8 border border-accent/20 bg-accent/5">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
        <div className="space-y-3 flex-1">
          <div className="inline-flex items-center gap-2 text-xs font-medium text-accent bg-accent/10 px-3 py-1 rounded-full">
            <Sparkles className="w-3.5 h-3.5" />
            Interactive Demo
          </div>
          <h2 className="text-xl md:text-2xl font-semibold text-zinc-100 leading-snug">
            🕵️‍♂️ Recruiter Triage Challenge
          </h2>
          <p className="text-sm md:text-base text-zinc-400 max-w-2xl">
            An agent trace just failed in production. Can you find the bug manually — or let
            AgentScope triage it in one click?
          </p>
        </div>

        <button
          type="button"
          onClick={onTriage}
          disabled={loading}
          className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-lg bg-accent hover:bg-accent/90 text-white font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed min-w-[220px]"
        >
          {loading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Scanning trace...
            </>
          ) : (
            <>
              <ScanSearch className="w-5 h-5" />
              Let AgentScope Triage
            </>
          )}
        </button>
      </div>

      {loading && (
        <div className="mt-6 h-1.5 rounded-full bg-zinc-800 overflow-hidden">
          <div className="h-full bg-accent animate-pulse rounded-full w-full origin-left" />
        </div>
      )}
    </section>
  );
}
