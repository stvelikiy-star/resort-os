import { occupancyProgress } from '../src/components/OwnerControlDashboard';

describe('owner dashboard motion inputs', () => {
  it('keeps verified occupancy within the progressbar contract', () => {
    expect(occupancyProgress(73.4)).toBe(73.4);
    expect(occupancyProgress(-1)).toBe(0);
    expect(occupancyProgress(101)).toBe(100);
    expect(occupancyProgress(Number.NaN)).toBe(0);
  });
});
