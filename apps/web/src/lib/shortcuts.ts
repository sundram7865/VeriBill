export type ReviewAction = 'next' | 'previous' | 'edit' | 'cancel' | 'approve' | 'reject' | 'help';

export interface KeyInput {
  key: string;
  ctrlKey: boolean;
  metaKey: boolean;
  inInput: boolean; // focus is in a text field
}

export const SHORTCUTS: Array<{ keys: string; action: string }> = [
  { keys: 'j / ↓', action: 'Next field' },
  { keys: 'k / ↑', action: 'Previous field' },
  { keys: 'e / Enter', action: 'Edit selected field' },
  { keys: 'Esc', action: 'Stop editing' },
  { keys: 'Ctrl+Enter', action: 'Approve (with your corrections)' },
  { keys: 'Shift+R', action: 'Reject document' },
  { keys: '?', action: 'Show shortcuts' },
];

/**
 * Maps a key press to a review action. Plain letters are ignored while typing in a field, so
 * editing a value never triggers navigation; Ctrl+Enter and Esc work everywhere.
 */
export function actionFor(input: KeyInput): ReviewAction | null {
  const mod = input.ctrlKey || input.metaKey;
  if (mod && input.key === 'Enter') return 'approve';
  if (input.key === 'Escape') return 'cancel';
  if (input.inInput) return null;
  switch (input.key) {
    case 'j':
    case 'ArrowDown':
      return 'next';
    case 'k':
    case 'ArrowUp':
      return 'previous';
    case 'e':
    case 'Enter':
      return 'edit';
    case 'R':
      return 'reject';
    case '?':
      return 'help';
    default:
      return null;
  }
}
