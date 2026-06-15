"use client";

import { useCallback, useState } from "react";
import { Upload, FileJson, Loader2 } from "lucide-react";

interface UploadFormProps {
  onUpload: (file: File) => void;
  onSample: () => void;
  loading: boolean;
}

export default function UploadForm({ onUpload, onSample, loading }: UploadFormProps) {
  const [dragActive, setDragActive] = useState(false);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);
      const file = e.dataTransfer.files?.[0];
      if (file && file.name.endsWith(".json")) {
        onUpload(file);
      }
    },
    [onUpload]
  );

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) onUpload(file);
  };

  return (
    <div className="w-full max-w-2xl mx-auto space-y-4">
      <div
        className={`upload-zone glass-card p-12 text-center cursor-pointer transition-all duration-300 ${
          dragActive ? "border-accent bg-accent/5" : "border-border hover:border-accent/50"
        } ${loading ? "opacity-50 pointer-events-none" : ""}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => document.getElementById("file-input")?.click()}
      >
        <input
          id="file-input"
          type="file"
          accept=".json"
          className="hidden"
          onChange={handleChange}
          disabled={loading}
        />
        {loading ? (
          <Loader2 className="w-12 h-12 mx-auto text-accent animate-spin" />
        ) : (
          <Upload className="w-12 h-12 mx-auto text-accent mb-4" />
        )}
        <h3 className="text-lg font-semibold mb-2">
          {loading ? "Analyzing trace..." : "Upload Agent Trace"}
        </h3>
        <p className="text-zinc-400 text-sm mb-4">
          Drag & drop a JSON trace file, or click to browse
        </p>
        <div className="flex items-center justify-center gap-2 text-xs text-zinc-500">
          <FileJson className="w-4 h-4" />
          Supports Generic, LangGraph, CrewAI formats
        </div>
      </div>

      <div className="text-center">
        <button
          onClick={onSample}
          disabled={loading}
          className="text-sm text-accent hover:text-accent-light transition-colors disabled:opacity-50"
        >
          Or analyze the sample trace →
        </button>
      </div>
    </div>
  );
}
