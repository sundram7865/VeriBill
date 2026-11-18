'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch, apiJson } from '@/lib/api';
import type {
  DocumentDetail,
  DocumentList,
  DocumentStatus,
  Metrics,
  ReviewTaskItem,
  UploadResult,
} from '@/lib/types';

const IN_FLIGHT: DocumentStatus[] = ['uploaded', 'processing'];
const POLL_MS = 2000;

export function useDocuments(status: DocumentStatus | 'all', page: number) {
  const params = new URLSearchParams({ page: String(page), pageSize: '25' });
  if (status !== 'all') params.set('status', status);
  return useQuery({
    queryKey: ['documents', status, page],
    queryFn: () => apiJson<DocumentList>(`/documents?${params}`),
    // Live status: poll while anything on screen is still being processed.
    refetchInterval: (query) =>
      query.state.data?.items.some((d) => IN_FLIGHT.includes(d.status)) ? POLL_MS : false,
  });
}

export function useDocument(id: string | null) {
  return useQuery({
    queryKey: ['document', id],
    queryFn: () => apiJson<DocumentDetail>(`/documents/${id}`),
    enabled: Boolean(id),
    refetchInterval: (query) =>
      query.state.data && IN_FLIGHT.includes(query.state.data.document.status) ? POLL_MS : false,
  });
}

/** The original file bytes, fetched with auth (the browser never sees a storage URL). */
export function useDocumentFile(id: string | null) {
  return useQuery({
    queryKey: ['document-file', id],
    queryFn: async () => (await apiFetch(`/documents/${id}/file`)).arrayBuffer(),
    enabled: Boolean(id),
    staleTime: Infinity,
  });
}

export function useReviewTasks() {
  return useQuery({
    queryKey: ['review-tasks'],
    queryFn: () => apiJson<{ items: ReviewTaskItem[] }>('/review-tasks?status=open&limit=200'),
    refetchInterval: 10_000,
  });
}

export function useMetrics(days: number) {
  return useQuery({
    queryKey: ['metrics', days],
    queryFn: () => apiJson<Metrics>(`/metrics?days=${days}`),
  });
}

export function useUpload() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (files: File[]) => {
      const form = new FormData();
      files.forEach((file) => form.append('files', file));
      // 422 = every file was rejected; the body still says why for each one.
      const res = await apiFetch('/documents', { method: 'POST', body: form }, [422]);
      return (await res.json()) as UploadResult;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['documents'] }),
  });
}

export interface CorrectionDraft {
  fieldPath: string;
  after: string | null;
}

export function useSubmitReview() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: {
      taskId: string;
      action: 'approve' | 'reject';
      corrections: CorrectionDraft[];
    }) =>
      apiJson<{ outcome: string; corrections: number }>(`/review-tasks/${input.taskId}/submit`, {
        method: 'POST',
        json: { action: input.action, corrections: input.corrections },
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['review-tasks'] });
      void queryClient.invalidateQueries({ queryKey: ['documents'] });
      void queryClient.invalidateQueries({ queryKey: ['document'] });
      void queryClient.invalidateQueries({ queryKey: ['metrics'] });
    },
  });
}
