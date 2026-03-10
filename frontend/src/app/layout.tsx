import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'PrivacyFL — Privacy-Preserving Federated Learning Platform',
  description:
    'A secure platform for collaborative machine learning using Federated Learning, Differential Privacy, and Secure Aggregation.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
