'use client';

import { useEffect, useRef } from 'react';
import { actionFor, type ReviewAction } from '@/lib/shortcuts';

/** Global key handler for the review screen; the mapping itself lives in lib/shortcuts.ts. */
export function useReviewKeyboard(
  onAction: (action: ReviewAction) => void,
  enabled: boolean,
): void {
  // Keep the latest callback without re-registering the window listener on every render.
  const handler = useRef(onAction);
  useEffect(() => {
    handler.current = onAction;
  });

  useEffect(() => {
    if (!enabled) return;
    function onKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const inInput = Boolean(
        target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA'),
      );
      const action = actionFor({
        key: event.key,
        ctrlKey: event.ctrlKey,
        metaKey: event.metaKey,
        inInput,
      });
      if (!action) return;
      event.preventDefault();
      if (action === 'cancel' && inInput) target?.blur();
      handler.current(action);
    }
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [enabled]);
}
