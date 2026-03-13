import { API_V1_URL } from './config';

export async function fetchCommodities() {
    const response = await fetch(`${API_V1_URL}/commodities`);
    if (!response.ok) {
        throw new Error('Failed to fetch commodities');
    }
    return response.json();
}

export async function fetchMarkets() {
    const response = await fetch(`${API_V1_URL}/markets`);
    if (!response.ok) {
        throw new Error('Failed to fetch markets');
    }
    return response.json();
}

export async function fetchPrices(params: {
    commodity_id?: number;
    variety_id?: number;
    market_id?: number;
    commodity_name?: string;
    variety_name?: string;
    source_name?: string;
    category?: string;
    start_date?: string;
    end_date?: string;
    limit?: number;
}) {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
        if (value) query.append(key, value.toString());
    });

    const response = await fetch(`${API_V1_URL}/prices?${query.toString()}`);
    if (!response.ok) {
        throw new Error('Failed to fetch prices');
    }
    return response.json();
}

export async function fetchDailyAverage(commodityId: number) {
    const response = await fetch(`${API_V1_URL}/insights/daily-average?commodity_id=${commodityId}`);
    if (!response.ok) {
        throw new Error('Failed to fetch daily average');
    }
    return response.json();
}

export async function fetchPriceRange(commodityId: number, days: number = 30) {
    const response = await fetch(`${API_V1_URL}/analytics/price-range?commodity_id=${commodityId}&days=${days}`);
    if (!response.ok) {
        throw new Error('Failed to fetch price range');
    }
    return response.json();
}

export async function fetchSourceComparison(commodityId: number, days: number = 30) {
    const response = await fetch(`${API_V1_URL}/analytics/source-comparison?commodity_id=${commodityId}&days=${days}`);
    if (!response.ok) {
        throw new Error('Failed to fetch source comparison');
    }
    return response.json();
}

export async function triggerIngestion() {
    const response = await fetch(`${API_V1_URL}/ingest`, {
        method: 'POST',
    });
    if (!response.ok) {
        throw new Error('Failed to trigger ingestion');
    }
    return response.json();
}

export async function fetchHybridForecast(commodityId: number) {
    const response = await fetch(`${API_V1_URL}/forecast/${commodityId}`);
    if (!response.ok) {
        throw new Error('Forecast discovery failed');
    }
    return response.json();
}

export async function fetchMpedaExportData(params?: {
    commodity?: string;
    year?: string;
    limit?: number;
}) {
    const query = new URLSearchParams();
    if (params) {
        Object.entries(params).forEach(([key, value]) => {
            if (value) query.append(key, value.toString());
        });
    }
    const response = await fetch(`${API_V1_URL}/mpeda/export-data?${query.toString()}`);
    if (!response.ok) {
        throw new Error('Failed to fetch MPEDA data');
    }
    return response.json();
}

export async function refreshMpedaData() {
    const response = await fetch(`${API_V1_URL}/mpeda/refresh`, {
        method: 'POST',
    });
    if (!response.ok) {
        throw new Error('Failed to refresh MPEDA data');
    }
    return response.json();
}

export async function fetchMarineStates() {
    const response = await fetch(`${API_V1_URL}/marine/states`);
    if (!response.ok) {
        throw new Error('Failed to fetch marine states');
    }
    return response.json();
}

export async function fetchMarineSummary() {
    const response = await fetch(`${API_V1_URL}/marine/summary`);
    if (!response.ok) {
        throw new Error('Failed to fetch marine summary');
    }
    return response.json();
}
