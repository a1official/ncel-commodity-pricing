# Frontend Performance Day 1 Baseline

## Goals
- Capture initial frontend performance signals before optimization work.
- Add runtime visibility into API latency and payload size.
- Define budgets to validate progress in later days.

## Instrumentation Added
- Web Vitals logging (`LCP`, `INP`, `CLS`) via `PerformanceMonitor`.
- API timing and payload checks through `timedFetch`.
- Page load duration markers for:
  - `dashboard`
  - `marine`

## Budgets (Initial)
- Page load:
  - `dashboard`: `2500ms`
  - `marine`: `3000ms`
- API latency:
  - `default`: `1200ms`
  - `prices`: `1500ms`
  - `commodities`: `800ms`
  - `marineSummary`: `1200ms`
- Payload size:
  - `default`: `300KB`
  - `prices`: `450KB`
- Web Vitals:
  - `LCP <= 2500ms`
  - `INP <= 200ms`
  - `CLS <= 0.1`

## Runtime Output
- Console output tags:
  - `[perf][api][...]`
  - `[perf][page][...]`
  - `[perf][vital][...]`
- In-browser memory buffer:
  - `window.__NCEL_PERF_METRICS__`

## Usage
- Perf logging is enabled by default.
- To disable temporarily, set:
  - `NEXT_PUBLIC_ENABLE_PERF_LOGGING=false`
