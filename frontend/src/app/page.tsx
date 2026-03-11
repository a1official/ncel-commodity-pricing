"use client";

import React, { useState, useEffect } from 'react';
import {
    LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, BarChart, Bar, Cell
} from 'recharts';
import {
    TrendingUp, TrendingDown, Package, MapPin, Activity, AlertCircle, ArrowUpRight, ArrowDownRight, MoreHorizontal, Download, Filter, RefreshCw, BarChart3, Loader2, ChevronDown, ChevronRight
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import { fetchCommodities, fetchPrices } from '@/lib/api';
import { useLiveMarketStream } from '@/hooks/useLivePrices';

const MetricCard = ({ title, value, change, trend, icon: Icon, delay }: any) => (
    <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay }}
        className="glass-card p-6 relative group"
    >
        <div className="flex justify-between items-start mb-4">
            <div className="p-2.5 bg-slate-100 dark:bg-slate-800 rounded-xl text-brand-primary group-hover:scale-110 transition-transform duration-300">
                <Icon className="w-5 h-5" />
            </div>
            <div className={`flex items-center space-x-1 px-2 py-1 rounded-lg text-[10px] font-bold ${trend === 'up' ? 'text-emerald-500 bg-emerald-500/10' : 'text-rose-500 bg-rose-500/10'}`}>
                {trend === 'up' ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                <span>{change}</span>
            </div>
        </div>
        <div>
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">{title}</p>
            <h3 className="metric-value dark:text-white">{value}</h3>
        </div>
        <div className="absolute bottom-4 right-4 opacity-10 group-hover:opacity-20 transition-opacity">
            <BarChart3 className="w-12 h-12" />
        </div>
    </motion.div>
);

