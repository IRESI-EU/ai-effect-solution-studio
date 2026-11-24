import { IBM_Plex_Mono, SUSE } from "next/font/google";
import "./globals.css";
import "./design-tokens.css";
import "./design-components.css";
import "./design-shell.css";
import { Shell } from "../components/shell";
import { AuthProvider } from "../components/auth-context";

const sans = SUSE({ subsets: ["latin"], weight: ["400", "500", "600", "700"], variable: "--font-sans", display: "swap" });
const mono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-mono", display: "swap" });

export const metadata = {
  title: "AI-EFFECT Platform",
  description: "Discover, compose and run trusted AI services for energy",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${sans.variable} ${mono.variable}`}>
      <body>
        <AuthProvider>
          <Shell>{children}</Shell>
        </AuthProvider>
      </body>
    </html>
  );
}
