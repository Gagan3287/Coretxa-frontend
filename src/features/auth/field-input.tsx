"use client";

import { useId, useState } from "react";
import { Eye, EyeOff } from "lucide-react";

interface Props {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: "text" | "email" | "password" | "tel";
  placeholder?: string;
  error?: string;
  hint?: string;
  autoComplete?: string;
  autoFocus?: boolean;
  disabled?: boolean;
}

export default function FieldInput({
  label,
  value,
  onChange,
  type = "text",
  placeholder,
  error,
  hint,
  autoComplete,
  autoFocus,
  disabled,
}: Props) {
  const id = useId();
  const [show, setShow] = useState(false);
  const isPassword = type === "password";
  const note = error ?? hint;

  return (
    <div className="auth-reveal flex flex-col gap-2">
      <label htmlFor={id} className="font-mono text-xs uppercase tracking-[0.2em] text-muted">
        {label}
      </label>
      <div className="relative">
        <input
          id={id}
          type={isPassword && show ? "text" : type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          autoComplete={autoComplete}
          autoFocus={autoFocus}
          disabled={disabled}
          aria-invalid={!!error}
          aria-describedby={note ? `${id}-note` : undefined}
          className={`w-full rounded-xl border bg-surface/70 px-4 py-4 text-sm text-foreground outline-none backdrop-blur transition placeholder:text-muted/50 focus:ring-2 disabled:opacity-60 ${
            isPassword ? "pr-12" : ""
          } ${
            error
              ? "border-red-400/60 focus:border-red-400 focus:ring-red-400/30"
              : "border-border focus:border-secondary focus:ring-secondary/30"
          }`}
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setShow((s) => !s)}
            aria-label={show ? "Hide password" : "Show password"}
            className="absolute right-3 top-1/2 -translate-y-1/2 rounded-lg p-2 text-muted transition hover:text-foreground"
          >
            {show ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        )}
      </div>
      {note && (
        <p id={`${id}-note`} className={`text-xs ${error ? "text-red-400" : "text-muted"}`}>
          {note}
        </p>
      )}
    </div>
  );
}