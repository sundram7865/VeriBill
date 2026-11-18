import { describe, expect, it } from 'vitest';
import { toPixels } from './bbox';
import { fieldLabel, groupFields, orderedFields } from './fields';
import { confidenceLevel, formatMoney, formatPercent, formatUsd } from './format';
import { actionFor } from './shortcuts';
import type { ExtractedField } from './types';

function field(path: string): ExtractedField {
  return { id: path, path, value: 'x', confidence: 1, page: 1, bbox: null, issues: [] };
}

describe('bbox', () => {
  it('scales normalised boxes to pixels with a small padding', () => {
    const box = toPixels([0.1, 0.2, 0.3, 0.25], 1000, 2000);
    expect(box.left).toBeCloseTo(98);
    expect(box.top).toBeCloseTo(398);
    expect(box.width).toBeCloseTo(204);
    expect(box.height).toBeCloseTo(104);
  });
});

describe('fields', () => {
  it('labels and groups fields in printed-invoice order', () => {
    const fields = [
      field('totals.grand_total'),
      field('line_items.1.rate'),
      field('header.invoice_number'),
      field('line_items.0.description'),
      field('header.supplier_name'),
      field('line_items.0.rate'),
    ];
    expect(groupFields(fields).map((g) => g.title)).toEqual([
      'Header',
      'Line 1',
      'Line 2',
      'Totals',
    ]);
    expect(orderedFields(fields).map((f) => f.path)).toEqual([
      'header.supplier_name',
      'header.invoice_number',
      'line_items.0.description',
      'line_items.0.rate',
      'line_items.1.rate',
      'totals.grand_total',
    ]);
    expect(fieldLabel('line_items.3.igst_amount')).toBe('IGST');
  });
});

describe('format', () => {
  it('formats rupees with Indian grouping and percentages', () => {
    expect(formatMoney(123456.5)).toBe('₹1,23,456.50');
    expect(formatMoney(null)).toBe('—');
    expect(formatPercent(0.9234)).toBe('92.3%');
    expect(formatUsd(0.00054)).toBe('$0.00054');
  });

  it('maps confidence to badge bands', () => {
    expect(confidenceLevel(0.95)).toBe('high');
    expect(confidenceLevel(0.75)).toBe('medium');
    expect(confidenceLevel(0.3)).toBe('low');
  });
});

describe('shortcuts', () => {
  const press = (key: string, inInput = false, ctrlKey = false) =>
    actionFor({ key, ctrlKey, metaKey: false, inInput });

  it('maps navigation keys outside inputs', () => {
    expect(press('j')).toBe('next');
    expect(press('ArrowUp')).toBe('previous');
    expect(press('e')).toBe('edit');
    expect(press('R')).toBe('reject');
    expect(press('r')).toBeNull(); // lower-case r is too easy to hit by accident
  });

  it('never steals letters while typing, but Ctrl+Enter and Esc still work', () => {
    expect(press('j', true)).toBeNull();
    expect(press('Enter', true, true)).toBe('approve');
    expect(press('Escape', true)).toBe('cancel');
  });
});
