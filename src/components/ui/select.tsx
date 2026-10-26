import { cn } from "@/lib/utils/cn";

type Props = React.SelectHTMLAttributes<HTMLSelectElement> & {
  label?: string;
};

export default function Select({ label, id, className, children, ...props }: Props) {
  return (
    <div className="flex flex-col gap-2">
      {label && (
        <label htmlFor={id} className="font-mono text-xs uppercase tracking-wider text-muted">
          {label}
        </label>
      )}
      <select
        id={id}
        className={cn(
          "rounded-xl border border-border bg-surface px-4 py-3 text-sm text-foreground outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/30",
          className
        )}
        {...props}
      >
        {children}
      </select>
    </div>
  );
}