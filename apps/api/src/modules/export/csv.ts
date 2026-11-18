export type Cell = string | number | null | undefined;

/**
 * One CSV cell. Text that starts with = + - @ is prefixed with ' so spreadsheet apps do not
 * run it as a formula (CSV injection). Numbers are written as-is, so -0.40 stays a number.
 */
export function csvCell(value: Cell): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'number') return Number.isFinite(value) ? String(value) : '';
  let text = value;
  if (/^[=+\-@\t\r]/.test(text)) text = `'${text}`;
  return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

export function csvLine(cells: Cell[]): string {
  return cells.map(csvCell).join(',');
}
