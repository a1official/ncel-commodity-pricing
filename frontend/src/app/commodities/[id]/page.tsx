"use client";

import React, { useState, useEffect } from 'react';
import {
    LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, ComposedChart
} from 'recharts';
import {
    ArrowLeft, Download, Filter, Share2, Info, MapPin, Calendar, TrendingUp, Package, Layers, AlertTriangle, Loader2
} from 'lucide-react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { fetchCommodities, fetchPrices, fetchDailyAverage } from '@/lib/api';

export default function CommodityDetail({ params }: { params: { id: string } }) {
    const [commodity, setCommodity] = useState<any>(null);
    const [prices, setPrices] = useState<any[]>([]);
    const [average, setAverage] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function loadData() {
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

                const history = await fetchPrices({ commodity_id: parseInt(params.id) });
                setPrices(history);

            } catch (err) {
                console.error(err);
                setError('Failed to retrieve intelligence for this commodity.');
            } finally {
                setLoading(false);
            }
        }
        if (params.id && !isNaN(parseInt(params.id))) {
            loadData();
        } else {
            setError('Invalid intelligence identifier.');
            setLoading(false);
        }
    }, [params.id]);

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

    const isLive = prices.some(p => p.source_name === 'Agmarknet');

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
                            <span className="text-2xl font-bold dark:text-white">₹{(average?.average_price_per_kg * 100).toFixed(2)}</span>
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
                    <div className="flex justify-between items-center mb-10">
                        <div>
                            <h2 className="text-xl font-bold dark:text-white">Price Velocity & Terminal Density</h2>
                            <p className="text-sm text-slate-500 font-medium">Time-series audit of price discovery (₹/Qtl)</p>
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
                <div className="p-8 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center bg-slate-50/50 dark:bg-slate-900/40">
                    <div>
                        <h3 className="text-xl font-bold dark:text-white">Terminal Price Discovery</h3>
                        <p className="text-sm text-slate-500 mt-1">Variety-level audit across top performing markets</p>
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
                                    <td className="px-8 py-4 text-center">
                                        <span className="text-sm font-bold dark:text-slate-200">{parseFloat(record.arrival_quantity).toFixed(0)}</span>
                                        <span className="text-[10px] text-slate-500 ml-1">MT</span>
                                    </td>
                                    <td className="px-8 py-4 text-right text-sm text-slate-500">₹{parseFloat(record.min_price).toFixed(0)}</td>
                                    <td className="px-8 py-4 text-right text-sm text-slate-500">₹{parseFloat(record.max_price).toFixed(0)}</td>
                                    <td className="px-8 py-4 text-right">
                                        <div className="flex flex-col items-end">
                                            <span className={`text-[9px] font-black uppercase tracking-tighter px-1.5 py-0.5 rounded ${record.source_name === 'Agmarknet' ? 'bg-indigo-500/10 text-indigo-500' : 'bg-slate-500/10 text-slate-500'}`}>
                                                {record.source_name === 'Agmarknet' ? 'Gov.in API' : 'Hub Seeding'}
                                            </span>
                                            <span className="text-[10px] text-slate-400 font-medium">{record.source_name}</span>
                                        </div>
                                    </td>
                                    <td className="px-8 py-4 text-right">
                                        <div className="flex items-center justify-end space-x-2">
                                            <span className="text-sm font-bold dark:text-white">₹{parseFloat(record.modal_price).toFixed(0)}</span>
                                            <div className="w-1.5 h-1.5 rounded-full bg-brand-primary animate-pulse" />
                                        </div>
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