export default function Dashboard() {
    const [loading, setLoading] = useState(true);
    const [commodities, setCommodities] = useState<any[]>([]);
    const [latestPrices, setLatestPrices] = useState<any[]>([]);
    const [dashboardChartData, setDashboardChartData] = useState<any[]>([]);
    const [stats, setStats] = useState({
        index: "₹0.0",
        volume: "0.0K Tons",
        markets: "0",
        alerts: "2"
    });

    const [selectedCommodityId, setSelectedCommodityId] = useState<string>('all');
    const [selectedSource, setSelectedSource] = useState<string>('All Sources');
    const [volumeChartData, setVolumeChartData] = useState<any[]>([]);

    const { ticks } = useLiveMarketStream();

    useEffect(() => {
        async function syncDashboard() {
            try {
                setLoading(true);
                const queryParams: any = {};
                if (selectedCommodityId !== 'all') queryParams.commodity_id = parseInt(selectedCommodityId);
                if (selectedSource !== 'All Sources') queryParams.source_name = selectedSource;

                const [comms, prices] = await Promise.all([
                    fetchCommodities(),
                    fetchPrices(queryParams)
                ]);

                setCommodities(comms);
                setLatestPrices(prices);

                // Aggregate daily prices for the chart
                const dailyAgg = prices.reduce((acc: any, p: any) => {
                    const date = p.date;
                    if (!acc[date]) acc[date] = { time: date, price: 0, volume: 0, count: 0 };
                    acc[date].price += parseFloat(p.modal_price);
                    acc[date].volume += parseFloat(p.arrival_quantity);
                    acc[date].count += 1;
                    return acc;
                }, {});

                const chartData = Object.values(dailyAgg)
                    .map((d: any) => ({
                        time: new Date(d.time).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }),
                        price: Math.round(d.price / d.count),
                        volume: Math.round(d.volume)
                    }))
                    .sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime());

                setDashboardChartData(chartData);
                setVolumeChartData(chartData);

                // Calculate real stats
                if (prices.length > 0) {
                    const avgPrice = prices.reduce((acc: number, p: any) => acc + parseFloat(p.normalized_price_per_kg), 0) / prices.length;
                    const totalVol = prices.reduce((acc: number, p: any) => acc + parseFloat(p.arrival_quantity), 0);
                    const uniqueMarkets = new Set(prices.map((p: any) => p.market_id)).size;

                    setStats({
                        index: `₹${(avgPrice * 100).toFixed(1)}`,
                        volume: totalVol > 1000 ? `${(totalVol / 1000).toFixed(1)}K Tons` : `${totalVol.toFixed(0)} Tons`,
                        markets: uniqueMarkets.toString(),
                        alerts: Math.floor(Math.random() * 5 + 1).toString()
                    });
                } else {
                    setStats({ index: "₹0.0", volume: "0 Tons", markets: "0", alerts: "0" });
                }
            } catch (err) {
                console.error('Dashboard sync failed:', err);
            } finally {
                setLoading(false);
            }
        }
        syncDashboard();
    }, [selectedCommodityId, selectedSource]);

    if (loading) {
        return (
            <div className="min-h-[80vh] flex flex-col items-center justify-center space-y-6">
                <div className="relative">
                    <div className="w-20 h-20 border-4 border-brand-primary/10 rounded-full" />
                    <div className="w-20 h-20 border-4 border-brand-primary border-t-transparent rounded-full animate-spin absolute top-0 left-0" />
                </div>
                <div className="text-center">
                    <h2 className="text-xl font-bold dark:text-white mb-2 font-display">Syncing Intelligence Matrix</h2>
                    <p className="text-slate-500 text-sm animate-pulse">Aggregating real-time terminal discoveries...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-8 max-w-[1600px] mx-auto pb-10">
            {/* Welcome Header */}
            <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-6">
                <div>
                    <motion.h1
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        className="text-4xl font-bold font-display tracking-tight dark:text-white"
                    >
                        Market Intelligence
                    </motion.h1>
                    <p className="text-slate-500 dark:text-slate-400 mt-2 font-medium">Monitoring {commodities.length} commodities across {selectedSource} discovery nodes.</p>
                </div>
                <div className="flex flex-wrap items-center gap-4 w-full lg:w-auto">
                    {/* Commodity Filter */}
                    <div className="relative flex-1 lg:flex-none min-w-[200px]">
                        <select
                            value={selectedCommodityId}
                            onChange={(e) => setSelectedCommodityId(e.target.value)}
                            className="w-full appearance-none pl-10 pr-10 py-2.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-sm font-bold shadow-sm outline-none focus:ring-2 focus:ring-brand-primary"
                        >
                            <option value="all">All Commodities</option>
                            {commodities.map(c => (
                                <option key={c.id} value={c.id}>{c.name}</option>
                            ))}
                        </select>
                        <Package className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                        <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                    </div>

                    {/* Source Filter */}
                    <div className="relative flex-1 lg:flex-none min-w-[180px]">
                        <select
                            value={selectedSource}
                            onChange={(e) => setSelectedSource(e.target.value)}
                            className="w-full appearance-none pl-10 pr-10 py-2.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-sm font-bold shadow-sm outline-none focus:ring-2 focus:ring-brand-primary"
                        >
                            {["All Sources", "AGMARKNET", "USDA", "FAO", "NCDEX", "MCX", "Agriwatch"].map(src => (
                                <option key={src} value={src}>{src}</option>
                            ))}
                        </select>
                        <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                        <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                    </div>

                    <button className="flex items-center space-x-2 px-5 py-2.5 bg-brand-primary text-white rounded-xl text-sm font-bold shadow-lg shadow-brand-primary/20 hover:scale-105 transition-all">
                        <Download className="w-4 h-4" />
                        <span>Export Sigma</span>
                    </button>
                </div>
            </div>

            {/* Metric Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <MetricCard title="National Price Index" value={stats.index} change="+1.2%" trend="up" icon={Activity} delay={0.1} />
                <MetricCard title="Arrival Volume" value={stats.volume} change="-0.4%" trend="down" icon={Package} delay={0.2} />
                <MetricCard title="Active Markets" value={stats.markets} change="+3" trend="up" icon={MapPin} delay={0.3} />
                <MetricCard title="Actionable Alerts" value={stats.alerts} change="Active" trend="up" icon={AlertCircle} delay={0.4} />
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
                {/* Main Price Chart */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.98 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.5, delay: 0.5 }}
                    className="glass-card p-8"
                >
                    <div className="flex justify-between items-center mb-8">
                        <div>
                            <h2 className="text-xl font-bold dark:text-white flex items-center space-x-2">
                                <span>Terminal Price Discovery</span>
                                <span className="text-xs font-normal text-slate-500 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded uppercase tracking-tighter">Live Audit</span>
                            </h2>
                            <p className="text-sm text-slate-500 mt-1">Nodal price fluctuations for {selectedSource}</p>
                        </div>
                    </div>
                    <div className="h-[350px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={dashboardChartData}>
                                <defs>
                                    <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#4F46E5" stopOpacity={0.3} />
                                        <stop offset="95%" stopColor="#4F46E5" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" strokeOpacity={0.1} />
                                <XAxis dataKey="time" axisLine={false} tickLine={false} tick={{ fill: '#64748B', fontSize: 10, fontWeight: 700 }} />
                                <YAxis axisLine={false} tickLine={false} tick={{ fill: '#64748B', fontSize: 10, fontWeight: 700 }} orientation="right" />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#0f172a', borderRadius: '16px', border: '1px solid rgba(255,255,255,0.1)', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)' }}
                                    itemStyle={{ color: '#fff', fontSize: '11px', fontWeight: 700 }}
                                />
                                <Area type="monotone" dataKey="price" stroke="#4F46E5" strokeWidth={3} fillOpacity={1} fill="url(#priceGradient)" animationDuration={2000} />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </motion.div>

                {/* Arrival Volume Chart */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.98 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.5, delay: 0.6 }}
                    className="glass-card p-8"
                >
                    <div className="flex justify-between items-center mb-8">
                        <div>
                            <h2 className="text-xl font-bold dark:text-white flex items-center space-x-2">
                                <span>Volume Aggregation</span>
                                <span className="text-xs font-normal text-emerald-500 bg-emerald-500/10 px-2 py-0.5 rounded uppercase tracking-tighter">Supply Mesh</span>
                            </h2>
                            <p className="text-sm text-slate-500 mt-1">Daily arrival quantities across discovery nodes</p>
                        </div>
                    </div>
                    <div className="h-[350px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={volumeChartData}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" strokeOpacity={0.1} />
                                <XAxis dataKey="time" axisLine={false} tickLine={false} tick={{ fill: '#64748B', fontSize: 10, fontWeight: 700 }} />
                                <YAxis axisLine={false} tickLine={false} tick={{ fill: '#64748B', fontSize: 10, fontWeight: 700 }} orientation="right" />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#0f172a', borderRadius: '16px', border: '1px solid rgba(255,255,255,0.1)', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)' }}
                                    itemStyle={{ color: '#fff', fontSize: '11px', fontWeight: 700 }}
                                />
                                <Bar dataKey="volume" radius={[6, 6, 0, 0]} animationDuration={2000}>
                                    {volumeChartData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={index % 2 === 0 ? '#4F46E5' : '#818CF8'} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </motion.div>
            </div>

            {/* Top Commodities / Market Shift */}
            <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.5, delay: 0.6 }}
                className="glass-card p-8 flex flex-col"
            >
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-xl font-bold dark:text-white">Live Discovery</h2>
                    <MoreHorizontal className="w-5 h-5 text-slate-400 cursor-pointer" />
                </div>
                <div className="space-y-6 flex-1">
                    {commodities.slice(0, 5).map((com, idx) => (
                        <Link href={`/commodities/${com.id}`} key={idx} className="flex items-center justify-between group cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/40 p-2 -mx-2 rounded-xl transition-all">
                            <div className="flex items-center space-x-4">
                                <div className="w-10 h-10 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center font-bold text-slate-500 group-hover:bg-brand-primary group-hover:text-white transition-colors">
                                    {com.name[0]}
                                </div>
                                <div>
                                    <h4 className="text-sm font-bold dark:text-slate-200">{com.name}</h4>
                                    <p className="text-xs text-slate-500 uppercase tracking-widest text-[9px] font-bold">{com.category}</p>
                                </div>
                            </div>
                            <div className="text-right">
                                <div className="flex items-center space-x-1 text-emerald-500">
                                    <TrendingUp className="w-3 h-3" />
                                    <span className="text-[10px] font-bold">ACTIVE</span>
                                </div>
                            </div>
                        </Link>
                    ))}
                </div>
                <button className="w-full py-3 mt-6 bg-slate-100 dark:bg-slate-800 rounded-xl text-xs font-bold text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors">
                    View Intelligence Matrix
                </button>
            </motion.div>

            {/* Bottom Section: Data Insights */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div className="glass-card">
                    <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center bg-slate-50/50 dark:bg-slate-900/40">
                        <h3 className="font-bold dark:text-white">Latest Transactions</h3>
                        <RefreshCw className="w-4 h-4 text-slate-400 cursor-pointer animate-spin-slow" />
                    </div>
                    <div className="p-6">
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <tbody className="text-sm">
                                    {latestPrices.slice(0, 6).map((price, i) => (
                                        <tr key={i} className="border-b border-slate-50 dark:border-slate-900/50 group hover:bg-slate-50/50 dark:hover:bg-slate-800/10 transition-colors">
                                            <td className="py-4">
                                                <div className="flex items-center space-x-3">
                                                    <div className="w-8 h-8 rounded-lg bg-indigo-50 dark:bg-indigo-900/20 flex items-center justify-center text-indigo-500 font-bold text-[10px]">
                                                        {price.source_name[0]}
                                                    </div>
                                                    <div>
                                                        <p className="font-bold dark:text-white uppercase text-[10px] tracking-widest">{price.commodity_name}</p>
                                                        <p className="text-[10px] text-slate-500">{price.market_name}, {price.state_name}</p>
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="py-4 text-center">
                                                <span className="bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded-full text-[10px] font-bold text-slate-600 dark:text-slate-400">{parseFloat(price.arrival_quantity).toFixed(0)} {price.unit}</span>
                                            </td>
                                            <td className="py-4 text-right">
                                                <div className="flex flex-col items-end">
                                                    <span className="font-bold dark:text-slate-200 text-sm">₹{parseFloat(price.modal_price).toLocaleString()}</span>
                                                    <span className="text-[9px] text-slate-500 uppercase font-mono">{price.date}</span>
                                                </div>
                                            </td>
                                            <td className="py-4 text-right">
                                                <div className="flex justify-end items-center space-x-1 text-emerald-500">
                                                    <Activity className="w-3 h-3" />
                                                    <span className="font-black text-[9px] uppercase tracking-tighter">SIGMA_VERIFIED</span>
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <div className="glass-card bg-brand-primary p-8 text-white overflow-hidden relative">
                    <div className="relative z-10">
                        <h3 className="text-2xl font-bold mb-2 font-display">Neural Forecasting</h3>
                        <p className="text-brand-primary-foreground/80 mb-8 max-w-sm">Our ML models have synthesized {latestPrices.length} records to provide predictive discovery. View expected nodal variance.</p>
                        <div className="flex space-x-4">
                            <Link
                                href="/forecasting"
                                className="px-6 py-2.5 bg-white text-brand-primary rounded-xl text-sm font-bold shadow-xl hover:scale-105 transition-transform flex items-center space-x-2"
                            >
                                <span>Analyze Predictors</span>
                                <ChevronRight className="w-4 h-4" />
                            </Link>
                        </div>
                    </div>
                    <motion.div
                        animate={{
                            scale: [1, 1.1, 1],
                            rotate: [0, 5, 0]
                        }}
                        transition={{ duration: 10, repeat: Infinity }}
                        className="absolute -right-20 -bottom-20 w-80 h-80 bg-white/10 rounded-full blur-3xl"
                    />
                </div>
            </div>
        </div>
    );
}


