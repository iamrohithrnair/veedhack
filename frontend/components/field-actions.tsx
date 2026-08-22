"use client";

import { Check, ClipboardPaste, Copy, Trash2 } from "lucide-react";
import { useState } from "react";

type FieldActionsProps = {
  value: string;
  onChange: (value: string) => void;
  className?: string;
  copyLabel?: string;
  pasteLabel?: string;
  clearLabel?: string;
};

export function FieldActions({
  value,
  onChange,
  className,
  copyLabel = "Copy",
  pasteLabel = "Paste",
  clearLabel = "Clear",
}: FieldActionsProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!value) return;
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      // Fallback if clipboard permission fails
    }
  };

  const handlePaste = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      const text = await navigator.clipboard.readText();
      if (typeof text === "string") {
        onChange(text);
      }
    } catch {
      // Fallback
    }
  };

  const handleClear = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onChange("");
  };

  return (
    <span className={`field-actions ${className || ""}`} role="toolbar" aria-label="Text field controls">
      <button
        type="button"
        className="field-action-btn"
        onClick={handleCopy}
        disabled={!value}
        title={copied ? "Copied!" : "Copy text"}
        aria-label="Copy text"
      >
        {copied ? <Check size={11} className="copy-success-icon" /> : <Copy size={11} />}
        <span>{copied ? "Copied" : copyLabel}</span>
      </button>
      <button
        type="button"
        className="field-action-btn"
        onClick={handlePaste}
        title="Paste from clipboard"
        aria-label="Paste text"
      >
        <ClipboardPaste size={11} />
        <span>{pasteLabel}</span>
      </button>
      <button
        type="button"
        className="field-action-btn delete-btn"
        onClick={handleClear}
        disabled={!value}
        title="Clear text"
        aria-label="Clear text"
      >
        <Trash2 size={11} />
        <span>{clearLabel}</span>
      </button>
    </span>
  );
}
