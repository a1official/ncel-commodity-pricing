const API_URL = 'http://localhost:8000/api/v1';

export async function fetchCommodities() {
    const response = await fetch(`${API_URL}/commodities`);
    if (!response.ok) {
        throw new Error('Failed to fetch commodities');
    }
    return response.json();
}

export async function fetchMarkets() {
    const response = await fetch(`${API_URL}/markets`);
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
    start_date?: string;
    end_date?: string;
}) {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
        if (value) query.append(key, value.toString());
    });

    const response = await fetch(`${API_URL}/prices?${query.toString()}`);
    if (!response.ok) {
        throw new Error('Failed to fetch prices');
    }
    return response.json();
}

export async function fetchDailyAverage(commodityId: number) {
    const response = await fetch(`${API_URL}/insights/daily-average?commodity_id=${commodityId}`);
    if (!response.ok) {
        throw new Error('Failed to fetch daily average');
    }
    return response.json();
}

export async function triggerIngestion() {
    const response = await fetch(`${API_URL}/ingest`, {
        method: 'POST',
    });
    if (!response.ok) {
        throw new Error('Failed to trigger ingestion');
    }
    return response.json();
}

export async function fetchHybridForecast(commodityId: number) {
    const response = await fetch(`${API_URL}/forecast/${commodityId}`);
    if (!response.ok) {
        throw new Error('Forecast discovery failed');
    }
    return response.json();
}
