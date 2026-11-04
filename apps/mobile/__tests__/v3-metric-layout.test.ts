import { metricNeedsFullWidth } from '../src/theme/layout';

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
