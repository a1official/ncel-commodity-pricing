export const PERFORMANCE_BUDGETS = {
  // Keep homepage quick even with market summaries.
  pageLoadMs: {
    dashboard: 2500,
    marine: 3000,
  },
  apiResponseMs: {
    default: 1200,
    prices: 1500,
    marineSummary: 1200,
    commodities: 800,
  },
  payloadKb: {
    default: 300,
    prices: 450,
  },
  webVitals: {
    lcp: 2500,
    inp: 200,
    cls: 0.1,
  },
} as const;

export type PageBudgetKey = keyof typeof PERFORMANCE_BUDGETS.pageLoadMs;
export type ApiBudgetKey = keyof typeof PERFORMANCE_BUDGETS.apiResponseMs;
