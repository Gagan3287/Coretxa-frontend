import Badge from "@/components/ui/badge";
import Button from "@/components/ui/button";
import Card from "@/components/ui/card";
import PageHeader from "@/components/ui/page-header";

const stats = [
  { label: "Active bots", value: "3" },
  { label: "Documents", value: "24" },
  { label: "Conversations (30d)", value: "1,284" },
  { label: "Answer rate", value: "92%" },
];

const bots = [
  { name: "Customer Support", docs: 12, status: "Live" },
  { name: "HR Policy", docs: 8, status: "Live" },
  { name: "Product Docs", docs: 4, status: "Processing" },
];

export default function Overview() {
  return (
    <div className="mx-auto w-full max-w-[1440px]">
      <PageHeader
        title="Overview"
        description="Sample data for design purposes. Not connected to the backend yet."
        actions={<Button>New bot</Button>}
      />

      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((s) => (
          <Card key={s.label}>
            <p className="text-sm text-muted">{s.label}</p>
            <p className="font-display mt-3 text-3xl font-bold">{s.value}</p>
          </Card>
        ))}
      </div>

      <h2 className="font-display mt-12 text-xl font-semibold">Your bots</h2>
      <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {bots.map((b) => (
          <Card key={b.name}>
            <div className="flex items-start justify-between gap-3">
              <h3 className="font-semibold">{b.name}</h3>
              <Badge tone={b.status === "Live" ? "live" : "processing"}>{b.status}</Badge>
            </div>
            <p className="mt-4 text-sm text-muted">{b.docs} documents</p>
          </Card>
        ))}
      </div>
    </div>
  );
}