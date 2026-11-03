import { Redirect } from 'expo-router';
import { useSession } from '../src/state/session';
import { homeFor } from '../src/roles/registry';

export default function Index() {
  const { hotel, user } = useSession();
  if (!hotel) return <Redirect href="/connect" />;
  if (!user) return <Redirect href="/login" />;
  return <Redirect href={homeFor(user.role)} />;
}
