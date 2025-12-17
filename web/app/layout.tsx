import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Tastebuds',
  description: 'Curate cross-medium menus with Tastebuds.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-950 text-slate-50">{children}</body>
    </html>
  );
}
