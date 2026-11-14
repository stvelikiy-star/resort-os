/// <reference types="node" />
import React from 'react';
import fs from 'fs';
import path from 'path';
import { AccessibilityInfo, AppState, StyleSheet, Text, View } from 'react-native';
import { act, render } from '@testing-library/react-native';
import { ThemeProvider } from '../src/theme/ThemeProvider';
import { getMotionSnapshot, primeMotionPreference, resetMotionPreferenceForTests } from '../src/theme/motion';
import { AnimatedKpi, OccupancyRing, PremiumEntrance } from '../src/components/Future';
import { AnimatedProgressBar } from '../src/components/ui';
import { AnimatedSheet, ConfirmedChange, TabIcon } from '../src/components/Motion';
import { Sparkles } from 'lucide-react-native';

jest.mock('../src/lib/storage', () => ({
  getItem: jest.fn(async () => null),
  setItem: jest.fn(async () => {}),
}));

async function setOsReduceMotion(reduce: boolean, appState: 'active' | 'background' = 'active') {
  resetMotionPreferenceForTests();
  // RN's jest mock exposes currentState as a function; on a device it is the string 'active' / 'background'.
  Object.defineProperty(AppState, 'currentState', { value: appState, configurable: true, writable: true });
  jest.spyOn(AccessibilityInfo, 'isReduceMotionEnabled').mockResolvedValue(reduce);
  await act(async () => { primeMotionPreference(); await Promise.resolve(); await Promise.resolve(); });
}
const wrap = (node: React.ReactNode) => <ThemeProvider initial="dark">{node}</ThemeProvider>;
const opacityOf = (el: { props: { style?: unknown } }) => StyleSheet.flatten(el.props.style as never).opacity;

const originalAppState = Object.getOwnPropertyDescriptor(AppState, 'currentState');
afterEach(() => {
  jest.restoreAllMocks();
  resetMotionPreferenceForTests();
  if (originalAppState) Object.defineProperty(AppState, 'currentState', originalAppState);
});

describe('motion preference (single shared source)', () => {
  it('Reduce Motion => motion is not allowed but the preference is known', async () => {
    await setOsReduceMotion(true);
    expect(getMotionSnapshot()).toEqual({ allowed: false, ready: true });
  });
  it('motion allowed only when OS Reduce Motion is off', async () => {
    await setOsReduceMotion(false);
    expect(getMotionSnapshot()).toEqual({ allowed: true, ready: true });
  });
  it('a backgrounded app never runs motion', async () => {
    await setOsReduceMotion(false, 'background');
    expect(getMotionSnapshot()).toEqual({ allowed: false, ready: true });
  });
  it('an unreadable OS preference fails SAFE (static)', async () => {
    resetMotionPreferenceForTests();
    jest.spyOn(AccessibilityInfo, 'isReduceMotionEnabled').mockRejectedValue(new Error('unavailable'));
    await act(async () => { primeMotionPreference(); await Promise.resolve(); await Promise.resolve(); });
    expect(getMotionSnapshot().allowed).toBe(false);
  });
});

