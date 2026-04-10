import { API_V1_URL } from './config';
import { timedFetch } from './performance';

type RequestOptions = {
    signal?: AbortSignal;
    bypassCache?: boolean;
};

export type PriceQueryParams = {
    commodity_id?: number;
    variety_id?: number;
    market_id?: number;
    commodity_name?: string;
    variety_name?: string;
    source_name?: string;
    category?: string;
    start_date?: string;
    end_date?: string;
    skip?: number;
    limit?: number;
};

export type ManualPriceUpdatePayload = {
    date: string;
    commodity_id: number;
    market_id: number;
    modal_price: number;
    min_price?: number;
    max_price?: number;
    arrival_quantity?: number;
    unit?: string;
};

type CacheEntry = {
    data: unknown;
    expiresAt: number;
};

const responseCache = new Map<string, CacheEntry>();
const inFlightRequests = new Map<string, Promise<unknown>>();

function toQueryString(params?: Record<string, string | number | undefined>) {
    if (!params) return '';
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
            query.append(key, value.toString());
        }
    });
    return query.toString();
}

function withQuery(path: string, params?: Record<string, string | number | undefined>) {
    const query = toQueryString(params);
    return query ? `${path}?${query}` : path;
}

function pickApiBudgetKey(endpoint: string): 'default' | 'prices' | 'marineSummary' | 'commodities' {
    if (endpoint.startsWith('/prices')) return 'prices';
    if (endpoint.startsWith('/marine/summary')) return 'marineSummary';
    if (endpoint.startsWith('/commodities')) return 'commodities';
    return 'default';
}

async function requestJson(endpoint: string, init?: RequestInit) {
    const method = (init?.method ?? 'GET').toUpperCase();
    const cacheKey = `${method}:${endpoint}`;
    const bypassCache = (init as RequestInit & { bypassCache?: boolean } | undefined)?.bypassCache ?? false;
    const isCacheableGet = method === 'GET' && !bypassCache;

    if (isCacheableGet) {
        const existing = responseCache.get(cacheKey);
        if (existing && existing.expiresAt > Date.now()) {
            return existing.data;
        }
        const pending = inFlightRequests.get(cacheKey);
        if (pending) {
            return pending;
        }
    }

    const requestPromise = (async () => {
        const response = await timedFetch(`${API_V1_URL}${endpoint}`, init, {
            endpoint,
            budgetKey: pickApiBudgetKey(endpoint),
        });
        if (!response.ok) {
            throw new Error(`API request failed (${response.status}) for ${endpoint}`);
        }
        const data = await response.json();

        if (isCacheableGet) {
            const ttlMs = getCacheTtlMs(endpoint);
            responseCache.set(cacheKey, { data, expiresAt: Date.now() + ttlMs });
        }
        return data;
    })();

    if (isCacheableGet) {
        inFlightRequests.set(cacheKey, requestPromise);
    }

    try {
        return await requestPromise;
    } finally {
        inFlightRequests.delete(cacheKey);
    }
}

function getCacheTtlMs(endpoint: string): number {
    if (endpoint.startsWith('/prices')) return 30 * 1000;
    if (endpoint.startsWith('/marine/summary')) return 2 * 60 * 1000;
    if (endpoint.startsWith('/marine/states')) return 5 * 60 * 1000;
    if (endpoint.startsWith('/commodities')) return 10 * 60 * 1000;
    return 60 * 1000;
}

function withRequestOptions(options?: RequestOptions): RequestInit {
    return {
        signal: options?.signal,
        bypassCache: options?.bypassCache,
    } as RequestInit;
}

export function clearApiResponseCache() {
    responseCache.clear();
    inFlightRequests.clear();
}

export async function fetchCommodities(options?: RequestOptions) {
    return requestJson('/commodities', withRequestOptions(options));
}

export async function fetchCommoditiesOverview(options?: RequestOptions) {
    return requestJson('/commodities/overview', withRequestOptions(options));
}

export async function fetchMarkets(options?: RequestOptions) {
    return requestJson('/markets', withRequestOptions(options));
}

export async function fetchPrices(params: PriceQueryParams, options?: RequestOptions) {
    return requestJson(withQuery('/prices', params), withRequestOptions(options));
}

export async function upsertManualPrice(payload: ManualPriceUpdatePayload, options?: RequestOptions) {
    return requestJson('/prices/manual', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
        signal: options?.signal,
    });
}

