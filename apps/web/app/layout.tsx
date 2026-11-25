import "./globals.css";
import { Shell } from "../components/shell";
import { AuthProvider } from "../components/auth-context";

export const metadata = {
  title: "AI-EFFECT Web portal",
  description: "Discover, compose, validate, and run trusted AI-EFFECT services",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <Shell>{children}</Shell>
        </AuthProvider>
      </body>
    </html>
  );
}