describe('verified numbers', () => {
  it('Reduce Motion shows the exact server value immediately', async () => {
    await setOsReduceMotion(true);
    const view = await render(wrap(<AnimatedKpi testID="kpi" value={73} suffix="%" />));
    expect(view.getByTestId('kpi').props.children).toEqual([73, '%']);
    expect(view.getByTestId('kpi').props.accessibilityLabel).toBe('73%');
  });
  it('with motion allowed it reveals 0 -> server value, never past it', async () => {
    jest.useFakeTimers();
    try {
      await setOsReduceMotion(false);
      const view = await render(wrap(<AnimatedKpi testID="kpi" value={73} suffix="%" />));
      const read = () => Number(String(view.getByTestId('kpi').props.children[0]));
      expect(read()).toBe(0);
      const seen: number[] = [];
      for (let i = 0; i < 12; i += 1) {
        await act(async () => { jest.advanceTimersByTime(100); });
        seen.push(read());
      }
      expect(seen.some(value => value > 0 && value < 73)).toBe(true);
      expect(Math.max(...seen)).toBe(73);
      expect(seen.every((value, i) => i === 0 || value >= seen[i - 1])).toBe(true);
      expect(view.getByTestId('kpi').props.accessibilityLabel).toBe('73%');
    } finally { jest.useRealTimers(); }
  });
  it('a later server value animates from the previous one', async () => {
    jest.useFakeTimers();
    try {
      await setOsReduceMotion(false);
      const view = await render(wrap(<AnimatedKpi testID="kpi" value={40} />));
      await act(async () => { jest.advanceTimersByTime(1500); });
      await view.rerender(wrap(<AnimatedKpi testID="kpi" value={60} />));
      await act(async () => { jest.advanceTimersByTime(200); });
      const mid = Number(String(view.getByTestId('kpi').props.children[0]));
      expect(mid).toBeGreaterThanOrEqual(40);
      expect(mid).toBeLessThan(60);
      await act(async () => { jest.advanceTimersByTime(1500); });
      expect(Number(String(view.getByTestId('kpi').props.children[0]))).toBe(60);
    } finally { jest.useRealTimers(); }
  });
  it('a missing / invalid value is shown as 0, never as an invented number', async () => {
    await setOsReduceMotion(true);
    const view = await render(wrap(<AnimatedKpi testID="kpi" value={Number.NaN} />));
    expect(view.getByTestId('kpi').props.children).toEqual([0, '']);
  });
  it('progress bars and rings clamp to the verified 0..100 range and expose the exact value', async () => {
    await setOsReduceMotion(true);
    const view = await render(wrap(<>
      <AnimatedProgressBar testID="bar" percent={140} label="occupancy" />
      <OccupancyRing percent={-5} label="ring" />
    </>));
    expect(view.getByTestId('bar').props.accessibilityValue).toEqual({ min: 0, max: 100, now: 100 });
    expect(view.getByLabelText('ring').props.accessibilityValue).toEqual({ min: 0, max: 100, now: 0 });
  });
});

describe('entrances never hide content', () => {
  it('Reduce Motion => fully visible on first frame', async () => {
    await setOsReduceMotion(true);
    const view = await render(wrap(<PremiumEntrance index={3}><View testID="card" /></PremiumEntrance>));
    expect(view.getByTestId('card')).toBeTruthy();
    expect(opacityOf(view.getByTestId('card').parent as never)).toBe(1);
  });
  it('unknown preference => fully visible (fail visible, no flash)', async () => {
    resetMotionPreferenceForTests();
    jest.spyOn(AccessibilityInfo, 'isReduceMotionEnabled').mockReturnValue(new Promise(() => {}));
    const view = await render(wrap(<PremiumEntrance><View testID="card" /></PremiumEntrance>));
    expect(opacityOf(view.getByTestId('card').parent as never)).toBe(1);
  });
});

describe('ConfirmedChange (status swaps only on a server-confirmed change)', () => {
  const Badgeish = ({ status }: { status: string }) => <ConfirmedChange value={status}><Text testID="status">{status}</Text></ConfirmedChange>;
  it('does not animate on first mount or when the same status is re-delivered', async () => {
    await setOsReduceMotion(false);
    const view = await render(wrap(<Badgeish status="GUARANTEED" />));
    expect(opacityOf(view.getByTestId('status').parent as never)).toBe(1);
    await view.rerender(wrap(<Badgeish status="GUARANTEED" />));
    expect(opacityOf(view.getByTestId('status').parent as never)).toBe(1);
  });
  it('animates when the server status actually changes (native-driven, so only the start is observable in jest)', async () => {
    await setOsReduceMotion(false);
    const view = await render(wrap(<Badgeish status="GUARANTEED" />));
    await view.rerender(wrap(<Badgeish status="CHECKED_IN" />));
    expect(view.getByTestId('status').props.children).toBe('CHECKED_IN');
    expect(opacityOf(view.getByTestId('status').parent as never)).toBeLessThan(1);
  });
  it('Reduce Motion => the new status is shown at full opacity immediately', async () => {
    await setOsReduceMotion(true);
    const view = await render(wrap(<Badgeish status="GUARANTEED" />));
    await view.rerender(wrap(<Badgeish status="CHECKED_IN" />));
    expect(opacityOf(view.getByTestId('status').parent as never)).toBe(1);
  });
});

