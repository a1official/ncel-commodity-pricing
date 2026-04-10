# Frontend Performance Day 2

## Implemented
- Added shared query foundation with `@tanstack/react-query` provider in app layout.
- Upgraded API client to include:
  - In-flight request deduplication for identical `GET` calls.
  - In-memory response cache with endpoint-specific TTL.
  - Optional request cancelation support via `AbortSignal`.
  - `clearApiResponseCache()` utility for forced refresh scenarios.

## Cache TTLs
- `/commodities`: 10 minutes
- `/marine/states`: 5 minutes
- `/marine/summary`: 2 minutes
- `/prices`: 30 seconds
- Other `GET`: 60 seconds

## Notes
- Deduplication prevents duplicate parallel calls from different components.
- This is additive and backward-compatible with existing page code.
- Next step is route-by-route migration to query hooks (`useQuery`) for stale-while-revalidate UX and finer-grained refetch controls.
