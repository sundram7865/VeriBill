'use client';

import { useSearchParams } from 'next/navigation';
import { Suspense } from 'react';
import { AppShell } from '@/components/AppShell';
import { ReviewScreen } from '@/components/review/ReviewScreen';
import { EmptyState, Spinner } from '@/components/States';

// Static export has no dynamic routes, so the document id travels in the query string:
// /review?id=<documentId>. useSearchParams needs a Suspense boundary under static export.
function ReviewFromQuery() {
  const id = useSearchParams().get('id');
  if (!id)
    return (
      <EmptyState title="No document selected">
        Open a document from the list or the review queue.
      </EmptyState>
    );
  return <ReviewScreen key={id} documentId={id} />;
}

export default function ReviewPage() {
  return (
    <AppShell wide>
      <Suspense fallback={<Spinner />}>
        <ReviewFromQuery />
      </Suspense>
    </AppShell>
  );
}
