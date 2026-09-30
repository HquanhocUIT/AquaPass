import type { Metadata } from "next";
import "./globals.css";
import "./aquatic-theme.css";
import "./intro.css";

export const metadata: Metadata = {
  title: "AquaPass | Evidence for better water-health decisions",
  description:
    "AquaPass connects water-health evidence, uncertainty and response actions for One Health teams.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
