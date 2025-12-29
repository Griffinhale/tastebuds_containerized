// Taste profile page now redirects to the account overview.
import { redirect } from 'next/navigation';

export default function TasteProfilePage() {
  redirect('/account#profile');
}
