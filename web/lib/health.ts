import { apiFetch } from './api';

export type ConnectorHealth = {
  source: string;
  state: 'ok' | 'degraded' | 'circuit_open';
  last_error?: string | null;
  failure_total?: number;
  remaining_cooldown?: number;
};

export type HealthIssue = {
  source: string;
  reason: string;
  operation?: string;
  failed?: number;
  error?: string;
  remaining_cooldown?: number;
};

export type HealthResponse = {
  status: string;
  ingestion?: {
    sources?: Record<
      string,
      {
        state?: string;
        last_error?: string | null;
        failure_total?: number;
        repeated_failure?: { operation: string; failed: number } | null;
        circuit?: { remaining_cooldown?: number };
        operations?: Record<string, { last_error?: string | null; failed?: number }>;
      }
    >;
    issues?: HealthIssue[];
  };
};

export async function fetchHealth() {
  return apiFetch<HealthResponse>('/health', {}, { isServer: false });
}

export function normalizeConnectorHealth(payload: HealthResponse): ConnectorHealth[] {
  const sources = payload.ingestion?.sources ?? {};
  const issues = payload.ingestion?.issues ?? [];
  return Object.entries(sources).map(([source, data]) => {
    const matchingIssue = issues.find((issue) => issue.source === source);
    return {
      source,
      state: (data.state as ConnectorHealth['state']) || 'ok',
      last_error: data.last_error ?? matchingIssue?.error,
      failure_total: data.failure_total,
      remaining_cooldown: data.circuit?.remaining_cooldown ?? matchingIssue?.remaining_cooldown,
    };
  });
}
