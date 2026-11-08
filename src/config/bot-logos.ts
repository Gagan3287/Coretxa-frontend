export interface BotLogo {
  id: string;
  name: string;
  gradient: string;
  bgTone: string;
  badge: string;
  svg: string;
}

export const BOT_LOGOS: BotLogo[] = [
  {
    id: "neural-core",
    name: "Neural Core",
    gradient: "from-indigo-500 to-cyan-400",
    bgTone: "bg-indigo-500/15 text-indigo-400 border-indigo-500/30",
    badge: "Neural",
    svg: `<svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" class="w-full h-full">
      <circle cx="20" cy="20" r="18" fill="url(#g-neural)" fill-opacity="0.2" stroke="#818cf8" stroke-width="2"/>
      <circle cx="20" cy="14" r="3.5" fill="#22d3ee"/>
      <circle cx="13" cy="24" r="3" fill="#818cf8"/>
      <circle cx="27" cy="24" r="3" fill="#818cf8"/>
      <circle cx="20" cy="28" r="2.5" fill="#a5b4fc"/>
      <path d="M20 14L13 24M20 14L27 24M13 24L20 28M27 24L20 28M13 24H27" stroke="#e0e7ff" stroke-width="1.5" stroke-linecap="round" stroke-dasharray="1 1"/>
      <defs><linearGradient id="g-neural" x1="0" y1="0" x2="40" y2="40"><stop stop-color="#6366f1"/><stop offset="1" stop-color="#06b6d4"/></linearGradient></defs>
    </svg>`,
  },
  {
    id: "quantum-spark",
    name: "Quantum Spark",
    gradient: "from-fuchsia-500 to-violet-400",
    bgTone: "bg-fuchsia-500/15 text-fuchsia-400 border-fuchsia-500/30",
    badge: "Quantum",
    svg: `<svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" class="w-full h-full">
      <circle cx="20" cy="20" r="18" fill="url(#g-quantum)" fill-opacity="0.2" stroke="#e879f9" stroke-width="2"/>
      <path d="M20 7L22.5 16.5L32 19L22.5 21.5L20 31L17.5 21.5L8 19L17.5 16.5L20 7Z" fill="#f0abfc"/>
      <circle cx="20" cy="19" r="3" fill="#ffffff"/>
      <circle cx="30" cy="10" r="1.5" fill="#c084fc"/>
      <circle cx="10" cy="28" r="1.5" fill="#e879f9"/>
      <defs><linearGradient id="g-quantum" x1="0" y1="0" x2="40" y2="40"><stop stop-color="#d946ef"/><stop offset="1" stop-color="#8b5cf6"/></linearGradient></defs>
    </svg>`,
  },
  {
    id: "cyber-shield",
    name: "Cyber Shield",
    gradient: "from-emerald-500 to-teal-400",
    bgTone: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
    badge: "Security",
    svg: `<svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" class="w-full h-full">
      <circle cx="20" cy="20" r="18" fill="url(#g-shield)" fill-opacity="0.2" stroke="#34d399" stroke-width="2"/>
      <path d="M20 9L29 13.5V20.5C29 25.5 25.2 29.8 20 31C14.8 29.8 11 25.5 11 20.5V13.5L20 9Z" fill="#059669" fill-opacity="0.4" stroke="#34d399" stroke-width="2" stroke-linejoin="round"/>
      <path d="M16 20L19 23L24 17" stroke="#a7f3d0" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      <defs><linearGradient id="g-shield" x1="0" y1="0" x2="40" y2="40"><stop stop-color="#10b981"/><stop offset="1" stop-color="#14b8a6"/></linearGradient></defs>
    </svg>`,
  },
  {
    id: "code-sentinel",
    name: "Code Sentinel",
    gradient: "from-amber-500 to-orange-400",
    bgTone: "bg-amber-500/15 text-amber-400 border-amber-500/30",
    badge: "DevOps",
    svg: `<svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" class="w-full h-full">
      <circle cx="20" cy="20" r="18" fill="url(#g-code)" fill-opacity="0.2" stroke="#fbbf24" stroke-width="2"/>
      <path d="M14 15L9 20L14 25" stroke="#fcd34d" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M26 15L31 20L26 25" stroke="#fcd34d" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M22 13L18 27" stroke="#fb923c" stroke-width="2" stroke-linecap="round"/>
      <defs><linearGradient id="g-code" x1="0" y1="0" x2="40" y2="40"><stop stop-color="#f59e0b"/><stop offset="1" stop-color="#f97316"/></linearGradient></defs>
    </svg>`,
  },
  {
    id: "pulse-ai",
    name: "Pulse AI",
    gradient: "from-rose-500 to-pink-400",
    bgTone: "bg-rose-500/15 text-rose-400 border-rose-500/30",
    badge: "Audio & Data",
    svg: `<svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" class="w-full h-full">
      <circle cx="20" cy="20" r="18" fill="url(#g-pulse)" fill-opacity="0.2" stroke="#fb7185" stroke-width="2"/>
      <path d="M8 20H13L16 12L20 28L24 16L27 23H32" stroke="#fda4af" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
      <circle cx="20" cy="28" r="1.5" fill="#fff"/>
      <circle cx="16" cy="12" r="1.5" fill="#fff"/>
      <defs><linearGradient id="g-pulse" x1="0" y1="0" x2="40" y2="40"><stop stop-color="#f43f5e"/><stop offset="1" stop-color="#ec4899"/></linearGradient></defs>
    </svg>`,
  },
  {
    id: "hex-reactor",
    name: "Hex Reactor",
    gradient: "from-cyan-500 to-blue-500",
    bgTone: "bg-cyan-500/15 text-cyan-400 border-cyan-500/30",
    badge: "Compute",
    svg: `<svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" class="w-full h-full">
      <circle cx="20" cy="20" r="18" fill="url(#g-hex)" fill-opacity="0.2" stroke="#38bdf8" stroke-width="2"/>
      <path d="M20 9L29 14.2V24.8L20 30L11 24.8V14.2L20 9Z" stroke="#38bdf8" stroke-width="2" fill="#0284c7" fill-opacity="0.3"/>
      <circle cx="20" cy="19.5" r="4.5" fill="#67e8f9" stroke="#ffffff" stroke-width="1.5"/>
      <defs><linearGradient id="g-hex" x1="0" y1="0" x2="40" y2="40"><stop stop-color="#06b6d4"/><stop offset="1" stop-color="#3b82f6"/></linearGradient></defs>
    </svg>`,
  },
  {
    id: "nova-galaxy",
    name: "Nova Galaxy",
    gradient: "from-purple-600 to-indigo-400",
    bgTone: "bg-purple-500/15 text-purple-400 border-purple-500/30",
    badge: "Analytics",
    svg: `<svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" class="w-full h-full">
      <circle cx="20" cy="20" r="18" fill="url(#g-nova)" fill-opacity="0.2" stroke="#c084fc" stroke-width="2"/>
      <ellipse cx="20" cy="20" rx="13" ry="5.5" transform="rotate(-30 20 20)" stroke="#e9d5ff" stroke-width="1.8"/>
      <ellipse cx="20" cy="20" rx="13" ry="5.5" transform="rotate(30 20 20)" stroke="#c084fc" stroke-width="1.8"/>
      <circle cx="20" cy="20" r="4" fill="#a855f7" stroke="#ffffff" stroke-width="1.5"/>
      <circle cx="28" cy="14" r="1.5" fill="#e9d5ff"/>
      <defs><linearGradient id="g-nova" x1="0" y1="0" x2="40" y2="40"><stop stop-color="#9333ea"/><stop offset="1" stop-color="#6366f1"/></linearGradient></defs>
    </svg>`,
  },
  {
    id: "bolt-prime",
    name: "Bolt Prime",
    gradient: "from-yellow-400 to-amber-500",
    bgTone: "bg-yellow-400/15 text-yellow-300 border-yellow-400/30",
    badge: "Realtime",
    svg: `<svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" class="w-full h-full">
      <circle cx="20" cy="20" r="18" fill="url(#g-bolt)" fill-opacity="0.2" stroke="#facc15" stroke-width="2"/>
      <path d="M22 8L11 21H20L18 32L29 19H20L22 8Z" fill="#fde047" stroke="#ca8a04" stroke-width="1.5" stroke-linejoin="round"/>
      <defs><linearGradient id="g-bolt" x1="0" y1="0" x2="40" y2="40"><stop stop-color="#eab308"/><stop offset="1" stop-color="#f59e0b"/></linearGradient></defs>
    </svg>`,
  },
  {
    id: "nexus-companion",
    name: "Nexus Bot",
    gradient: "from-teal-400 to-emerald-500",
    bgTone: "bg-teal-500/15 text-teal-300 border-teal-500/30",
    badge: "Support",
    svg: `<svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" class="w-full h-full">
      <circle cx="20" cy="20" r="18" fill="url(#g-nexus)" fill-opacity="0.2" stroke="#2dd4bf" stroke-width="2"/>
      <rect x="11" y="13" width="18" height="14" rx="4" fill="#0d9488" fill-opacity="0.4" stroke="#2dd4bf" stroke-width="2"/>
      <circle cx="16" cy="19" r="2.2" fill="#5eead4"/>
      <circle cx="24" cy="19" r="2.2" fill="#5eead4"/>
      <path d="M16 23C17 24.5 23 24.5 24 23" stroke="#99f6e4" stroke-width="1.5" stroke-linecap="round"/>
      <path d="M20 9V13" stroke="#2dd4bf" stroke-width="2" stroke-linecap="round"/>
      <defs><linearGradient id="g-nexus" x1="0" y1="0" x2="40" y2="40"><stop stop-color="#14b8a6"/><stop offset="1" stop-color="#10b981"/></linearGradient></defs>
    </svg>`,
  },
  {
    id: "prism-oracle",
    name: "Prism Oracle",
    gradient: "from-blue-500 to-indigo-600",
    bgTone: "bg-blue-500/15 text-blue-400 border-blue-500/30",
    badge: "Knowledge",
    svg: `<svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" class="w-full h-full">
      <circle cx="20" cy="20" r="18" fill="url(#g-prism)" fill-opacity="0.2" stroke="#60a5fa" stroke-width="2"/>
      <path d="M20 10L30 16V24L20 30L10 24V16L20 10Z" stroke="#93c5fd" stroke-width="2" fill="#2563eb" fill-opacity="0.25"/>
      <path d="M20 10V30M10 16L30 24M10 24L30 16" stroke="#bfdbfe" stroke-width="1.2" stroke-linecap="round"/>
      <defs><linearGradient id="g-prism" x1="0" y1="0" x2="40" y2="40"><stop stop-color="#3b82f6"/><stop offset="1" stop-color="#4f46e5"/></linearGradient></defs>
    </svg>`,
  },
];

export function getBotLogo(id?: string | null): BotLogo {
  if (!id) return BOT_LOGOS[0];
  const found = BOT_LOGOS.find((l) => l.id === id);
  return found || BOT_LOGOS[0];
}
