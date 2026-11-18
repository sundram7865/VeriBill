export type NormalizedBox = [number, number, number, number];

export interface PixelBox {
  left: number;
  top: number;
  width: number;
  height: number;
}

const PADDING_PX = 2;

/** Boxes are stored as fractions of the page, so they scale with any rendered page size. */
export function toPixels(box: NormalizedBox, pageWidth: number, pageHeight: number): PixelBox {
  const [x0, y0, x1, y1] = box;
  return {
    left: Math.max(0, x0 * pageWidth - PADDING_PX),
    top: Math.max(0, y0 * pageHeight - PADDING_PX),
    width: (x1 - x0) * pageWidth + 2 * PADDING_PX,
    height: (y1 - y0) * pageHeight + 2 * PADDING_PX,
  };
}
