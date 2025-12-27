// Ops endpoint helpers for queue health dashboards.
import { apiFetch } from './api';

export type QueueSnapshot = {
  status: string;
  queues: {
    name: string;
    size: number;
    deferred: number;
    scheduled: number;
    started: number;
    failed: number;
  }[];
  workers: { name: string; state: string; queues: string[]; current_job_id?: string | null }[];
  scheduler?: { scheduled_jobs?: number | null; healthy?: boolean };
  warnings?: string[];
  checked_at?: string;
};

export async function fetchQueueHealth() {
  // Fetch queue health for the ops panel.
  return apiFetch<QueueSnapshot>('/ops/queues', {}, { isServer: false });
}
