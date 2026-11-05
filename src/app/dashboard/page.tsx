import type { Metadata } from "next";
import WorkbenchView from "@/features/workbench/workbench-view";

export const metadata: Metadata = {
  title: "Workbench & Execution Engine | Cortexa",
  description: "Live click-to-run C Algorithms and Computing lab assignments powered by Cortexa backend engine.",
};

export default function DashboardPage() {
  return <WorkbenchView />;
}
