// Taste profile now lives on the account page.
import { redirect } from 'next/navigation';

export default function TasteProfilePage() {
  redirect('/account#taste-profile');
}
