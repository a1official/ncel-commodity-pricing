import { PERFORMANCE_BUDGETS, type ApiBudgetKey, type PageBudgetKey } from './performance-budgets';

type WebVitalMetric = {
  id: string;
  name: string;
  value: number;
  rating?: 'good' | 'needs-improvement' | 'poor';
  navigationType?: string;
};

type ApiMetricPayload = {
  endpoint: string;
  durationMs: number;
  status: number;
  ok: boolean;
  payloadKb?: number;
};

declare global {
  interface Window {
    __NCEL_PERF_METRICS__?: {
      api: ApiMetricPayload[];
      webVitals: WebVitalMetric[];
      pages: Array<{ page: string; durationMs: number; measuredAt: string }>;
    };
  }
}

const PERF_FLAG = process.env.NEXT_PUBLIC_ENABLE_PERF_LOGGING;
export const isPerfLoggingEnabled = PERF_FLAG !== 'false';
let pageLoadSequence = 0;

export type PageLoadToken = {
  page: PageBudgetKey;
  startMark: string;
  endMark: string;
  measureName: string;
};

function pushMetric<T extends keyof NonNullable<Window['__NCEL_PERF_METRICS__']>>(
  group: T,
  value: NonNullable<Window['__NCEL_PERF_METRICS__']>[T][number],
) {
  if (typeof window === 'undefined') return;
  if (!window.__NCEL_PERF_METRICS__) {
    window.__NCEL_PERF_METRICS__ = {
      api: [],
      webVitals: [],
      pages: [],
    };
  }
  window.__NCEL_PERF_METRICS__[group].push(value as never);
}

function toPayloadKb(contentLengthHeader: string | null): number | undefined {
  if (!contentLengthHeader) return undefined;
  const bytes = Number(contentLengthHeader);
  if (Number.isNaN(bytes) || bytes <= 0) return undefined;
  return Number((bytes / 1024).toFixed(2));
}

export async function timedFetch(
  url: string,
  init?: RequestInit,
  options?: { endpoint?: string; budgetKey?: ApiBudgetKey },
): Promise<Response> {
  const startedAt = performance.now();
  const response = await fetch(url, init);
  const durationMs = Number((performance.now() - startedAt).toFixed(1));

  const endpoint = options?.endpoint ?? url;
  const payloadKb = toPayloadKb(response.headers.get('content-length'));
  const budgetMs = PERFORMANCE_BUDGETS.apiResponseMs[options?.budgetKey ?? 'default'];
  const payloadBudgetKb = PERFORMANCE_BUDGETS.payloadKb[options?.budgetKey ?? 'default'];

  if (isPerfLoggingEnabled) {
    const payload: ApiMetricPayload = {
      endpoint,
      durationMs,
      status: response.status,
      ok: response.ok,
      payloadKb,
    };
    pushMetric('api', payload);

    const speedTag = durationMs > budgetMs ? 'BUDGET_EXCEEDED' : 'OK';
    const payloadTag = payloadKb !== undefined && payloadKb > payloadBudgetKb ? 'PAYLOAD_HIGH' : 'PAYLOAD_OK';

    console.info(
      `[perf][api][${speedTag}][${payloadTag}] ${endpoint} ${durationMs}ms status=${response.status} payloadKb=${payloadKb ?? 'n/a'}`,
    );
  }

  return response;
}

export function markPageLoadStart(page: PageBudgetKey): PageLoadToken | null {
  if (typeof performance === 'undefined') return null;
  pageLoadSequence += 1;
  const suffix = `${Date.now()}:${pageLoadSequence}`;
  const token: PageLoadToken = {
    page,
    startMark: `ncel:${page}:start:${suffix}`,
    endMark: `ncel:${page}:end:${suffix}`,
    measureName: `ncel:${page}:load:${suffix}`,
  };
  performance.mark(token.startMark);
  return token;
}

export function markPageLoadEnd(token: PageLoadToken | null) {
  if (typeof performance === 'undefined') return;
  if (!token) return;
  const { page, startMark, endMark, measureName } = token;
  const hasStart = performance.getEntriesByName(startMark).length > 0;
  if (!hasStart) return;

  performance.mark(endMark);
  performance.measure(measureName, startMark, endMark);
  const [entry] = performance.getEntriesByName(measureName).slice(-1);
  if (!entry) return;

  const durationMs = Number(entry.duration.toFixed(1));
  const budgetMs = PERFORMANCE_BUDGETS.pageLoadMs[page];
  pushMetric('pages', { page, durationMs, measuredAt: new Date().toISOString() });

  if (isPerfLoggingEnabled) {
    const tag = durationMs > budgetMs ? 'BUDGET_EXCEEDED' : 'OK';
    console.info(`[perf][page][${tag}] ${page} ${durationMs}ms (budget=${budgetMs}ms)`);
  }

  performance.clearMarks(startMark);
  performance.clearMarks(endMark);
  performance.clearMeasures(measureName);
}

export function reportWebVital(metric: WebVitalMetric) {
  if (!isPerfLoggingEnabled) return;
  pushMetric('webVitals', metric);

  let budget: number | undefined;
  if (metric.name === 'LCP') budget = PERFORMANCE_BUDGETS.webVitals.lcp;
  if (metric.name === 'INP') budget = PERFORMANCE_BUDGETS.webVitals.inp;
  if (metric.name === 'CLS') budget = PERFORMANCE_BUDGETS.webVitals.cls;

  const isBudgetExceeded = budget !== undefined ? metric.value > budget : false;
  const tag = isBudgetExceeded ? 'BUDGET_EXCEEDED' : 'OK';
  console.info(`[perf][vital][${tag}] ${metric.name}=${metric.value} rating=${metric.rating ?? 'n/a'}`);
}
