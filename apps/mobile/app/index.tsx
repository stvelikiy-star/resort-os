import { Redirect } from 'expo-router';
import { useSession } from '../src/state/session';
import { homeForSession } from '../src/roles/registry';

export default function Index() {
  const { hotel, user, api } = useSession();
  if (!hotel) return <Redirect href="/connect" />;
  if (!user) return <Redirect href="/login" />;
  return <Redirect href={homeForSession(user.role, user.module_permissions, api?.mode ?? 'LIVE')} />;
}
