import { cn } from "@/lib/utils/cn";

type Props = React.TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label?: string;
  hint?: string;
  error?: string;
};

export default function Textarea({ label, hint, error, id, className, ...props }: Props) {
  return (
    <div className="flex flex-col gap-2">
      {label && (
        <label htmlFor={id} className="font-mono text-xs uppercase tracking-wider text-muted">
          {label}
        </label>
      )}
      <textarea
        id={id}
        aria-invalid={!!error}
        rows={3}
        className={cn(
          "resize-none rounded-xl border bg-surface px-4 py-3 text-sm text-foreground outline-none transition placeholder:text-muted/60 focus:ring-2",
          error
            ? "border-red-400/60 focus:border-red-400 focus:ring-red-400/30"
            : "border-border focus:border-primary focus:ring-primary/30",
          className
        )}
        {...props}
      />
      {error ? (
        <p className="text-xs text-red-400">{error}</p>
      ) : (
        hint && <p className="text-xs text-muted">{hint}</p>
      )}
    </div>
  );
}