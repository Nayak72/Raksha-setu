/**
 * Alerts page removed — redirects to dashboard.
 */
import { redirect } from 'next/navigation';

export default function AlertsPage() {
  redirect('/dashboard');
}
