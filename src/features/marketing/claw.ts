// Claw-scratch mask for the DEPLOY word.
// Each slash: [topX, topY, bottomX, bottomY, halfWidth] in a 330 x 100 box.
const W = 330;
const H = 100;

const slashes: [number, number, number, number, number][] = [
  [40, -6, 12, 106, 5.2],
  [56, 10, 40, 88, 2.4],
  [84, -6, 50, 106, 6.5],
  [101, -6, 70, 106, 4.2],
  [117, 10, 94, 92, 2.6],
  [178, -6, 146, 106, 7.2],
  [196, -6, 167, 106, 4.4],
  [213, 14, 192, 88, 2.4],
  [262, -6, 230, 106, 6.2],
  [279, -6, 250, 106, 4.0],
  [296, 6, 272, 94, 2.8],
  [326, -6, 300, 76, 3.6],
];

export function clawSvg(): string {
  const polys = slashes
    .map(([tx, ty, bx, by, w]) => {
      const at = (t: number, off: number) =>
        `${(tx + (bx - tx) * t + off).toFixed(1)},${(ty + (by - ty) * t).toFixed(1)}`;
      const pts = [
        at(0, 0),
        at(0.18, -w * 0.5),
        at(0.4, -w),
        at(0.7, -w * 0.6),
        at(1, 0),
        at(0.76, w * 0.5),
        at(0.5, w),
        at(0.24, w * 0.55),
      ];
      return `<polygon points='${pts.join(" ")}'/>`;
    })
    .join("");

  return (
    `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 ${W} ${H}' preserveAspectRatio='none'>` +
    `<defs><mask id='m' maskUnits='userSpaceOnUse' x='0' y='0' width='${W}' height='${H}'>` +
    `<rect width='${W}' height='${H}' fill='white'/><g fill='black'>${polys}</g></mask></defs>` +
    `<rect width='${W}' height='${H}' fill='black' mask='url(#m)'/></svg>`
  );
}

export function clawMaskUrl(): string {
  return `url("data:image/svg+xml,${encodeURIComponent(clawSvg())}")`;
}