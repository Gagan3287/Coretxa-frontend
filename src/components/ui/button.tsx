import { cn } from "@/lib/utils/cn";

type Props = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "outline" | "ghost" | "danger";
  size?: "sm" | "md";
};

const variants = {
  primary: "bg-primary text-primary-foreground hover:-translate-y-0.5",
  outline: "border border-border bg-surface text-foreground hover:-translate-y-0.5",
  ghost: "text-muted hover:bg-foreground/5 hover:text-foreground",
  danger: "bg-red-500/15 text-red-400 hover:bg-red-500/25",
};

const sizes = {
  sm: "px-4 py-2 text-xs",
  md: "px-6 py-3 text-sm",
};

export default function Button({ variant = "primary", size = "md", className, ...props }: Props) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-full font-semibold transition-all duration-200 disabled:pointer-events-none disabled:opacity-50",
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    />
  );
}