export async function deleteManualPrice(recordId: string, options?: RequestOptions) {
    return requestJson(`/prices/manual/${recordId}`, {
        method: 'DELETE',
        signal: options?.signal,
    });
}

export async function uploadManualPriceSheet(commodityId: number, file: File, options?: RequestOptions) {
    const formData = new FormData();
    formData.append('file', file);

    return requestJson(`/prices/manual/bulk?commodity_id=${commodityId}`, {
        method: 'POST',
        body: formData,
        signal: options?.signal,
    });
}

export async function fetchPricesPage(params: PriceQueryParams, options?: RequestOptions) {
    return requestJson(withQuery('/prices/page', params), withRequestOptions(options));
}

export async function fetchPriceSummary(params: PriceQueryParams, options?: RequestOptions) {
    return requestJson(withQuery('/prices/summary', params), withRequestOptions(options));
}

export async function fetchPriceTimeseries(params?: PriceQueryParams & { days?: number }, options?: RequestOptions) {
    return requestJson(withQuery('/prices/timeseries', params), withRequestOptions(options));
}

export async function fetchDailyAverage(commodityId: number) {
    return requestJson(withQuery('/insights/daily-average', { commodity_id: commodityId }));
}

export async function fetchPriceRange(commodityId: number, days: number = 30) {
    return requestJson(withQuery('/analytics/price-range', { commodity_id: commodityId, days }));
}

export async function fetchSourceComparison(commodityId: number, days: number = 30) {
    return requestJson(withQuery('/analytics/source-comparison', { commodity_id: commodityId, days }));
}

export async function triggerIngestion() {
    return requestJson('/ingest', { method: 'POST' });
}

export async function fetchHybridForecast(commodityId: number) {
    return requestJson(`/forecast/${commodityId}`);
}

export async function fetchWheatMonteCarloForecast(params?: {
    days?: number;
    simulations?: number;
}) {
    return requestJson(withQuery('/forecast/wheat/monte-carlo', params));
}

export async function fetchWheatMlForecast(params?: {
    days?: number;
    simulations?: number;
}) {
    return requestJson(withQuery('/forecast/wheat/ml', params));
}

export async function fetchWheatHistory(params?: {
    days?: number;
}) {
    return requestJson(withQuery('/forecast/wheat/history', params));
}

export async function fetchRiceMlForecast(params?: {
    days?: number;
    simulations?: number;
}) {
    return requestJson(withQuery('/forecast/rice/ml', params));
}

export async function fetchRiceHistory(params?: {
    days?: number;
}) {
    return requestJson(withQuery('/forecast/rice/history', params));
}

export async function fetchMaizeMlForecast(params?: {
    days?: number;
    simulations?: number;
}) {
    return requestJson(withQuery('/forecast/maize/ml', params));
}

export async function fetchMaizeHistory(params?: {
    days?: number;
}) {
    return requestJson(withQuery('/forecast/maize/history', params));
}

export async function fetchMpedaExportData(params?: {
    commodity?: string;
    year?: string;
    limit?: number;
}, options?: RequestOptions) {
    return requestJson(withQuery('/mpeda/export-data', params), withRequestOptions(options));
}

export async function refreshMpedaData() {
    return requestJson('/mpeda/refresh', { method: 'POST' });
}

export async function fetchMarineStates(options?: RequestOptions) {
    return requestJson('/marine/states', withRequestOptions(options));
}

export async function fetchMarineSummary(options?: RequestOptions) {
    return requestJson('/marine/summary', withRequestOptions(options));
}

export async function fetchTerminalSummary(commodityTerms: string[]) {
    const query = new URLSearchParams();
    commodityTerms.forEach((term) => {
        if (term) query.append('commodity_terms', term);
    });

    return requestJson(`/analytics/terminal-summary?${query.toString()}`);
}

export async function fetchSupplyDemandAnalytics(params?: {
    crop?: string;
}) {
    return requestJson(withQuery('/analytics/supply-demand', params));
}

export async function fetchSupplyDemandHistory(params?: {
    crop?: string;
}) {
    return requestJson(withQuery('/analytics/supply-demand-history', params));
}

export async function fetchAnalyticsDashboard(params?: {
    commodity?: string;
}) {
    return requestJson(withQuery('/analytics/dashboard', params));
}
