import Button from "@/components/ui/button";
import CopyButton from "@/components/ui/copy-button";

export default function EmbedOptions({ hostedUrl }: { hostedUrl: string }) {
  const iframe = `<iframe
  src="${hostedUrl}"
  title="Chat with our AI assistant"
  width="100%"
  height="600"
  style="border: 0; border-radius: 12px;"
  loading="lazy"
></iframe>`;

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <section className="rounded-2xl border border-border bg-surface p-5">
        <h2 className="font-display text-lg font-semibold">Iframe embed</h2>
        <p className="mt-1 text-sm text-muted">
          Use this when you can&apos;t add a script to your site. The hosted page must allow embedding on
          your websites, which the backend will control.
        </p>
        <div className="mt-4 overflow-hidden rounded-xl border border-border bg-background">
          <div className="flex items-center justify-between border-b border-border px-4 py-2">
            <span className="font-mono text-xs text-muted">iframe</span>
            <CopyButton text={iframe} label="Copy code" />
          </div>
          <pre className="overflow-x-auto p-4 font-mono text-xs leading-relaxed" data-lenis-prevent>
            <code>{iframe}</code>
          </pre>
        </div>
      </section>

      <section className="rounded-2xl border border-border bg-surface p-5">
        <h2 className="font-display text-lg font-semibold">Hosted chat page</h2>
        <p className="mt-1 text-sm text-muted">
          A standalone page for this bot that you can share by link. This URL is a placeholder, and the
          page does not exist yet.
        </p>
        <div className="mt-4 break-all rounded-xl border border-border bg-background px-4 py-3 font-mono text-xs">
          {hostedUrl}
        </div>
        <div className="mt-4 flex flex-wrap gap-3">
          <CopyButton text={hostedUrl} label="Copy link" />
          <Button variant="outline" size="sm" disabled title="Available once hosted pages are built">
            Open preview
          </Button>
        </div>
      </section>
    </div>
  );
}