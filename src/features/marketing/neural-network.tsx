"use client";

import { useRef } from "react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";

gsap.registerPlugin(useGSAP);

const nodes: [number, number][] = [
  [80, 120], [200, 60], [330, 110], [470, 70], [540, 190], [430, 250], [300, 210], [170, 230],
  [90, 340], [220, 380], [350, 340], [490, 380], [410, 500], [260, 510], [140, 480],
];

const edges: [number, number][] = [
  [0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7], [7, 0], [1, 6], [2, 6], [5, 10], [6, 10],
  [7, 8], [8, 9], [9, 10], [10, 11], [11, 5], [9, 13], [10, 12], [12, 13], [13, 14], [14, 8], [11, 12],
];

export default function NeuralNetwork() {
  const root = useRef<SVGSVGElement>(null);

  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add("(prefers-reduced-motion: no-preference)", () => {
        gsap.from(".nn-edge", { strokeDashoffset: 1, duration: 1.6, stagger: 0.05, ease: "power2.out" });
        gsap.to(".nn-node", {
          opacity: 0.3,
          duration: 1.6,
          ease: "sine.inOut",
          stagger: { each: 0.15, repeat: -1, yoyo: true },
        });
      });
      return () => mm.revert();
    },
    { scope: root }
  );

  return (
    <svg
      ref={root}
      viewBox="0 0 600 600"
      className="absolute inset-0 h-full w-full text-primary"
      aria-hidden="true"
    >
      {edges.map(([a, b], i) => (
        <line
          key={i}
          className="nn-edge"
          x1={nodes[a][0]}
          y1={nodes[a][1]}
          x2={nodes[b][0]}
          y2={nodes[b][1]}
          stroke="currentColor"
          strokeOpacity="0.35"
          strokeWidth="1.2"
          pathLength={1}
          strokeDasharray="1"
        />
      ))}
      {nodes.map(([x, y], i) => (
        <circle key={i} className="nn-node fill-secondary" cx={x} cy={y} r="5" />
      ))}
    </svg>
  );
}