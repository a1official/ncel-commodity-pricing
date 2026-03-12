"use client";

import React, { useState, useEffect, useMemo } from 'react';
import {
    Waves, Anchor, Ship, TrendingUp, Download, Filter, MapPin, ExternalLink, ArrowRight, Activity, RefreshCw, X, Search, Package, ChevronRight, ArrowUpRight
} from 'lucide-react';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend
} from 'recharts';
import { motion, AnimatePresence } from 'framer-motion';
import { fetchCommodities, fetchPrices } from '@/lib/api';
import Link from 'next/link';

export default function MarineDashboard() {
    const [commodities, setCommodities] = useState<any[]>([]);
    const [prices, setPrices] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedState, setSelectedState] = useState<string>('All');
    const [search, setSearch] = useState('');
    const [selectedMarket, setSelectedMarket] = useState<string | null>(null);
    const [availableStates, setAvailableStates] = useState<string[]>(['All']);

    useEffect(() => {
        const loadMarineData = async () => {
            setLoading(true);
            try {
                // Try the new optimized endpoints first
                const [comms, marineStates] = await Promise.all([
                    fetchCommodities(),
                    fetch('http://localhost:8000/api/v1/marine/states').then(r => r.json())
                ]);

                const marineComms = comms.filter((c: any) => c.category === "Marine Products");
                setCommodities(marineComms);
                
                // Set all available states from the dedicated endpoint
                setAvailableStates(['All', ...marineStates]);
                
                // Try to get marine summary, fallback to regular prices if it fails
                try {
                    const marineSummary = await fetch('http://localhost:8000/api/v1/marine/summary').then(r => r.json());
                    setPrices(marineSummary.map((item: any) => ({
                        ...item,
                        commodity_name: item.commodity_name,
                        state_name: item.state_name,
                        modal_price: item.modal_price.toString(),
                        source_name: 'FMPIS'
                    })));
                } catch (summaryError) {
                    console.log("Marine summary failed, using fallback API");
                    // Fallback to regular prices API
                    const allPrices = await fetchPrices({ source_name: 'FMPIS' });
                    setPrices(allPrices);
                }
                
            } catch (err) {
                console.error("Marine data load failed", err);
                // Complete fallback to regular API
                const [comms, allPrices] = await Promise.all([
                    fetchCommodities(),
                    fetchPrices({ source_name: 'FMPIS' })
                ]);
                const marineComms = comms.filter((c: any) => c.category === "Marine Products");
                setCommodities(marineComms);
                setPrices(allPrices);
                
                // Fallback: ensure we have all 9 marine states
                const allMarineStates = [
                    "Andhra Pradesh", "Goa", "Gujarat", "Karnataka", "Kerala", 
                    "Maharashtra", "Odisha", "Tamil Nadu", "West Bengal"
                ];
                setAvailableStates(['All', ...allMarineStates]);
            } finally {
                setLoading(false);
            }
        };
        loadMarineData();
    }, []);

    // Filter commodities based on state and search
    const filteredCommodities = useMemo(() => {
        return commodities.filter(c => {
            const matchesSearch = c.name.toLowerCase().includes(search.toLowerCase());
            
            if (selectedState === 'All') {
                return matchesSearch;
            }
            
            // Check if this commodity has prices in the selected state
            const hasDataInState = prices.some(p => 
                p.commodity_name === c.name && p.state_name === selectedState
            );
            
            return matchesSearch && hasDataInState;
        });
    }, [commodities, selectedState, search, prices]);

    // Get commodity data with latest prices for display
    const commodityData = useMemo(() => {
        return filteredCommodities.map(commodity => {
            // Get prices for this commodity
            let commodityPrices = prices.filter(p => p.commodity_name === commodity.name);
            
            // Filter by state if not 'All'
            if (selectedState !== 'All') {
                commodityPrices = commodityPrices.filter(p => p.state_name === selectedState);
            }
            
            if (commodityPrices.length === 0) {
                return {
                    ...commodity,
                    latestPrice: 0,
                    priceChange: 0,
                    marketCount: 0,
                    stateCount: 0,
                    lastUpdated: null
                };
            }
            
            // Calculate statistics
            const prices_values = commodityPrices.map(p => parseFloat(p.modal_price));
            const avgPrice = prices_values.reduce((a, b) => a + b, 0) / prices_values.length;
            const marketCount = new Set(commodityPrices.map(p => p.market_name)).size;
            const stateCount = new Set(commodityPrices.map(p => p.state_name)).size;
            
            // Get latest price (most recent date)
            const sortedPrices = commodityPrices.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
            const latestPrice = sortedPrices[0]?.modal_price || 0;
            const lastUpdated = sortedPrices[0]?.date;
            
            // Calculate price change (mock for now)
            const priceChange = Math.random() > 0.5 ? Math.random() * 10 : -Math.random() * 10;
            
            return {
                ...commodity,
                latestPrice: parseFloat(latestPrice),
                avgPrice: Math.round(avgPrice),
                priceChange: Math.round(priceChange * 100) / 100,
                marketCount,
                stateCount,
                lastUpdated,
                recordCount: commodityPrices.length
            };
        });
    }, [filteredCommodities, prices, selectedState]);

    const marketPrices = useMemo(() => {
        if (!selectedMarket) return [];
        return prices.filter(p => p.market_name === selectedMarket);
    }, [selectedMarket, prices]);

    if (loading) {
        return (
            <div className="min-h-[60vh] flex flex-col items-center justify-center space-y-4">
                <RefreshCw className="w-10 h-10 text-brand-primary animate-spin" />
                <p className="text-sm font-bold text-slate-500 animate-pulse uppercase tracking-widest">Loading Marine Intelligence...</p>
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
                                                    <span className="text-[8px] font-black text-slate-400 uppercase ml-1">/Kg</span>
                                                </td>
                                                <td className="py-5">
                                                    <p className="font-bold dark:text-slate-300">{p.arrival_quantity} Kg</p>
                                                </td>
                                                <td className="py-5 text-xs font-bold text-slate-400 italic">
                                                    {new Date(p.date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}
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
                        <p className="text-slate-500 font-medium">Tracking {commodities.length} marine species across {availableStates.length - 1} coastal states.</p>
                    </div>
                </div>
                <div className="flex space-x-3">
                    <div className="relative">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                        <input
                            type="text"
                            placeholder="Search marine species..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="pl-11 pr-4 py-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-sm font-medium outline-none focus:ring-2 focus:ring-brand-primary/20 transition-all w-64"
                        />
                    </div>
                    <button className="flex items-center space-x-2 px-6 py-3 bg-brand-primary text-white rounded-xl text-sm font-bold shadow-lg shadow-brand-primary/20 hover:scale-[1.02] transition-all">
                        <Download className="w-4 h-4" />
                        <span>Export Data</span>
                    </button>
                </div>
            </div>

            {/* State Filter */}
            <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2">
                    <MapPin className="w-4 h-4 text-slate-400" />
                    <span className="text-sm font-bold text-slate-600 dark:text-slate-400">Filter by State:</span>
                </div>
                <div className="flex space-x-2 overflow-x-auto pb-1">
                    {availableStates.map((state) => (
                        <button
                            key={state}
                            onClick={() => setSelectedState(state)}
                            className={`px-4 py-2 rounded-lg text-xs font-bold whitespace-nowrap transition-all ${selectedState === state
                                ? 'bg-brand-primary text-white shadow-lg shadow-brand-primary/20'
                                : 'bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
                                }`}
                        >
                            {state}
                        </button>
                    ))}
                </div>
            </div>

            {/* Marine Commodities Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
                {commodityData.map((commodity, idx) => (
                    <motion.div
                        key={commodity.id}
                        initial={{ opacity: 0, y: 16 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.3, delay: idx * 0.04 }}
                    >
                        <Link href={`/commodities/${commodity.id}`} className="block">
                            <div className="glass-card p-6 group cursor-pointer hover:shadow-xl hover:border-brand-primary/20 transition-all duration-300 h-full flex flex-col">
                                <div className="flex justify-between items-start mb-5">
                                    <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-2xl flex items-center justify-center text-2xl group-hover:scale-110 transition-transform duration-300">
                                        🐟
                                    </div>
                                    <div className="flex items-center space-x-1 px-2.5 py-1 rounded-lg text-[10px] font-bold bg-emerald-500/10 text-emerald-500">
                                        <ArrowUpRight className="w-3 h-3" />
                                        <span>LIVE</span>
                                    </div>
                                </div>

                                <div className="mb-4">
                                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">Marine Products</p>
                                    <h3 className="text-base font-bold dark:text-white leading-tight">{commodity.name}</h3>
                                </div>

                                <div className="space-y-3 mb-4">
                                    <div className="flex justify-between items-center">
                                        <span className="text-xs text-slate-500">Latest Price</span>
                                        <span className="text-lg font-black text-brand-primary">
                                            ₹{commodity.latestPrice.toLocaleString()}
                                        </span>
                                    </div>
                                    
                                    <div className="flex justify-between items-center">
                                        <span className="text-xs text-slate-500">Markets</span>
                                        <span className="text-sm font-bold dark:text-white">{commodity.marketCount}</span>
                                    </div>
                                    
                                    {selectedState === 'All' && (
                                        <div className="flex justify-between items-center">
                                            <span className="text-xs text-slate-500">States</span>
                                            <span className="text-sm font-bold dark:text-white">{commodity.stateCount}</span>
                                        </div>
                                    )}
                                    
                                    <div className="flex justify-between items-center">
                                        <span className="text-xs text-slate-500">Records</span>
                                        <span className="text-sm font-bold text-slate-400">{commodity.recordCount}</span>
                                    </div>
                                </div>

                                <div className="mt-auto pt-5 border-t border-slate-100 dark:border-slate-800 flex justify-between items-center">
                                    <span className="text-xs font-bold text-brand-primary">View Details</span>
                                    <ChevronRight className="w-4 h-4 text-slate-300 dark:text-slate-600 group-hover:text-brand-primary group-hover:translate-x-0.5 transition-all" />
                                </div>
                            </div>
                        </Link>
                    </motion.div>
                ))}
            </div>

            {commodityData.length === 0 && (
                <div className="text-center py-20 glass-card">
                    <Waves className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                    <p className="text-slate-500 font-medium">
                        {search ? 'No marine species matched your search.' : 
                         selectedState !== 'All' ? `No marine data available for ${selectedState}.` : 
                         'No marine data available.'}
                    </p>
                </div>
            )}
        </div>
    );
}


