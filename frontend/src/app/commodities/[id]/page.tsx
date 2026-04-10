"use client";

import React, { useState, useEffect, useCallback } from 'react';
import {
    LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, ComposedChart
} from 'recharts';
import {
    ArrowLeft, Download, Filter, Share2, Info, MapPin, Calendar, TrendingUp, Package, Layers, AlertTriangle, Loader2, Upload, Trash2
} from 'lucide-react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { fetchCommodities, fetchPrices, fetchDailyAverage, upsertManualPrice, uploadManualPriceSheet, deleteManualPrice, clearApiResponseCache } from '@/lib/api';

export default function CommodityDetail({ params }: { params: { id: string } }) {
    const [activeUpdatePanel, setActiveUpdatePanel] = useState<'manual' | 'sheet' | null>(null);
    const [commodity, setCommodity] = useState<any>(null);
    const [prices, setPrices] = useState<any[]>([]);
    const [average, setAverage] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [activeSource, setActiveSource] = useState('All Sources');
    const [savingManualPrice, setSavingManualPrice] = useState(false);
    const [manualPriceError, setManualPriceError] = useState<string | null>(null);
    const [manualPriceSuccess, setManualPriceSuccess] = useState<string | null>(null);
    const [uploadingSheet, setUploadingSheet] = useState(false);
    const [sheetUploadError, setSheetUploadError] = useState<string | null>(null);
    const [sheetUploadSuccess, setSheetUploadSuccess] = useState<string | null>(null);
    const [sheetFile, setSheetFile] = useState<File | null>(null);
    const [deletingRecordId, setDeletingRecordId] = useState<string | null>(null);
    const [manualPriceForm, setManualPriceForm] = useState({
        date: new Date().toISOString().slice(0, 10),
        market_id: '',
        modal_price: '',
        min_price: '',
        max_price: '',
        arrival_quantity: '0',
        unit: 'QUINTAL',
    });

    const sources = ['All Sources', 'AGMARKNET', 'NCEL', 'USDA', 'FAO', 'APEDA', 'MPEDA', 'NCDEX', 'MCX'];

    const loadData = useCallback(async () => {
        try {
            setLoading(true);
            const [allCommodities, dailyAvg] = await Promise.all([
                fetchCommodities(),
                fetchDailyAverage(parseInt(params.id))
            ]);

            const current = allCommodities.find((c: any) => c.id.toString() === params.id);
            if (!current) throw new Error('Commodity not found in active registries.');

            setCommodity(current);
            setAverage(dailyAvg);

            let params_api: any = { commodity_id: parseInt(params.id) };

            if (activeSource === 'FAO') {
                params_api = { commodity_name: 'Food Price Index' };
            } else if (activeSource !== 'All Sources') {
                params_api.source_name = activeSource;
            }

            const history = await fetchPrices(params_api);
            setPrices(history);
        } catch (err) {
            console.error(err);
            setError('Failed to retrieve intelligence for this commodity.');
        } finally {
            setLoading(false);
        }
    }, [activeSource, params.id]);

    useEffect(() => {
        if (params.id && !isNaN(parseInt(params.id))) {
            loadData();
        } else {
            setError('Invalid intelligence identifier.');
            setLoading(false);
        }
    }, [params.id, activeSource, loadData]);

    // Aggregate data for the chart (Average modal price per day)
    const aggregatedChartData = React.useMemo(() => {
        const groups: { [key: string]: { price: number; arrival: number; count: number } } = {};

        prices.forEach(p => {
            if (!groups[p.date]) {
                groups[p.date] = { price: 0, arrival: 0, count: 0 };
            }
            groups[p.date].price += parseFloat(p.modal_price);
            groups[p.date].arrival += parseFloat(p.arrival_quantity);
            groups[p.date].count += 1;
        });

        return Object.entries(groups).map(([date, data]) => ({
            date,
            price: Math.round(data.price / data.count),
            arrival: Math.round(data.arrival)
        })).sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
    }, [prices]);

    // Calculate Market Distribution by State
    const distribution = React.useMemo(() => {
        const states: { [key: string]: number } = {};
        let totalVolume = 0;

        prices.forEach(p => {
            const vol = parseFloat(p.arrival_quantity);
            states[p.state_name] = (states[p.state_name] || 0) + vol;
            totalVolume += vol;
        });

        return Object.entries(states)
            .map(([state, volume], i) => ({
                state,
                share: Math.round((volume / totalVolume) * 100),
                color: i === 0 ? 'bg-brand-primary' : i === 1 ? 'bg-cyan-500' : 'bg-emerald-500'
            }))
            .sort((a, b) => b.share - a.share)
            .slice(0, 3);
    }, [prices]);

    // Calculate Variance for Insight
    const insightVariance = React.useMemo(() => {
        if (prices.length < 2) return 2.4;
        const pList = prices.map(p => parseFloat(p.modal_price));
        const avg = pList.reduce((a, b) => a + b, 0) / pList.length;
        const diffs = pList.map(p => Math.abs(p - avg));
        const avgDiff = diffs.reduce((a, b) => a + b, 0) / diffs.length;
        return ((avgDiff / avg) * 100).toFixed(1);
    }, [prices]);

    const handleExport = () => {
        alert("Exporting Intelligence Matrix for " + commodity.name + "... [PDF/XLS Generation Initiated]");
    };

    const handleShare = () => {
        alert("Generating Secure Intelligence Link... [Link Copied to Clipboard]");
    };

    const isLive = prices.some(p => String(p.source_name || '').toUpperCase() === 'AGMARKNET');

    const marketOptions = React.useMemo(() => {
        const seen = new Map();
        prices.forEach((price) => {
            if (price.market_id && !seen.has(price.market_id)) {
                seen.set(price.market_id, {
                    market_id: String(price.market_id),
                    market_name: price.market_name,
                    state_name: price.state_name,
                    unit: price.unit || 'QUINTAL',
                });
            }
        });
        return Array.from(seen.values());
    }, [prices]);

    useEffect(() => {
        if (!manualPriceForm.market_id && marketOptions.length > 0) {
            setManualPriceForm((current) => ({
                ...current,
                market_id: marketOptions[0].market_id,
                unit: marketOptions[0].unit || current.unit,
            }));
        }
    }, [marketOptions, manualPriceForm.market_id]);

    const handleManualPriceSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (!commodity) return;

        setSavingManualPrice(true);
        setManualPriceError(null);
        setManualPriceSuccess(null);

        try {
            const shouldReloadImmediately = activeSource === 'All Sources' || activeSource === 'NCEL';

            await upsertManualPrice({
                date: manualPriceForm.date,
                commodity_id: commodity.id,
                market_id: parseInt(manualPriceForm.market_id, 10),
                modal_price: parseFloat(manualPriceForm.modal_price),
                min_price: manualPriceForm.min_price ? parseFloat(manualPriceForm.min_price) : undefined,
                max_price: manualPriceForm.max_price ? parseFloat(manualPriceForm.max_price) : undefined,
                arrival_quantity: manualPriceForm.arrival_quantity ? parseFloat(manualPriceForm.arrival_quantity) : 0,
                unit: manualPriceForm.unit,
            });

            clearApiResponseCache();
            setManualPriceSuccess('NCEL price saved successfully.');
            setActiveUpdatePanel(null);
            setActiveSource('All Sources');
            if (shouldReloadImmediately) {
                await loadData();
            }
        } catch (submitError) {
            console.error(submitError);
            setManualPriceError('Failed to save the NCEL price update.');
        } finally {
            setSavingManualPrice(false);
        }
    };

    const handleSheetUpload = async (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (!commodity || !sheetFile) return;

        setUploadingSheet(true);
        setSheetUploadError(null);
        setSheetUploadSuccess(null);

        try {
            const response = await uploadManualPriceSheet(commodity.id, sheetFile);
            setSheetUploadSuccess(
                `Sheet processed successfully. Created ${response.created}, updated ${response.updated}, failed ${response.failed}.`,
            );
            setSheetFile(null);
            clearApiResponseCache();
            setActiveUpdatePanel(null);
            setActiveSource('All Sources');
            await loadData();
        } catch (uploadError) {
            console.error(uploadError);
            setSheetUploadError('Failed to upload the NCEL sheet. Please check the file format and try again.');
        } finally {
            setUploadingSheet(false);
        }
    };

    const handleDeleteManualPrice = async (recordId: string) => {
        const confirmed = window.confirm('Delete this NCEL manual price record? This cannot be undone.');
        if (!confirmed) return;

        setDeletingRecordId(recordId);
        setManualPriceError(null);
        setManualPriceSuccess(null);
        setSheetUploadError(null);
        setSheetUploadSuccess(null);

        try {
            setPrices((current) => current.filter((record) => record.id !== recordId));
            await deleteManualPrice(recordId);
            clearApiResponseCache();
            await loadData();
        } catch (deleteError) {
            console.error(deleteError);
            setManualPriceError('Failed to delete the NCEL manual price record.');
            await loadData();
        } finally {
            setDeletingRecordId(null);
        }
    };

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
                <div className="w-12 h-12 border-4 border-brand-primary/20 border-t-brand-primary rounded-full animate-spin" />
                <p className="text-slate-500 font-medium font-display tracking-wide animate-pulse uppercase text-[10px]">Processing Market Data...</p>
            </div>
        );
    }

    if (error || !commodity) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-6">
                <AlertTriangle className="w-16 h-16 text-amber-500 opacity-50" />
                <div className="text-center">
                    <h3 className="text-xl font-bold dark:text-white mb-2">Terminal Access Denied</h3>
                    <p className="text-slate-500 max-w-md mx-auto">{error || 'Intelligence node not found.'}</p>
                </div>
                <Link href="/commodities" className="px-6 py-2.5 bg-brand-primary text-white rounded-xl text-sm font-bold">
                    Return to Universe
                </Link>
            </div>
        );
    }

    return (
        <div className="space-y-8 max-w-[1600px] mx-auto pb-20">
            {/* Breadcrumbs & Actions */}
            <div className="flex justify-between items-center">
                <Link href="/commodities" className="flex items-center space-x-2 text-slate-500 hover:text-brand-primary transition-colors group">
                    <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
                    <span className="text-sm font-bold">Back to Universe</span>
                </Link>
                <div className="flex space-x-3">
                    <button
                        onClick={() => {
                            setManualPriceError(null);
                            setManualPriceSuccess(null);
                            setActiveUpdatePanel((value) => value === 'manual' ? null : 'manual');
                        }}
                        className="flex items-center space-x-2 px-5 py-2.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-sm font-bold text-slate-700 dark:text-slate-200 hover:border-brand-primary hover:text-brand-primary transition-all"
                    >
                        <Package className="w-4 h-4" />
                        <span>Update Manually</span>
                    </button>
                    <button
                        onClick={() => {
                            setSheetUploadError(null);
                            setSheetUploadSuccess(null);
                            setActiveUpdatePanel((value) => value === 'sheet' ? null : 'sheet');
                        }}
                        className="flex items-center space-x-2 px-5 py-2.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-sm font-bold text-slate-700 dark:text-slate-200 hover:border-brand-primary hover:text-brand-primary transition-all"
                    >
                        <Upload className="w-4 h-4" />
                        <span>Update Through Sheet</span>
                    </button>
                    <button
                        onClick={handleShare}
                        className="p-2.5 glass-card bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-slate-500 hover:text-brand-primary transition-colors"
                        title="Share Intelligence"
                    >
                        <Share2 className="w-4 h-4" />
                    </button>
                    <button
                        onClick={handleExport}
                        className="flex items-center space-x-2 px-5 py-2.5 bg-brand-primary text-white rounded-xl text-sm font-bold shadow-lg shadow-brand-primary/20 hover:bg-brand-primary/90 transition-all"
                    >
                        <Download className="w-4 h-4" />
                        <span>Export Intelligence</span>
                    </button>
                </div>
            </div>

            {activeUpdatePanel === 'manual' && (
                <div className="glass-card p-6 bg-white dark:bg-slate-900/70 border border-slate-200 dark:border-slate-800">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-6">
                        <div>
                            <h3 className="text-lg font-bold dark:text-white">Manual NCEL Price Update</h3>
                            <p className="text-sm text-slate-500">Save a manual price for this commodity and it will appear with discovery source `NCEL`.</p>
                        </div>
                        {manualPriceSuccess && (
                            <div className="text-sm font-medium text-emerald-600">{manualPriceSuccess}</div>
                        )}
                    </div>

                    <form onSubmit={handleManualPriceSubmit} className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                        <label className="space-y-2">
                            <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Date</span>
                            <input
                                type="date"
                                value={manualPriceForm.date}
                                onChange={(e) => setManualPriceForm((current) => ({ ...current, date: e.target.value }))}
                                className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl outline-none focus:ring-2 focus:ring-brand-primary/20"
                                required
                            />
                        </label>

                        <label className="space-y-2">
                            <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Market</span>
                            <select
                                value={manualPriceForm.market_id}
                                onChange={(e) => {
                                    const nextMarket = marketOptions.find((option: any) => option.market_id === e.target.value);
                                    setManualPriceForm((current) => ({
                                        ...current,
                                        market_id: e.target.value,
                                        unit: nextMarket?.unit || current.unit,
                                    }));
                                }}
                                className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl outline-none focus:ring-2 focus:ring-brand-primary/20"
                                required
                            >
                                {marketOptions.map((option: any) => (
                                    <option key={option.market_id} value={option.market_id}>
                                        {option.market_name} - {option.state_name}
                                    </option>
                                ))}
                            </select>
                        </label>

                        <label className="space-y-2">
                            <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Modal Price</span>
                            <input
                                type="number"
                                step="0.01"
                                min="0"
                                value={manualPriceForm.modal_price}
                                onChange={(e) => setManualPriceForm((current) => ({ ...current, modal_price: e.target.value }))}
                                className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl outline-none focus:ring-2 focus:ring-brand-primary/20"
                                required
                            />
                        </label>

                        <label className="space-y-2">
                            <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Arrival Quantity</span>
                            <input
                                type="number"
                                step="0.01"
                                min="0"
                                value={manualPriceForm.arrival_quantity}
                                onChange={(e) => setManualPriceForm((current) => ({ ...current, arrival_quantity: e.target.value }))}
                                className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl outline-none focus:ring-2 focus:ring-brand-primary/20"
                            />
                        </label>

                        <label className="space-y-2">
                            <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Min Price</span>
                            <input
                                type="number"
                                step="0.01"
                                min="0"
                                value={manualPriceForm.min_price}
                                onChange={(e) => setManualPriceForm((current) => ({ ...current, min_price: e.target.value }))}
                                className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl outline-none focus:ring-2 focus:ring-brand-primary/20"
                            />
                        </label>

                        <label className="space-y-2">
                            <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Max Price</span>
                            <input
                                type="number"
                                step="0.01"
                                min="0"
                                value={manualPriceForm.max_price}
                                onChange={(e) => setManualPriceForm((current) => ({ ...current, max_price: e.target.value }))}
                                className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl outline-none focus:ring-2 focus:ring-brand-primary/20"
                            />
                        </label>

                        <label className="space-y-2">
                            <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Unit</span>
                            <select
                                value={manualPriceForm.unit}
                                onChange={(e) => setManualPriceForm((current) => ({ ...current, unit: e.target.value }))}
                                className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl outline-none focus:ring-2 focus:ring-brand-primary/20"
                            >
                                <option value="QUINTAL">QUINTAL</option>
                                <option value="KG">KG</option>
                                <option value="MT">MT</option>
                            </select>
                        </label>

                        <div className="flex items-end gap-3">
                            <button
                                type="submit"
                                disabled={savingManualPrice || marketOptions.length === 0}
                                className="px-5 py-3 bg-brand-primary text-white rounded-xl text-sm font-bold shadow-lg shadow-brand-primary/20 hover:bg-brand-primary/90 transition-all disabled:opacity-50"
                            >
                                {savingManualPrice ? 'Saving...' : 'Save NCEL Price'}
                            </button>
                            <button
                                type="button"
                                onClick={() => setActiveUpdatePanel(null)}
                                className="px-5 py-3 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 rounded-xl text-sm font-bold"
                            >
                                Cancel
                            </button>
                        </div>
                    </form>

                    {marketOptions.length === 0 && (
                        <p className="mt-4 text-sm text-amber-500">No market options are available for this commodity yet, so a manual NCEL update cannot be attached to a market.</p>
                    )}
                    {manualPriceError && (
                        <p className="mt-4 text-sm text-rose-500">{manualPriceError}</p>
                    )}

                </div>
            )}

            {activeUpdatePanel === 'sheet' && (
                <div className="glass-card p-6 bg-white dark:bg-slate-900/70 border border-slate-200 dark:border-slate-800">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-5">
                        <div>
                            <h3 className="text-lg font-bold dark:text-white">Bulk NCEL Sheet Upload</h3>
                            <p className="text-sm text-slate-500">
                                Upload a `.csv`, `.xlsx`, or `.xls` file with columns `date`, `modal_price`, and either `market_id` or `market_name`.
                            </p>
                        </div>
                        {sheetUploadSuccess && (
                            <div className="text-sm font-medium text-emerald-600">{sheetUploadSuccess}</div>
                        )}
                    </div>

                    <form onSubmit={handleSheetUpload} className="grid grid-cols-1 lg:grid-cols-[1.5fr_auto_auto] gap-4 items-end">
                        <label className="space-y-2">
                            <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Upload Sheet</span>
                            <input
                                type="file"
                                accept=".csv,.xlsx,.xls"
                                onChange={(e) => setSheetFile(e.target.files?.[0] || null)}
                                className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl outline-none focus:ring-2 focus:ring-brand-primary/20 file:mr-4 file:border-0 file:bg-brand-primary/10 file:px-3 file:py-2 file:rounded-lg file:text-brand-primary file:font-semibold"
                                required
                            />
                        </label>
                        <button
                            type="submit"
                            disabled={uploadingSheet || !sheetFile}
                            className="px-5 py-3 bg-brand-primary text-white rounded-xl text-sm font-bold shadow-lg shadow-brand-primary/20 hover:bg-brand-primary/90 transition-all disabled:opacity-50"
                        >
                            {uploadingSheet ? 'Uploading...' : 'Upload NCEL Sheet'}
                        </button>
                        <button
                            type="button"
                            onClick={() => setActiveUpdatePanel(null)}
                            className="px-5 py-3 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 rounded-xl text-sm font-bold"
                        >
                            Cancel
                        </button>
                    </form>

                    <div className="mt-4 grid grid-cols-1 xl:grid-cols-2 gap-4 text-sm text-slate-500">
                        <div className="rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 p-4">
                            <p className="font-bold text-slate-700 dark:text-slate-200 mb-2">Supported columns</p>
                            <p>`date`, `modal_price`, `market_id` or `market_name`</p>
                            <p>`min_price`, `max_price`, `arrival_quantity`, `unit`</p>
                        </div>
                        <div className="rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 p-4">
                            <p className="font-bold text-slate-700 dark:text-slate-200 mb-2">Sample row</p>
                            <p className="font-mono text-xs break-all">2026-04-09, Azadpur Mandi, 2400, 2350, 2450, 500, QUINTAL</p>
                            <p className="text-xs mt-2">If you use names, map the second column to `market_name`.</p>
                        </div>
                    </div>

                    {sheetUploadError && (
                        <p className="mt-4 text-sm text-rose-500">{sheetUploadError}</p>
                    )}
                </div>
            )}

            {/* Header Info */}
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
                <div className="flex items-center space-x-6">
                    <div className="w-20 h-20 bg-brand-primary/10 rounded-3xl flex items-center justify-center border-2 border-brand-primary/20 relative">
                        <div className="text-2xl font-black text-brand-primary">{commodity.name.charAt(0)}</div>
                        {isLive && (
                            <div className="absolute -top-2 -right-2 w-6 h-6 bg-emerald-500 rounded-full border-4 border-white dark:border-slate-900 flex items-center justify-center" title="Live Verified Source">
                                <div className="w-1.5 h-1.5 bg-white rounded-full animate-ping" />
                            </div>
                        )}
                    </div>
                    <div>
                        <div className="flex items-center space-x-3 mb-1">
                            <h1 className="text-4xl font-bold font-display dark:text-white capitalize">{commodity.name}</h1>
                            <div className={`px-3 py-1 rounded-full text-[10px] font-black tracking-widest uppercase border ${isLive ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20' : 'bg-amber-500/10 text-amber-500 border-amber-500/20'}`}>
                                {isLive ? '✓ API Verified' : '! Index Fallback'}
                            </div>
                        </div>
                        <p className="text-slate-500 font-medium">Commodity Node: #NCR-{commodity.id.toString().padStart(4, '0')} • Sector: {commodity.category}</p>
                    </div>
                </div>

                <div className="flex flex-wrap gap-4">
                    <div className="p-4 glass-card bg-white dark:bg-slate-900 min-w-[200px]">
                        <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mb-1">Mean Terminal Price</p>
                        <div className="flex items-end space-x-2">
                            <span className="text-2xl font-bold dark:text-white">₹{average?.average_price_per_kg ? (average.average_price_per_kg * 100).toFixed(2) : '0.00'}</span>
                            <span className="text-emerald-500 text-xs font-bold mb-1">Modal / Qtl</span>
                        </div>
                    </div>
                    <div className="p-4 glass-card bg-white dark:bg-slate-900 min-w-[200px]">
                        <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mb-1">Tracked Transactions</p>
                        <div className="flex items-end space-x-2">
                            <span className="text-2xl font-bold dark:text-white">{prices.length}</span>
                            <span className="text-slate-500 text-xs font-bold mb-1">Records Found</span>
                        </div>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
                {/* Main Price & Arrival Chart */}
                <div className="xl:col-span-2 glass-card p-8 bg-white dark:bg-slate-900/40">
                    <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
                        <div>
                            <h2 className="text-xl font-bold dark:text-white">Price Velocity & Terminal Density</h2>
                            <p className="text-sm text-slate-500 font-medium">Time-series audit of price discovery (₹/Qtl)</p>
                        </div>
                        <div className="flex items-center space-x-2">
                            <TrendingUp className="w-4 h-4 text-brand-primary" />
                            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest px-2 py-1 bg-slate-100 dark:bg-slate-800 rounded-lg">Real-time Feed</span>
                        </div>
                    </div>

                    <div className="h-[450px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <ComposedChart data={aggregatedChartData}>
                                <defs>
                                    <linearGradient id="priceFlow" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#4F46E5" stopOpacity={0.1} />
                                        <stop offset="95%" stopColor="#4F46E5" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" strokeOpacity={0.1} />
                                <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: '#64748B', fontSize: 11 }} />
                                <YAxis yAxisId="left" axisLine={false} tickLine={false} tick={{ fill: '#64748B', fontSize: 11 }} orientation="left" />
                                <YAxis yAxisId="right" axisLine={false} tickLine={false} tick={{ fill: '#64748B', fontSize: 11 }} orientation="right" />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#0f172a', borderRadius: '12px', border: '1px solid #1e293b' }}
                                    itemStyle={{ fontSize: '12px', fontWeight: 'bold' }}
                                />
                                <Bar yAxisId="right" dataKey="arrival" fill="#94A3B8" fillOpacity={0.2} radius={[6, 6, 0, 0]} barSize={40} />
                                <Area yAxisId="left" type="monotone" dataKey="price" stroke="#4F46E5" strokeWidth={3} fill="url(#priceFlow)" dot={{ fill: '#4F46E5', strokeWidth: 2, r: 4 }} />
                            </ComposedChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* State Performance / Side Panel */}
                <div className="space-y-8">
                    <div className="glass-card p-6 bg-brand-primary/5 border-brand-primary/10">
                        <h3 className="font-bold dark:text-white mb-4 flex items-center">
                            <TrendingUp className="w-4 h-4 mr-2 text-brand-primary" />
                            Algorithmic Insight
                        </h3>
                        <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed italic">
                            Terminal data analysis suggests a stable trading corridor. Modal variance within ±{insightVariance}% across primary mandis.
                        </p>
                    </div>

                    <div className="glass-card p-6">
                        <h3 className="font-bold dark:text-white mb-6">Market Distribution</h3>
                        <div className="space-y-4">
                            {distribution.map((s, i) => (
                                <div key={i}>
                                    <div className="flex justify-between text-xs font-bold mb-1.5">
                                        <span className="dark:text-slate-300">{s.state}</span>
                                        <span className="text-slate-500">{s.share}% Volume</span>
                                    </div>
                                    <div className="h-1.5 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                                        <motion.div
                                            initial={{ width: 0 }}
                                            animate={{ width: `${s.share}%` }}
                                            transition={{ duration: 1, delay: i * 0.1 }}
                                            className={`h-full ${s.color}`}
                                        />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>

            {/* Mandi Drilldown Table */}
            <div className="glass-card">
                <div className="p-8 border-b border-slate-100 dark:border-slate-800 flex flex-col md:flex-row justify-between items-start md:items-center bg-slate-50/50 dark:bg-slate-900/40 gap-6">
                    <div>
                        <h3 className="text-xl font-bold dark:text-white">Terminal Price Discovery</h3>
                        <p className="text-sm text-slate-500 mt-1">Variety-level audit across top performing markets</p>
                    </div>
                    <div className="flex flex-wrap bg-slate-100 dark:bg-slate-800 p-1 rounded-xl">
                        {sources.map(src => (
                            <button
                                key={src}
                                onClick={() => setActiveSource(src)}
                                className={`px-3 py-1.5 rounded-lg text-[10px] font-bold transition-all ${activeSource === src
                                    ? 'bg-white dark:bg-slate-700 text-brand-primary shadow-sm'
                                    : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                                    }`}
                            >
                                {src}
                            </button>
                        ))}
                    </div>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead className="bg-slate-50 dark:bg-slate-900/60 text-[10px] text-slate-400 uppercase tracking-widest font-bold">
                            <tr>
                                <th className="px-8 py-5 text-left">Generated Date</th>
                                <th className="px-8 py-5 text-left">Terminal Market</th>
                                <th className="px-8 py-5 text-center">Arrival Qty</th>
                                <th className="px-8 py-5 text-right">Min Price</th>
                                <th className="px-8 py-5 text-right">Max Price</th>
                                <th className="px-8 py-5 text-right">Discovery Source</th>
                                <th className="px-8 py-5 text-right">Modal Discovery</th>
                                <th className="px-8 py-5 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                            {prices.slice(0, 20).map((record, i) => (
                                <tr key={i} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors cursor-pointer group">
                                    <td className="px-8 py-4">
                                        <div className="flex items-center space-x-3">
                                            <div className="w-8 h-8 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
                                                <Calendar className="w-4 h-4 text-slate-400 group-hover:text-brand-primary transition-colors" />
                                            </div>
                                            <div>
                                                <p className="text-sm font-bold dark:text-slate-200">{record.date}</p>
                                                <p className="text-[10px] text-slate-500 font-mono">ID: {record.id.split('-')[0]}</p>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-8 py-4">
                                        <div className="flex items-center space-x-2">
                                            <MapPin className="w-3.5 h-3.5 text-brand-primary" />
                                            <div>
                                                <p className="text-sm font-bold dark:text-slate-200">{record.market_name}</p>
                                                <p className="text-[10px] text-slate-500 font-display uppercase tracking-wider">{record.state_name}</p>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-8 py-4 text-center font-mono text-xs text-slate-500">
                                        {record.source_name === 'FAO' ? '--' : `${parseFloat(record.arrival_quantity).toFixed(0)} `}
                                        <span className="text-[10px] uppercase">{record.source_name === 'FAO' ? 'Pts' : 'MT'}</span>
                                    </td>
                                    <td className="px-8 py-4 text-right text-sm text-slate-500">
                                        {record.source_name === 'FAO' ? '' : '₹'}{parseFloat(record.min_price).toFixed(0)}
                                    </td>
                                    <td className="px-8 py-4 text-right text-sm text-slate-500">
                                        {record.source_name === 'FAO' ? '' : '₹'}{parseFloat(record.max_price).toFixed(0)}
                                    </td>
                                    <td className="px-8 py-4 text-right">
                                        <div className="flex flex-col items-end">
                                            <span className={`text-[9px] font-black uppercase tracking-tighter px-1.5 py-0.5 rounded ${String(record.source_name || '').toUpperCase() === 'AGMARKNET' ? 'bg-indigo-500/10 text-indigo-500' : String(record.source_name || '').toUpperCase() === 'NCEL' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-slate-500/10 text-slate-500'}`}>
                                                {String(record.source_name || '').toUpperCase() === 'AGMARKNET' ? 'Gov.in API' : String(record.source_name || '').toUpperCase() === 'NCEL' ? 'Manual Update' : 'Hub Seeding'}
                                            </span>
                                            <span className="text-[10px] text-slate-400 font-medium">{record.source_name}</span>
                                            {String(record.source_name || '').toUpperCase() === 'NCEL' && (
                                                <button
                                                    type="button"
                                                    onClick={(event) => {
                                                        event.preventDefault();
                                                        event.stopPropagation();
                                                        handleDeleteManualPrice(record.id);
                                                    }}
                                                    disabled={deletingRecordId === record.id}
                                                    className="mt-2 inline-flex items-center gap-1 rounded-md border border-rose-200 bg-rose-50 px-2 py-1 text-[10px] font-bold text-rose-600 transition-colors hover:bg-rose-100 disabled:opacity-50 dark:border-rose-900/40 dark:bg-rose-500/10 dark:text-rose-400"
                                                >
                                                    <Trash2 className="w-3 h-3" />
                                                    <span>{deletingRecordId === record.id ? 'Deleting...' : 'Delete'}</span>
                                                </button>
                                            )}
                                        </div>
                                    </td>
                                    <td className="px-8 py-4 text-right">
                                        <div className="flex items-center justify-end space-x-2">
                                            <span className="text-sm font-bold dark:text-white">₹{parseFloat(record.modal_price).toFixed(0)}</span>
                                            <div className="w-1.5 h-1.5 rounded-full bg-brand-primary animate-pulse" />
                                        </div>
                                    </td>
                                    <td className="px-8 py-4 text-right">
                                        {String(record.source_name || '').toUpperCase() === 'NCEL' ? (
                                            <button
                                                type="button"
                                                onClick={(event) => {
                                                    event.preventDefault();
                                                    event.stopPropagation();
                                                    handleDeleteManualPrice(record.id);
                                                }}
                                                disabled={deletingRecordId === record.id}
                                                className="inline-flex items-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-[11px] font-bold text-rose-600 transition-colors hover:bg-rose-100 disabled:opacity-50 dark:border-rose-900/40 dark:bg-rose-500/10 dark:text-rose-400"
                                            >
                                                <Trash2 className="w-3.5 h-3.5" />
                                                <span>{deletingRecordId === record.id ? 'Deleting...' : 'Delete'}</span>
                                            </button>
                                        ) : (
                                            <span className="text-[10px] text-slate-400">Locked</span>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
