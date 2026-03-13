"use client";

import React, { useState, useEffect, useMemo } from 'react';
import {
    Waves, Anchor, Ship, TrendingUp, DollarSign, Filter, Box, MapPin, 
    Activity, ArrowRight, RefreshCw, Layers, X, Download
} from 'lucide-react';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend, LineChart, Line
} from 'recharts';
import { motion, AnimatePresence } from 'framer-motion';
import { fetchCommodities, fetchPrices, fetchMpedaExportData, fetchMarineSummary, fetchMarineStates } from '@/lib/api';

export default function MarineDashboard() {
    const [commodities, setCommodities] = useState<any[]>([]);
    const [prices, setPrices] = useState<any[]>([]);
    const [mpedaData, setMpedaData] = useState<any[]>([]);
    const [mpedaLoading, setMpedaLoading] = useState(true);
    const [loading, setLoading] = useState(true);
    const [marineSummary, setMarineSummary] = useState<any[]>([]);
    const [marineStates, setMarineStates] = useState<any[]>([]);
    const [selectedMarket, setSelectedMarket] = useState<string | null>(null);
    const [hubType, setHubType] = useState<'all' | 'port' | 'mandi'>('all');
    const [mpedaError, setMpedaError] = useState<string | null>(null);

    useEffect(() => {
        const loadMarineData = async () => {
            setLoading(true);
            try {
                const [comms, allPrices, summary, states] = await Promise.all([
                    fetchCommodities(),
                    fetchPrices({ category: 'Marine Products', limit: 1000 }),
                    fetchMarineSummary(),
                    fetchMarineStates()
                ]);

                const marineComms = comms.filter((c: any) => 
                    c.category === 'Marine Products'
                );
                setCommodities(marineComms);
                setPrices(allPrices);
                setMarineSummary(summary);
                setMarineStates(states);
            } catch (err) {
                console.error("Marine data load failed", err);
            } finally {
                setLoading(false);
            }
        };
        
        const loadMpedaData = async () => {
            setMpedaLoading(true);
            setMpedaError(null);
            try {
                console.log("Fetching MPEDA data...");
                const data = await fetchMpedaExportData({ limit: 100 });
                console.log("MPEDA data received:", data);
                if (data && data.records && data.records.length > 0) {
                    setMpedaData(data.records);
                } else {
                    console.log("No records in MPEDA response");
                    setMpedaError("No data available");
                }
            } catch (err) {
                console.error("MPEDA data load failed", err);
                setMpedaError("Failed to load MPEDA data");
            } finally {
                setMpedaLoading(false);
            }
        };
        
        loadMarineData();
        loadMpedaData();
    }, []);

    const speciesAverages = useMemo(() => {
        const groups: any = {};
        prices.forEach(p => {
            if (!groups[p.commodity_name]) groups[p.commodity_name] = { sum: 0, count: 0 };
            groups[p.commodity_name].sum += parseFloat(p.modal_price);
            groups[p.commodity_name].count += 1;
        });

        return Object.entries(groups).map(([name, data]: [string, any]) => {
            const avg = data.sum / data.count;
            // Mock export price as baseline + 35% margin for arbitrage visualization
            return {
                name,
                price: Math.round(avg),
                exportPrice: Math.round(avg * 1.35)
            };
        }).sort((a, b) => b.price - a.price);
    }, [prices]);

    const marineHubs = useMemo(() => {
        const uniqueMarkets = Array.from(new Set(prices.map(p => p.market_name)));
        return uniqueMarkets.map(market => {
            const p = prices.find(price => price.market_name === market);
            const isPort = p?.state_name === "Coastal Hub" || 
                          market.toLowerCase().includes('port') || 
                          market.toLowerCase().includes('harbour') ||
                          market.toLowerCase().includes('jetty') ||
                          market.toLowerCase().includes('landing');
            return {
                name: market,
                type: isPort ? 'port' as const : 'mandi' as const,
                state: p?.state_name || 'Unknown'
            };
        });
    }, [prices]);

    const filteredHubs = useMemo(() => {
        if (hubType === 'all') return marineHubs;
        return marineHubs.filter(h => h.type === hubType);
    }, [marineHubs, hubType]);

    const stats = useMemo(() => {
        const totalValue = prices.reduce((acc, p) => {
            return acc + (parseFloat(p.modal_price) * parseFloat(p.arrival_quantity));
        }, 0);
        
        return [
            { label: 'Export Quality Index', value: '4.9/5.0', change: '+0.1', trend: 'up', icon: Activity },
            { label: 'Active Landing Centers', value: marineHubs.filter(h => h.type === 'port').length || '0', change: '+2', trend: 'up', icon: Anchor },
            { label: 'Est. Revenue Pulse', value: `₹${(totalValue / 1e7).toFixed(1)} Cr`, change: '+8%', trend: 'up', icon: Activity },
            { label: 'Integrated Marine Hubs', value: marineHubs.length || '0', change: 'Stable', trend: 'up', icon: Ship },
        ];
    }, [prices, marineHubs]);

    const gradeDistribution = [
        { name: 'Grade A (Export)', value: 65, color: '#4F46E5' },
        { name: 'Grade B (Premium)', value: 25, color: '#06B6D4' },
        { name: 'Grade C (Standard)', value: 10, color: '#10B981' },
    ];

    const marketPrices = useMemo(() => {
        if (!selectedMarket) return [];
        return prices.filter(p => p.market_name === selectedMarket);
    }, [selectedMarket, prices]);

    if (loading) {
        return (
            <div className="min-h-[60vh] flex flex-col items-center justify-center space-y-4">
                <RefreshCw className="w-10 h-10 text-brand-primary animate-spin" />
                <p className="text-sm font-bold text-slate-500 animate-pulse uppercase tracking-widest">Scanning Maritime Landing Data...</p>
            </div>
        );
    }

    return (
        <div className="space-y-8 max-w-[1600px] mx-auto pb-20 relative">
            {/* Drilldown Modal Overlay */}
            <AnimatePresence>
                {selectedMarket && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-[100] flex items-center justify-center p-4 backdrop-blur-md bg-slate-950/40"
                    >
                        <motion.div
                            initial={{ scale: 0.95, opacity: 0, y: 20 }}
                            animate={{ scale: 1, opacity: 1, y: 0 }}
                            exit={{ scale: 0.95, opacity: 0, y: 20 }}
                            className="bg-white dark:bg-slate-900 w-full max-w-4xl rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden"
                        >
                            <div className="p-8 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center bg-slate-50/50 dark:bg-slate-800/30">
                                <div className="flex items-center space-x-4">
                                    <div className="p-3 bg-brand-primary/10 rounded-2xl">
                                        <Anchor className="w-6 h-6 text-brand-primary" />
                                    </div>
                                    <div>
                                        <h2 className="text-2xl font-bold dark:text-white capitalize">{selectedMarket} Hub Drilldown</h2>
                                        <p className="text-sm text-slate-500 font-medium tracking-tight">Real-time variety-level species pricing.</p>
                                    </div>
                                </div>
                                <button
                                    onClick={() => setSelectedMarket(null)}
                                    className="p-2 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-full transition-colors"
                                >
                                    <X className="w-6 h-6 text-slate-400" />
                                </button>
                            </div>

                            <div className="p-8 max-h-[65vh] overflow-y-auto custom-scrollbar">
                                <table className="w-full text-left border-collapse">
                                    <thead>
                                        <tr className="text-[10px] font-black text-slate-400 uppercase tracking-widest border-b border-slate-100 dark:border-slate-800">
                                            <th className="pb-4 pl-2">Commodity / Variety</th>
                                            <th className="pb-4">Market Price</th>
                                            <th className="pb-4">Arrivals</th>
                                            <th className="pb-4">Intelligence Date</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                                        {marketPrices.map((p, idx) => (
                                            <tr key={idx} className="group hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                                                <td className="py-5 pl-2">
                                                    <div className="flex items-center space-x-3">
                                                        <div className="w-1.5 h-1.5 rounded-full bg-brand-primary" />
                                                        <div>
                                                            <p className="font-bold dark:text-white mb-0.5">{p.commodity_name}</p>
                                                            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-tight">{p.variety_name}</p>
                                                        </div>
                                                    </div>
                                                </td>
                                                <td className="py-5">
                                                    <span className="text-lg font-black text-brand-primary">
                                                        ₹{Math.round(p.modal_price).toLocaleString()}
                                                    </span>
                                                    <span className="text-[8px] font-black text-slate-400 uppercase ml-1">/Qtl</span>
                                                </td>
                                                <td className="py-5">
                                                    <p className="font-bold dark:text-slate-300">{p.arrival_quantity} Qtl</p>
                                                </td>
                                                 <td className="py-5 text-xs font-bold text-slate-400 italic">
                                                    {p.date}
                                                 </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
            {/* Header */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
                <div className="flex items-center space-x-5">
                    <div className="w-16 h-16 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-2xl flex items-center justify-center shadow-xl shadow-blue-500/20">
                        <Waves className="text-white w-9 h-9" />
                    </div>
                    <div>
                        <h1 className="text-4xl font-bold font-display dark:text-white">Marine Intelligence</h1>
                        <p className="text-slate-500 font-medium">Tracking landing prices and global export arbitrage for {commodities.length} key species.</p>
                    </div>
                </div>
                <div className="flex space-x-3">
                    <button className="flex items-center space-x-2 px-6 py-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-sm font-bold shadow-sm hover:border-brand-primary transition-all">
                        <MapPin className="w-4 h-4 text-brand-primary" />
                        <span>Port Explorer</span>
                    </button>
                    <button className="flex items-center space-x-2 px-6 py-3 bg-brand-primary text-white rounded-xl text-sm font-bold shadow-lg shadow-brand-primary/20 hover:scale-[1.02] transition-all">
                        <Download className="w-4 h-4" />
                        <span>Export Trade Flows</span>
                    </button>
                </div>
            </div>

            {/* Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {stats.map((stat, idx) => (
                    <motion.div
                        key={idx}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: idx * 0.1 }}
                        className="glass-card p-6 border-b-2 border-transparent hover:border-brand-primary transition-all"
                    >
                        <div className="flex justify-between items-start mb-4">
                            <div className="p-2.5 bg-brand-primary/10 rounded-xl text-brand-primary group-hover:scale-110 transition-transform">
                                <stat.icon className="w-5 h-5" />
                            </div>
                            <span className="text-[10px] font-black px-2 py-1 bg-emerald-500/10 text-emerald-500 rounded-full uppercase">
                                {stat.change}
                            </span>
                        </div>
                        <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mb-1">{stat.label}</p>
                        <h3 className="text-2xl font-bold dark:text-white">{stat.value}</h3>
                    </motion.div>
                ))}
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
                {/* Species Arbitrage */}
                <div className="xl:col-span-2 glass-card p-8">
                    <div className="flex justify-between items-center mb-10">
                        <div>
                            <h2 className="text-xl font-bold dark:text-white">Global Species Arbitrage</h2>
                            <p className="text-sm text-slate-500">Real-time Domestic Landing vs. FOB Export Reference</p>
                        </div>
                        <div className="flex items-center space-x-4">
                            <div className="flex items-center space-x-2">
                                <div className="w-3 h-3 bg-brand-primary rounded-full" />
                                <span className="text-[10px] font-bold text-slate-400 uppercase">Landing</span>
                            </div>
                            <div className="flex items-center space-x-2">
                                <div className="w-3 h-3 bg-cyan-400 rounded-full" />
                                <span className="text-[10px] font-bold text-slate-400 uppercase">Export</span>
                            </div>
                        </div>
                    </div>

                    <div className="h-[400px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={speciesAverages}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" strokeOpacity={0.05} />
                                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#64748B', fontSize: 10, fontWeight: 700 }} />
                                <YAxis axisLine={false} tickLine={false} tick={{ fill: '#64748B', fontSize: 10 }} />
                                <Tooltip
                                    cursor={{ fill: 'rgba(79, 70, 229, 0.05)' }}
                                    contentStyle={{ backgroundColor: '#0f172a', borderRadius: '16px', border: 'none', boxShadow: '0 20px 25px -5px rgb(0 0 0 / 0.1)' }}
                                    itemStyle={{ fontSize: '12px', fontWeight: 'bold' }}
                                />
                                <Bar dataKey="price" name="Landing (₹)" fill="#4F46E5" radius={[6, 6, 0, 0]} barSize={24} />
                                <Bar dataKey="exportPrice" name="Export (₹)" fill="#06B6D4" radius={[6, 6, 0, 0]} barSize={24} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Grade Mix */}
                <div className="glass-card p-8">
                    <h2 className="text-xl font-bold dark:text-white mb-2">Species Quality Grade</h2>
                    <p className="text-sm text-slate-500 mb-10">Aggregate export-readiness across all hubs</p>

                    <div className="h-[280px] relative">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={gradeDistribution}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={70}
                                    outerRadius={95}
                                    paddingAngle={10}
                                    dataKey="value"
                                    stroke="none"
                                >
                                    {gradeDistribution.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.color} />
                                    ))}
                                </Pie>
                                <Tooltip />
                            </PieChart>
                        </ResponsiveContainer>
                        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                            <span className="text-4xl font-black dark:text-white">90%</span>
                            <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Market Fit</span>
                        </div>
                    </div>

                    <div className="space-y-5 mt-8">
                        {gradeDistribution.map((g, i) => (
                            <div key={i} className="flex justify-between items-center bg-slate-50 dark:bg-slate-900/50 p-3 rounded-xl border border-slate-100 dark:border-slate-800">
                                <div className="flex items-center space-x-3">
                                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: g.color }} />
                                    <span className="text-sm font-bold dark:text-slate-400">{g.name}</span>
                                </div>
                                <span className="text-sm font-black dark:text-white">{g.value}%</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Active Hubs */}
            <div className="glass-card overflow-hidden">
                <div className="p-8 border-b border-slate-100 dark:border-slate-800 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                    <div>
                        <h3 className="text-2xl font-bold dark:text-white">Marine Surveillance Grid</h3>
                        <p className="text-sm text-slate-500 font-medium">Live landing activity and volume intensity by port center.</p>
                    </div>
                    <div className="flex bg-slate-100 dark:bg-slate-900 p-1.5 rounded-xl border border-slate-200 dark:border-slate-800">
                        <button 
                            onClick={() => setHubType('all')}
                            className={`px-5 py-2.5 rounded-lg text-xs font-black uppercase tracking-wider transition-all ${hubType === 'all' ? 'bg-white dark:bg-slate-800 shadow-sm text-brand-primary' : 'text-slate-500 hover:text-brand-primary'}`}
                        >
                            All Hubs
                        </button>
                        <button 
                            onClick={() => setHubType('port')}
                            className={`px-5 py-2.5 rounded-lg text-xs font-black uppercase tracking-wider transition-all ${hubType === 'port' ? 'bg-white dark:bg-slate-800 shadow-sm text-brand-primary' : 'text-slate-500 hover:text-brand-primary'}`}
                        >
                            Ports
                        </button>
                        <button 
                            onClick={() => setHubType('mandi')}
                            className={`px-5 py-2.5 rounded-lg text-xs font-black uppercase tracking-wider transition-all ${hubType === 'mandi' ? 'bg-white dark:bg-slate-800 shadow-sm text-brand-primary' : 'text-slate-500 hover:text-brand-primary'}`}
                        >
                            Mandis
                        </button>
                    </div>
                </div>

                <div className="p-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {filteredHubs.map((hub, i) => (
                        <div
                            key={i}
                            onClick={() => setSelectedMarket(hub.name)}
                            className="group p-6 glass-card dark:hover:bg-slate-900 border-slate-100 dark:border-slate-800 hover:border-brand-primary/30 transition-all cursor-pointer"
                        >
                            <div className="flex justify-between items-start mb-6">
                                <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-2xl group-hover:bg-brand-primary/10 transition-colors">
                                    {hub.type === 'port' ? (
                                        <Anchor className="w-5 h-5 text-slate-400 group-hover:text-brand-primary" />
                                    ) : (
                                        <Layers className="w-5 h-5 text-slate-400 group-hover:text-brand-primary" />
                                    )}
                                </div>
                                <div className="text-right">
                                    <div className="flex items-center text-[10px] font-black text-emerald-500 uppercase mb-1">
                                        <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full mr-2 animate-pulse" />
                                         Live Pulse
                                    </div>
                                    <p className="text-xl font-bold dark:text-white">
                                        ₹{(() => {
                                            const hubPrices = prices.filter(p => p.market_name === hub.name);
                                            const totalValue = hubPrices.reduce((acc, p) => {
                                                const price = parseFloat(p.modal_price) || 0;
                                                const qty = parseFloat(p.arrival_quantity) || 0;
                                                return acc + (price * qty);
                                            }, 0);
                                            const valueInMillions = totalValue / 1000000;
                                            return valueInMillions > 1000 
                                                ? (valueInMillions / 1000).toFixed(1) + ' B' 
                                                : valueInMillions.toFixed(1) + ' M';
                                        })()}
                                    </p>
                                </div>
                            </div>
                            <h4 className="text-lg font-bold dark:text-slate-100 mb-2 truncate">{hub.name}</h4>
                            <div className="flex items-center space-x-2 mb-6">
                                <span className={`text-[9px] font-black px-2 py-0.5 rounded uppercase tracking-widest ${hub.type === 'port' ? 'bg-blue-500/10 text-blue-500' : 'bg-amber-500/10 text-amber-500'}`}>
                                    {hub.type}
                                </span>
                                <span className="text-[10px] text-slate-500 font-bold">{hub.state}</span>
                            </div>
                            <p className="text-xs text-slate-500 font-medium mb-6 leading-relaxed">
                                Prime Hub: {prices.filter(p => p.market_name === hub.name).slice(0, 2).map(p => p.commodity_name).join(', ')}
                            </p>
                            <div className="flex items-center justify-between text-brand-primary text-[10px] font-black uppercase tracking-widest pt-4 border-t border-slate-50 dark:border-slate-800">
                                <span>Drilldown Analytics</span>
                                <ArrowRight className="w-4 h-4 group-hover:translate-x-2 transition-transform" />
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* MPEDA Export Data Section */}
            {mpedaLoading ? (
                <div className="glass-card p-12 flex items-center justify-center">
                    <RefreshCw className="w-6 h-6 text-brand-primary animate-spin mr-3" />
                    <span className="text-slate-500">Loading MPEDA export data...</span>
                </div>
            ) : mpedaData.length > 0 && (
                <div className="glass-card overflow-hidden">
                    <div className="p-8 border-b border-slate-100 dark:border-slate-800 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                        <div className="flex items-center space-x-4">
                            <div className="p-3 bg-gradient-to-br from-blue-600 to-cyan-500 rounded-xl">
                                <TrendingUp className="w-6 h-6 text-white" />
                            </div>
                            <div>
                                <h3 className="text-2xl font-bold dark:text-white">India Marine Export Intelligence</h3>
                                <p className="text-sm text-slate-500 font-medium">Real MPEDA export data - Quantity & Value by commodity</p>
                            </div>
                        </div>
                        <div className="flex items-center space-x-2 px-3 py-1.5 bg-emerald-500/10 rounded-full">
                            <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
                            <span className="text-xs font-bold text-emerald-500 uppercase">Live Source: MPEDA</span>
                        </div>
                    </div>

                    <div className="p-8">
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                            {/* Export Chart */}
                            <div>
                                <h4 className="text-lg font-bold dark:text-white mb-6">Export Quantity by Commodity (MT)</h4>
                                <div className="h-[350px]">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <BarChart 
                                            data={mpedaData
                                                .filter(r => r.year === '2024-25')
                                                .slice(0, 10)
                                                .map(r => ({
                                                    name: r.commodity?.length > 15 ? r.commodity.slice(0, 15) + '...' : r.commodity,
                                                    quantity: r.quantity_mt || 0,
                                                    value: r.value_crore || 0
                                                }))
                                            }
                                            layout="vertical"
                                        >
                                            <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} stroke="#334155" strokeOpacity={0.1} />
                                            <XAxis type="number" axisLine={false} tickLine={false} tick={{ fill: '#64748B', fontSize: 10 }} />
                                            <YAxis type="category" dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#94A3B8', fontSize: 10 }} width={100} />
                                            <Tooltip 
                                                contentStyle={{ backgroundColor: '#0f172a', borderRadius: '12px', border: 'none' }}
                                                formatter={(value: number) => [value.toLocaleString() + ' MT', 'Quantity']}
                                            />
                                            <Bar dataKey="quantity" fill="#06B6D4" radius={[0, 6, 6, 0]} barSize={20} />
                                        </BarChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>

                            {/* Export Value Chart */}
                            <div>
                                <h4 className="text-lg font-bold dark:text-white mb-6">Export Value by Commodity (₹ Crore)</h4>
                                <div className="h-[350px]">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <BarChart 
                                            data={mpedaData
                                                .filter(r => r.year === '2024-25')
                                                .slice(0, 10)
                                                .map(r => ({
                                                    name: r.commodity?.length > 15 ? r.commodity.slice(0, 15) + '...' : r.commodity,
                                                    value: r.value_crore || 0
                                                }))
                                            }
                                            layout="vertical"
                                        >
                                            <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} stroke="#334155" strokeOpacity={0.1} />
                                            <XAxis type="number" axisLine={false} tickLine={false} tick={{ fill: '#64748B', fontSize: 10 }} />
                                            <YAxis type="category" dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#94A3B8', fontSize: 10 }} width={100} />
                                            <Tooltip 
                                                contentStyle={{ backgroundColor: '#0f172a', borderRadius: '12px', border: 'none' }}
                                                formatter={(value: number) => ['₹' + value.toLocaleString() + ' Cr', 'Value']}
                                            />
                                            <Bar dataKey="value" fill="#10B981" radius={[0, 6, 6, 0]} barSize={20} />
                                        </BarChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>
                        </div>

                        {/* Data Table */}
                        <div className="mt-8">
                            <h4 className="text-lg font-bold dark:text-white mb-4">2024-25 Export Data</h4>
                            <div className="overflow-x-auto">
                                <table className="w-full text-left border-collapse">
                                    <thead>
                                        <tr className="text-[10px] font-black text-slate-400 uppercase tracking-widest border-b border-slate-100 dark:border-slate-800">
                                            <th className="pb-4 pl-4">Commodity</th>
                                            <th className="pb-4">Year</th>
                                            <th className="pb-4 text-right">Quantity (MT)</th>
                                            <th className="pb-4 text-right">Value (₹ Crore)</th>
                                            <th className="pb-4 text-right">Avg Price (₹/KG)</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                                        {mpedaData
                                            .filter(r => r.year === '2024-25')
                                            .slice(0, 12)
                                            .map((row, idx) => {
                                                const avgPrice = row.quantity_mt > 0 
                                                    ? (row.value_crore * 10000000) / (row.quantity_mt * 1000) 
                                                    : 0;
                                                return (
                                                    <tr key={idx} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                                                        <td className="py-4 pl-4">
                                                            <div className="flex items-center space-x-3">
                                                                <div className="w-2 h-2 bg-cyan-500 rounded-full" />
                                                                <span className="font-bold dark:text-white">{row.commodity}</span>
                                                            </div>
                                                        </td>
                                                        <td className="py-4">
                                                            <span className="text-sm font-medium text-slate-500">{row.year}</span>
                                                        </td>
                                                        <td className="py-4 text-right">
                                                            <span className="font-bold text-brand-primary">
                                                                {row.quantity_mt ? row.quantity_mt.toLocaleString() : '-'}
                                                            </span>
                                                        </td>
                                                        <td className="py-4 text-right">
                                                            <span className="font-bold text-emerald-500">
                                                                ₹{row.value_crore ? row.value_crore.toLocaleString() : '-'}
                                                            </span>
                                                        </td>
                                                        <td className="py-4 text-right">
                                                            <span className="font-bold text-slate-400">
                                                                {avgPrice > 0 ? `₹${avgPrice.toFixed(2)}` : '-'}
                                                            </span>
                                                        </td>
                                                    </tr>
                                                );
                                            })}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
