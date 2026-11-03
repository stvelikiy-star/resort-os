import React from 'react';
import { Pressable, Text } from 'react-native';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import { ThemeProvider, useTheme, validTheme } from '../src/theme/ThemeProvider';
import { colors, motion, TOUCH } from '../src/theme/tokens';
import { cappedStagger } from '../src/theme/motion';
import { setItem } from '../src/lib/storage';

jest.mock('../src/lib/storage', () => ({
  getItem: jest.fn(async () => null),
  setItem: jest.fn(async () => {}),
}));

function luminance(color: string) {
  const rgb = color.match(/[a-f0-9]{2}/gi);
  if (!rgb || rgb.length !== 3) throw new Error('invalid RGB token');
  return rgb.map(x => {
    const v = parseInt(x, 16) / 255;
    return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  }).reduce((sum, value, i) => sum + [0.2126, 0.7152, 0.0722][i] * value, 0);
}
function contrast(a: string, b: string) {
  const x = luminance(a), y = luminance(b);
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
}
it('future luxury palette maintains WCAG AA text and primary action contrast in both themes', () => {
  for (const theme of ['light', 'dark'] as const) {
    const c = colors[theme];
    expect(contrast(c.text, c.bg)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(c.text, c.surface)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(c.textMuted, c.surface)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(c.primary, c.primarySoft)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(c.primaryText, c.primary)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(c.warning, c.warningSoft)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(c.danger, c.dangerSoft)).toBeGreaterThanOrEqual(4.5);
  }
});
it('motion presets are centralized and stagger is bounded', () => {
  expect(motion.press).toBeLessThanOrEqual(150);
  expect(motion.card).toBeLessThanOrEqual(400);
  expect(cappedStagger(-3)).toBe(0);
  expect(cappedStagger(300)).toBe(motion.maxStaggerCards * motion.cardStagger);
  expect(TOUCH).toBeGreaterThanOrEqual(44);
});
it('theme accepts only known stored choices', () => {
  expect(validTheme('system')).toBe(true);
  expect(validTheme('dark')).toBe(true);
  expect(validTheme('malicious')).toBe(false);
});
function Probe() {
  const { name, pref, setPref } = useTheme();
  return <>
    <Text testID="future-theme">{name}:{pref}</Text>
    <Pressable testID="future-theme-toggle" onPress={() => setPref('dark')}><Text>Dark</Text></Pressable>
  </>;
}
it('theme switches without remounting the route and persists preference', async () => {
  const result = render(<ThemeProvider initial="light"><Probe/></ThemeProvider>);
  expect(result.getByTestId('future-theme').props.children).toEqual(['light', ':', 'light']);
  fireEvent.press(result.getByTestId('future-theme-toggle'));
  await waitFor(() => expect(result.getByTestId('future-theme').props.children).toEqual(['dark', ':', 'dark']));
  expect(setItem).toHaveBeenCalledWith('marina.theme', 'dark');
});
