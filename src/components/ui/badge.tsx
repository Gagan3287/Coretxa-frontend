import { cn } from "@/lib/utils/cn";

type Props = React.HTMLAttributes<HTMLSpanElement> & {
  tone?: "live" | "processing" | "neutral" | "error";
};

const tones = {
  live: "bg-secondary/15 text-secondary",
  processing: "bg-primary/15 text-primary",
  neutral: "bg-foreground/10 text-muted",
  error: "bg-red-500/15 text-red-400",
};

export default function Badge({ tone = "neutral", className, ...props }: Props) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center whitespace-nowrap rounded-full px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider",
        tones[tone],
        className
      )}
      {...props}
    />
  );
}