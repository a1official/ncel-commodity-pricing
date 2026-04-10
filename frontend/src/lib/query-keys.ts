export const queryKeys = {
  commodities: ['commodities'] as const,
  prices: (params: Record<string, string | number | undefined>) => ['prices', params] as const,
  pricesPage: (params: Record<string, string | number | undefined>) => ['prices', 'page', params] as const,
  priceSummary: (params: Record<string, string | number | undefined>) => ['prices', 'summary', params] as const,
  priceTimeseries: (params: Record<string, string | number | undefined>) => ['prices', 'timeseries', params] as const,
  marineSummary: ['marine', 'summary'] as const,
  marineStates: ['marine', 'states'] as const,
  mpedaExportData: (params: Record<string, string | number | undefined>) => ['mpeda', 'export-data', params] as const,
};
