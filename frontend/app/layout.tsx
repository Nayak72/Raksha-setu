import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'RakshaSethu — Disaster Command Center',
  description: 'Agentic AI for Disaster Relief Coordination and Supply Management. Real-time disaster monitoring, YOLO detection, and multi-agent response system.',
  keywords: ['disaster management', 'agentic AI', 'emergency response', 'RakshaSethu'],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className="min-h-screen bg-surface-950 antialiased" suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
