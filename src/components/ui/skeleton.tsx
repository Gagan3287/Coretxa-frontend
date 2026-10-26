import { cn } from "@/lib/utils/cn";

export default function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-xl bg-foreground/10", className)} />;
}