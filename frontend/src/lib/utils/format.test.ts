import { describe, it, expect } from 'vitest';
import { formatLatency } from './format';

describe('formatLatency', () => {
  it('formats milliseconds below 1000', () => {
    expect(formatLatency(42)).toBe('42ms');
    expect(formatLatency(0)).toBe('0ms');
    expect(formatLatency(999)).toBe('999ms');
  });

  it('rounds fractional milliseconds', () => {
    expect(formatLatency(42.7)).toBe('43ms');
    expect(formatLatency(0.4)).toBe('0ms');
  });

  it('formats values >= 1000 as seconds', () => {
    expect(formatLatency(1000)).toBe('1.00s');
    expect(formatLatency(1500)).toBe('1.50s');
    expect(formatLatency(2345)).toBe('2.35s');
    expect(formatLatency(10000)).toBe('10.00s');
  });
});
