import { cn } from "@/lib/utils/cn";

export default function Card({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("rounded-2xl border border-border bg-surface p-5", className)}
      {...props}
    />
  );
}