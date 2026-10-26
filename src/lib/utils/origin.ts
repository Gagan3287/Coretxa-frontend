export function normalizeOrigin(input: string): { origin?: string; error?: string } {
  const raw = input.trim();
  if (!raw) return { error: "Enter a website address." };
  if (raw.includes("*")) return { error: "Wildcards aren't supported. Add each website separately." };

  const withProtocol = /^[a-z][a-z0-9+.-]*:\/\//i.test(raw) ? raw : `https://${raw}`;
  let url: URL;
  try {
    url = new URL(withProtocol);
  } catch {
    return { error: "That doesn't look like a valid website address." };
  }

  const isLocal = url.hostname === "localhost" || url.hostname === "127.0.0.1";
  if (url.protocol !== "https:" && !(url.protocol === "http:" && isLocal)) {
    return { error: "Use https:// (http is only allowed for localhost)." };
  }
  if (url.username || url.password) return { error: "Remove the username or password from the address." };
  if (!isLocal && !url.hostname.includes(".")) return { error: "Enter a full domain, like example.com." };

  return { origin: url.origin };
}

export function readableTextOn(hex: string) {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex);
  if (!m) return "#ffffff";
  const n = parseInt(m[1], 16);
  const [r, g, b] = [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  return (r * 299 + g * 587 + b * 114) / 1000 > 150 ? "#0b1020" : "#ffffff";
}