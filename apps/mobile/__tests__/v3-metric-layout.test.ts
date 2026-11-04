import { metricNeedsFullWidth, shouldFrameMobileWeb, WEB_MOBILE_PREVIEW_WIDTH } from '../src/theme/layout';

describe('FUTURE LUXURY V3 verified KPI presentation', () => {
  it('keeps long KGS figures legible without shrinking to tiny double-column text', () => {
    expect(metricNeedsFullWidth(375, 1, '1 250 000 KGS')).toBe(true);
    expect(metricNeedsFullWidth(430, 1, '123 456 KGS')).toBe(true);
    expect(metricNeedsFullWidth(430, 1, '72%')).toBe(false);
  });
  it('adapts to compact and large-font devices', () => {
    expect(metricNeedsFullWidth(320, 1, '5')).toBe(true);
    expect(metricNeedsFullWidth(375, 1.6, '5')).toBe(true);
    expect(metricNeedsFullWidth(430, 1, '5')).toBe(false);
  });
});

describe('desktop Expo Web previews remain mobile-sized', () => {
  it('centers a bounded preview only for desktop-width Web', () => {
    expect(shouldFrameMobileWeb('web', 1728)).toBe(true);
    expect(shouldFrameMobileWeb('web', 1024)).toBe(true);
    expect(WEB_MOBILE_PREVIEW_WIDTH).toBeLessThanOrEqual(460);
  });
  it('never constrains native phones or a small browser viewport', () => {
    expect(shouldFrameMobileWeb('web', 375)).toBe(false);
    expect(shouldFrameMobileWeb('web', 640)).toBe(false);
    expect(shouldFrameMobileWeb('android', 1728)).toBe(false);
    expect(shouldFrameMobileWeb('ios', 1024)).toBe(false);
  });
});
