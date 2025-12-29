// Integrations now live on the account page.
import { redirect } from 'next/navigation';

export default function IntegrationsPage() {
  redirect('/account#integrations');
}