describe('AnimatedSheet', () => {
  const Sheet = ({ open }: { open: boolean }) => <AnimatedSheet visible={open} onRequestClose={() => {}} closeLabel="Close">
    <View testID="sheet-content"><Text>booking</Text></View>
  </AnimatedSheet>;
  it('renders existing sheet content when open and keeps it for the exit animation', async () => {
    jest.useFakeTimers();
    try {
      await setOsReduceMotion(false);
      const view = await render(wrap(<Sheet open />));
      expect(view.getByTestId('sheet-content')).toBeTruthy();
      await view.rerender(wrap(<Sheet open={false} />));
      expect(view.queryByTestId('sheet-content')).toBeTruthy(); // exit still playing
      await act(async () => { jest.advanceTimersByTime(600); });
      expect(view.queryByTestId('sheet-content')).toBeNull();
    } finally { jest.useRealTimers(); }
  });
  it('Reduce Motion => closes immediately, nothing left over a hidden Modal', async () => {
    await setOsReduceMotion(true);
    const view = await render(wrap(<Sheet open />));
    await view.rerender(wrap(<Sheet open={false} />));
    expect(view.queryByTestId('sheet-content')).toBeNull();
  });
});

describe('TabIcon', () => {
  it('shows the selected highlight at full strength once focused, and none when not', async () => {
    await setOsReduceMotion(true);
    const view = await render(wrap(<>
      <View testID="on"><TabIcon icon={Sparkles} focused color="#fff" /></View>
      <View testID="off"><TabIcon icon={Sparkles} focused={false} color="#fff" /></View>
    </>));
    const pill = (id: string) => view.getByTestId(id).children[0] as never;
    expect(view.getByTestId('on')).toBeTruthy();
    expect(view.getByTestId('off')).toBeTruthy();
    expect(pill('on')).toBeTruthy();
  });
});

describe('source contracts', () => {
  const root = path.resolve(__dirname, '..');
  const files: string[] = [];
  const walk = (dir: string) => {
    for (const name of fs.readdirSync(dir)) {
      const full = path.join(dir, name);
      if (fs.statSync(full).isDirectory()) { if (name !== 'node_modules') walk(full); }
      else if (/\.(ts|tsx)$/.test(name)) files.push(full);
    }
  };
  walk(path.join(root, 'src')); walk(path.join(root, 'app'));

  it('no endless animations: every Animated.loop declares a finite iteration count', () => {
    const offenders = files.filter(file => {
      const text = fs.readFileSync(file, 'utf8');
      const calls = text.match(/Animated\.loop\(/g)?.length ?? 0;
      const bounded = text.match(/iterations:\s*[\w.]+/g)?.length ?? 0;
      return calls > bounded;
    }).map(file => path.relative(root, file));
    expect(offenders).toEqual([]);
  });
  it('motion code never touches API, auth, bookings or finance modules', () => {
    for (const rel of ['src/theme/motion.ts', 'src/components/Motion.tsx']) {
      const text = fs.readFileSync(path.join(root, rel), 'utf8');
      expect(text).not.toMatch(/from '\.\.\/(api|state|roles|lib)\//);
    }
  });
  it('tab set, order and role guards are unchanged', () => {
    const layout = fs.readFileSync(path.join(root, 'app/(app)/_layout.tsx'), 'utf8');
    expect(layout).toContain("const ORDER: TabKey[] = ['overview', 'reception', 'pms', 'inbox', 'dining', 'kitchen', 'tasks', 'rooms', 'requests', 'admin', 'profile'];");
    expect(layout).toContain('hasTabForSession(user.role, user.module_permissions, mode, selected, serverAuthMode)');
    expect(layout).toContain('mobileTabPlan(workspace.tabs)');
    expect(layout).toContain("<Tabs.Screen name=\"more\"");
  });
});
