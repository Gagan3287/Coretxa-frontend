import Badge from "@/components/ui/badge";
import Button from "@/components/ui/button";
import Card from "@/components/ui/card";
import Input from "@/components/ui/input";

export default function Kit() {
  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <h1 className="font-display text-3xl font-bold tracking-tight">Component kit</h1>

      <Card className="space-y-4">
        <p className="font-mono text-xs text-muted">BUTTONS</p>
        <div className="flex flex-wrap gap-3">
          <Button>Primary</Button>
          <Button variant="outline">Outline</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="danger">Delete</Button>
          <Button size="sm">Small</Button>
          <Button disabled>Disabled</Button>
        </div>
      </Card>

      <Card className="space-y-4">
        <p className="font-mono text-xs text-muted">BADGES</p>
        <div className="flex flex-wrap gap-3">
          <Badge tone="live">Live</Badge>
          <Badge tone="processing">Processing</Badge>
          <Badge tone="neutral">Draft</Badge>
          <Badge tone="error">Failed</Badge>
        </div>
      </Card>

      <Card className="space-y-4">
        <p className="font-mono text-xs text-muted">INPUTS</p>
        <Input id="bot" label="Bot name" placeholder="e.g. Customer Support" />
        <Input id="site" label="Allowed website" placeholder="https://example.com" hint="Origins only, no paths." />
      </Card>
    </div>
  );
}