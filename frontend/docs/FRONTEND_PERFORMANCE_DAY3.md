# Frontend Performance Day 3

## Plan
- Migrate heavy client pages from ad-hoc `useEffect` fetching to query-managed data flow.
- Use shared query keys and AbortSignal-aware API functions for cancellation support.
- Keep expensive transforms in `useMemo` to reduce repeated render work.
- Preserve page-load instrumentation from Day 1.

## Implemented

### 1. Dashboard (`/`)
- Replaced manual fetch lifecycle state with `useQuery` for:
  - commodities
  - prices (filter-aware query key)
- Removed manual loading/data `setState` paths for fetched datasets.
- Kept derived chart and stats calculations memoized.
- Retained page-load markers with token-safe start/end tracking.

### 2. Marine (`/marine`)
- Replaced manual dual-loader `useEffect` flow with `useQuery` for:
  - commodities
  - marine prices
  - marine summary
  - marine states
  - MPEDA export data
- Continued to support separate base-page loading and MPEDA-section loading.
- Memoized derived collections and chart inputs.
- Retained page-load markers with token-safe start/end tracking.

### 3. Shared Query Infrastructure (already wired Day 2, now actively used)
- `QueryProvider` in root layout
- `queryKeys` for stable cache identity
- API layer supports `signal` and dedupe/cache behavior

## Result
- Cleaner data flow with fewer manual loading states.
- Better request reuse and cancellation under fast filter changes.
- Reduced recomputation churn by isolating derived data in memoized selectors.
