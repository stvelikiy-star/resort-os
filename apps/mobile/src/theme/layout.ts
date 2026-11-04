/** Pure presentation rule, not business data. Financial figures must remain legible on phones.
 * Full-width is reserved for compact devices, large system fonts and long formatted values.
 */
export function metricNeedsFullWidth(width: number, fontScale: number, value: string): boolean {
  const compact = !Number.isFinite(width) || width < 350;
  const enlarged = !Number.isFinite(fontScale) || fontScale > 1.5;
  const longFigure = value.trim().length > 10;
  return compact || enlarged || longFigure;
}

/** The product is a mobile app. On desktop Expo Web, display a mobile-sized preview,
 * but keep the native Android/iOS and small Web viewport fully fluid. */
export function shouldFrameMobileWeb(platform: string, viewportWidth: number): boolean {
  return platform === 'web' && Number.isFinite(viewportWidth) && viewportWidth >= 700;
}

export const WEB_MOBILE_PREVIEW_WIDTH = 440;
