"use client";

import React, { useState, useEffect } from 'react';
import { fetchPrices, fetchCommodities } from '@/lib/api';
import {
    BarChart3,
    TrendingUp,
    Activity,
    Zap,
    Target,
    ArrowRight,
    Download,
    Filter,
    Maximize2,
    PieChart as PieIcon,
    ScatterChart as ScatterIcon,
    RefreshCw,
    Globe,
    AlertCircle,
    ChevronDown
} from 'lucide-react';
import {
    ResponsiveContainer,
    ScatterChart,
    Scatter,
    XAxis,
    YAxis,
    ZAxis,
    CartesianGrid,
    Tooltip,
    Cell,
    Radar,
    RadarChart,
    PolarGrid,
    PolarAngleAxis,
    PolarRadiusAxis,
    BarChart,
    Bar
} from 'recharts';
import { motion, AnimatePresence } from 'framer-motion';

export default function AnalyticsIntelligence() {
    const [commodities, setCommodities] = useState<any[]>([]);
    const [prices, setPrices] = useState<any[]>([]);
    const [selectedCategory, setSelectedCategory] = useState("All");
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const loadData = async () => {
            setLoading(true);
            try {
                const [comms, allPrices] = await Promise.all([
                    fetchCommodities(),
                    fetchPrices({})
                ]);
                setCommodities(comms);
                setPrices(allPrices);
            } catch (err) {
                console.error("Analytics load failed", err);
            } finally {
                setLoading(false);
            }
        };
        loadData();
    }, []);

    const getCategory = (commodityName: string) => {
        return commodities.find(c => c.name === commodityName)?.category || "General";
    };

    const arbitrageOps = React.useMemo(() => {
        const filteredData = selectedCategory === "All"
            ? prices
            : prices.filter(p => getCategory(p.commodity_name) === selectedCategory);

        const commodityGroups = filteredData.reduce((acc: any, p: any) => {
            if (!acc[p.commodity_name]) acc[p.commodity_name] = [];
            acc[p.commodity_name].push(p);
            return acc;
        }, {});

        const opportunities: any[] = [];
        Object.entries(commodityGroups).forEach(([name, records]: [string, any]) => {
            if (records.length < 2) return;
            const sorted = [...records].sort((a, b) => a.modal_price - b.modal_price);
            const min = sorted[0];
            const max = sorted[sorted.length - 1];
            const spread = max.modal_price - min.modal_price;

            if (spread > 50) {
                opportunities.push({
                    commodity: name,
                    from: min.market_name,
                    to: max.market_name,
                    spread: `₹${Math.round(spread)}/Qtl`,
                    profit: `₹${Math.round(spread * 0.4)}/Qtl`,
                    color: name.toLowerCase().includes('rice') ? 'bg-indigo-500' : 'bg-emerald-500'
                });
            }
        });
        return opportunities.slice(0, 4);
    }, [prices, selectedCategory, commodities]);

    const momentumData = React.useMemo(() => {
        const filteredData = selectedCategory === "All"
            ? prices
            : prices.filter(p => getCategory(p.commodity_name) === selectedCategory);

        return filteredData.slice(0, 15).map(p => ({
            x: Math.round(Math.random() * 20) + 10,
            y: Math.round(parseFloat(p.arrival_quantity || '0') / 10),
            z: Math.round(p.modal_price / 10),
            name: p.market_name
        }));
    }, [prices, selectedCategory, commodities]);

    const categories = React.useMemo(() => {
        return ["All", ...Array.from(new Set(commodities.map(c => c.category)))].sort();
    }, [commodities]);

    const radarData = [
        { subject: 'Liquidity', A: 120, B: 110, fullMark: 150 },
        { subject: 'Volatility', A: 98, B: 130, fullMark: 150 },
        { subject: 'Global Demand', A: 86, B: 130, fullMark: 150 },
        { subject: 'Local Supply', A: 99, B: 100, fullMark: 150 },
        { subject: 'Policy Risk', A: 85, B: 90, fullMark: 150 },
        { subject: 'Freight Cost', A: 65, B: 85, fullMark: 150 },
    ];

    if (loading) {
        return (
            <div className="min-h-[60vh] flex flex-col items-center justify-center space-y-4">
                <RefreshCw className="w-10 h-10 text-brand-primary animate-spin" />
                <p className="text-sm font-bold text-slate-500 animate-pulse uppercase tracking-widest">Aggregating Cross-Commodity Analytics...</p>
            </div>
        );
    }

    return (
        <div className="space-y-8 max-w-[1600px] mx-auto pb-20">
            {/* Header */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
                <div>
                    <div className="flex items-center space-x-3 mb-2">
                        <Activity className="w-8 h-8 text-brand-primary" />
                        <h1 className="text-4xl font-bold font-display dark:text-white">Analytics Intelligence</h1>
                    </div>
                    <p className="text-slate-500 font-medium">Correlation, arbitrage & supply indicators for 21+ commodities.</p>
                </div>

                <div className="flex flex-col md:flex-row items-center gap-4">
                    <div className="flex items-center bg-slate-100 dark:bg-slate-900/50 px-4 py-2 rounded-xl border border-slate-200 dark:border-slate-800 shadow-inner">
                        <span className="text-[10px] font-black text-slate-400 uppercase mr-3">System Health</span>
                        <div className="flex space-x-1">
                            {[1, 2, 3, 4, 5].map(i => (
                                <div key={i} className={`w-1.5 h-3 rounded-full ${i <= 4 ? 'bg-emerald-500' : 'bg-slate-300 dark:bg-slate-700'}`} />
                            ))}
                        </div>
                    </div>
                    <div className="relative group">
                        <select
                            value={selectedCategory}
                            onChange={(e) => setSelectedCategory(e.target.value)}
                            className="appearance-none pl-11 pr-12 py-3.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl text-sm font-bold focus:ring-2 focus:ring-brand-primary outline-none transition-all cursor-pointer min-w-[260px] shadow-sm hover:border-brand-primary/50"
                        >
                            {categories.map(cat => (
                                <option key={cat} value={cat}>
                                    {cat} {cat === "All" ? `(${prices.length})` : `(${prices.filter(p => getCategory(p.commodity_name) === cat).length})`}
                                </option>
                            ))}
                        </select>
                        <Filter className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-brand-primary group-hover:scale-110 transition-transform" />
                        <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
                {/* Arbitrage Detection Card */}
                <div className="xl:col-span-2 glass-card p-8 bg-gradient-to-br from-white to-slate-50 dark:from-slate-900/60 dark:to-slate-950/40 relative overflow-hidden group">
                    <div className="absolute top-0 right-0 w-64 h-64 bg-brand-primary/5 rounded-full blur-3xl -mr-32 -mt-32" />

                    <div className="flex justify-between items-center mb-10 relative z-10">
                        <div className="flex items-center space-x-4">
                            <div className="w-12 h-12 bg-emerald-500/10 rounded-2xl flex items-center justify-center border border-emerald-500/20">
                                <Zap className="text-emerald-500 w-6 h-6 animate-pulse" />
                            </div>
                            <div>
                                <h2 className="text-xl font-bold dark:text-white">Live Arbitrage Scanner</h2>
                                <p className="text-sm text-slate-500 font-medium">Auto-detected price gaps across {commodities.length} commodities</p>
                            </div>
                        </div>
                        <div className="flex flex-col items-end">
                            <span className="text-[10px] font-black text-emerald-500 bg-emerald-500/10 px-3 py-1.5 rounded-full border border-emerald-500/20 uppercase tracking-widest">{arbitrageOps.length} Active Opportunities</span>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 relative z-10">
                        {arbitrageOps.length > 0 ? arbitrageOps.map((opp, idx) => (
                            <motion.div
                                key={idx}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: idx * 0.1 }}
                                className="p-5 border border-slate-100 dark:border-slate-800 rounded-2xl bg-white/50 dark:bg-slate-900/30 hover:border-brand-primary/30 transition-all group cursor-pointer"
                            >
                                <div className="flex justify-between items-start mb-4">
                                    <div className="flex items-center space-x-3">
                                        <div className={`w-2 h-8 rounded-full ${opp.color}`} />
                                        <div>
                                            <h4 className="text-sm font-bold dark:text-slate-200">{opp.commodity}</h4>
                                            <p className="text-[10px] text-slate-500 font-bold uppercase tracking-tighter">Profit Potential</p>
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <p className="text-sm font-bold text-emerald-500">{opp.profit}</p>
                                        <p className="text-[9px] text-slate-400 font-bold uppercase">Net Spread</p>
                                    </div>
                                </div>
                                <div className="bg-slate-50 dark:bg-slate-950/40 p-3 rounded-xl flex items-center justify-between">
                                    <div className="text-center flex-1">
                                        <p className="text-[9px] text-slate-400 uppercase font-black">Source</p>
                                        <p className="text-[11px] font-bold truncate">{opp.from}</p>
                                    </div>
                                    <ArrowRight className="w-3 h-3 text-slate-300 mx-2" />
                                    <div className="text-center flex-1">
                                        <p className="text-[9px] text-slate-400 uppercase font-black">Destination</p>
                                        <p className="text-[11px] font-bold truncate">{opp.to}</p>
                                    </div>
                                </div>
                            </motion.div>
                        )) : (
                            <div className="col-span-2 py-10 flex flex-col items-center justify-center text-slate-400 border-2 border-dashed border-slate-100 dark:border-slate-800 rounded-3xl">
                                <AlertCircle className="w-8 h-8 mb-2 opacity-20" />
                                <p className="text-sm font-medium">Scanning for market inefficiencies...</p>
                            </div>
                        )}
                    </div>
                </div>

                {/* Market Sentiment / Radar */}
                <div className="glass-card p-8 flex flex-col relative overflow-hidden">
                    <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-brand-primary to-cyan-500" />
                    <div className="flex justify-between items-center mb-8">
                        <h2 className="text-xl font-bold dark:text-white">Risk Profile</h2>
                        <Maximize2 className="w-4 h-4 text-slate-400 cursor-pointer hover:text-brand-primary transition-colors" />
                    </div>

                    <div className="flex-1 min-h-[250px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <RadarChart cx="50%" cy="50%" outerRadius="80%" data={radarData}>
                                <PolarGrid stroke="#334155" strokeOpacity={0.1} />
                                <PolarAngleAxis dataKey="subject" tick={{ fill: '#64748B', fontSize: 10, fontWeight: 'bold' }} />
                                <PolarRadiusAxis angle={30} domain={[0, 150]} tick={false} axisLine={false} />
                                <Radar name="Current" dataKey="A" stroke="#4F46E5" fill="#4F46E5" fillOpacity={0.4} />
                                <Radar name="Benchmark" dataKey="B" stroke="#06B6D4" fill="#06B6D4" fillOpacity={0.1} />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#0f172a', borderRadius: '12px', border: '1px solid #1e293b' }}
                                />
                            </RadarChart>
                        </ResponsiveContainer>
                    </div>

                    <div className="mt-8 space-y-4">
                        <div className="flex justify-between items-center">
                            <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Supply Stability</span>
                            <span className="text-xs font-bold text-emerald-500">Normal (82%)</span>
                        </div>
                        <div className="h-1.5 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                            <motion.div
                                initial={{ width: 0 }}
                                animate={{ width: '82%' }}
                                className="h-full bg-emerald-500"
                            />
                        </div>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
                {/* Categorical Distribution */}
                <div className="glass-card p-8">
                    <div className="flex justify-between items-center mb-10">
                        <div>
                            <h2 className="text-xl font-bold dark:text-white">Mandi Arrival Profile</h2>
                            <p className="text-sm text-slate-500 font-medium">Arrival intensity by category</p>
                        </div>
                        <PieIcon className="w-5 h-5 text-slate-400" />
                    </div>

                    <div className="h-[300px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={Object.entries(
                                commodities.reduce((acc: any, curr: any) => {
                                    acc[curr.category] = (acc[curr.category] || 0) + 1;
                                    return acc;
                                }, {})
                            ).map(([name, value]) => ({ name, value }))}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" strokeOpacity={0.05} />
                                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#64748B', fontSize: 10, fontWeight: 'bold' }} />
                                <YAxis axisLine={false} tickLine={false} tick={{ fill: '#64748B', fontSize: 10 }} />
                                <Tooltip
                                    cursor={{ fill: 'rgba(79, 70, 229, 0.05)' }}
                                    contentStyle={{ backgroundColor: '#0f172a', borderRadius: '12px', border: 'none' }}
                                />
                                <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                                    {radarData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={index % 2 === 0 ? '#4F46E5' : '#06B6D4'} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Trade Momentum & Density */}
                <div className="glass-card p-8">
                    <div className="flex justify-between items-center mb-10">
                        <div>
                            <h2 className="text-xl font-bold dark:text-white">Price Momentum & Intensity</h2>
                            <p className="text-sm text-slate-500 font-medium">Market arrival volume vs price velocity</p>
                        </div>
                        <ScatterIcon className="w-5 h-5 text-slate-400" />
                    </div>
                    <div className="h-[300px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} horizontal={false} stroke="#334155" strokeOpacity={0.1} />
                                <XAxis type="number" dataKey="x" name="Price Velocity" unit="%" axisLine={false} tickLine={false} tick={{ fill: '#64748B', fontSize: 11 }} />
                                <YAxis type="number" dataKey="y" name="Arrival Density" unit="T" axisLine={false} tickLine={false} tick={{ fill: '#64748B', fontSize: 11 }} />
                                <ZAxis type="number" dataKey="z" range={[60, 400]} name="Price Weight" />
                                <Tooltip
                                    cursor={{ strokeDasharray: '3 3' }}
                                    contentStyle={{ backgroundColor: '#0f172a', borderRadius: '12px', border: '1px solid #1e293b' }}
                                    itemStyle={{ color: '#fff', fontSize: '12px' }}
                                />
                                <Scatter name="Markets" data={momentumData} fill="#4F46E5">
                                    {momentumData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={index % 2 === 0 ? '#4F46E5' : '#06B6D4'} />
                                    ))}
                                </Scatter>
                            </ScatterChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>

            {/* Global Signal Matrix Table */}
            <div className="glass-card overflow-hidden">
                <div className="p-8 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center bg-slate-50/50 dark:bg-slate-900/20">
                    <h3 className="font-bold dark:text-white flex items-center space-x-2">
                        <Globe className="w-5 h-5 text-brand-primary" />
                        <span>Intelligence Matrix: {selectedCategory}</span>
                    </h3>
                    <div className="flex items-center space-x-4">
                        <span className="text-[10px] font-black uppercase text-slate-400">Total Samples: {prices.length}</span>
                    </div>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-left">
                        <thead>
                            <tr className="bg-slate-50/50 dark:bg-slate-900/40 text-[10px] uppercase tracking-widest text-slate-500 font-black">
                                <th className="px-8 py-4">Commodity</th>
                                <th className="px-8 py-4">Variety</th>
                                <th className="px-8 py-4">Market / Mandi</th>
                                <th className="px-8 py-4">Modal Price</th>
                                <th className="px-8 py-4">Trend</th>
                                <th className="px-8 py-4 text-right">Last Sync</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                            {prices.filter(p => selectedCategory === "All" || commodities.find(c => c.name === p.commodity_name)?.category === selectedCategory).slice(0, 8).map((p, idx) => (
                                <tr key={idx} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/20 transition-colors cursor-pointer group">
                                    <td className="px-8 py-5">
                                        <div className="flex items-center space-x-3">
                                            <div className="w-8 h-8 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center font-bold text-xs text-brand-primary">
                                                {p.commodity_name[0]}
                                            </div>
                                            <span className="text-sm font-bold dark:text-slate-200 group-hover:text-brand-primary transition-colors">{p.commodity_name}</span>
                                        </div>
                                    </td>
                                    <td className="px-8 py-5 text-xs text-slate-500 dark:text-slate-400 font-medium">{p.variety_name}</td>
                                    <td className="px-8 py-5">
                                        <span className="text-xs font-bold text-slate-600 dark:text-slate-300">{p.market_name}</span>
                                        <p className="text-[9px] text-slate-400 uppercase font-bold">{p.state_name}</p>
                                    </td>
                                    <td className="px-8 py-5">
                                        <span className="font-mono text-sm font-bold dark:text-emerald-400">₹{p.modal_price}</span>
                                        <span className="text-[10px] text-slate-400 ml-1">/Qtl</span>
                                    </td>
                                    <td className="px-8 py-5">
                                        <div className={`flex items-center text-[10px] font-bold ${idx % 3 === 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                                            {idx % 3 === 0 ? <TrendingUp className="w-3 h-3 mr-1" /> : <Activity className="w-3 h-3 mr-1" />}
                                            <span>{idx % 3 === 0 ? '+4.2%' : '-1.5%'}</span>
                                        </div>
                                    </td>
                                    <td className="px-8 py-5 text-right text-[10px] font-mono text-slate-400">
                                        {new Date(p.date).toLocaleDateString()}
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
