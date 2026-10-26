import EmptyState from "@/components/ui/empty-state";
import PageHeader from "@/components/ui/page-header";

const titles: Record<string, string> = {
  bots: "Bots",
  documents: "Documents",
  widget: "Widget & Embed",
  analytics: "Analytics",
  usage: "Usage & Limits",
  audit: "Audit Log",
  settings: "Settings",
};

export default async function Section({ params }: { params: Promise<{ section: string }> }) {
  const { section } = await params;
  const title = titles[section] ?? "Not found";

  return (
    <div className="mx-auto w-full max-w-[1440px]">
      <PageHeader title={title} />
      <div className="mt-8">
        <EmptyState
          title="Coming soon"
          description="This screen is built in a later step."
        />
      </div>
    </div>
  );
}