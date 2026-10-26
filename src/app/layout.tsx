import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Space_Grotesk } from "next/font/google";
import PageTransition from "@/components/effects/page-transition";
import SmoothScroll from "@/components/providers/smooth-scroll";
import { anton } from "@/lib/fonts";
import "./globals.css";

const grotesk = Space_Grotesk({ subsets: ["latin"], variable: "--font-grotesk" });
const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const jetbrains = JetBrains_Mono({ subsets: ["latin"], variable: "--font-jetbrains" });

export const metadata: Metadata = {
  metadataBase: new URL("https://cortexa-io.vercel.app"),
  title: "Cortexa",
  description: "Build, customize and deploy AI assistants trained on your documents.",
};

const themeScript = `try{document.documentElement.dataset.theme=localStorage.getItem('theme')||'dark'}catch(e){}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${grotesk.variable} ${inter.variable} ${jetbrains.variable} ${anton.variable}`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>
        <SmoothScroll>{children}</SmoothScroll>
        <PageTransition />
      </body>
    </html>
  );
}
