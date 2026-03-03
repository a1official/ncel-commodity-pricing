"use client";

import dynamic from 'next/dynamic';
import React, { useState, useEffect } from 'react';
import {
    MapPin,
    Navigation,
    Search,
    Filter,
    Layers,
    Maximize2,
    TrendingUp,
    Activity,
    ArrowUpRight
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { fetchMarkets, fetchPrices } from '@/lib/api';
import {
    X,
    TrendingUp as TrendingUpIcon,
    AlertCircle,
    Activity as ActivityIcon,
    DollarSign,
    Box
} from 'lucide-react';

const IndiaMap = dynamic(() => import('@/components/IndiaMap'), {
    ssr: false,
    loading: () => (
        <div className="w-full h-full flex items-center justify-center bg-slate-900/10">
            <div className="flex flex-col items-center space-y-4">
                <div className="w-10 h-10 border-4 border-brand-primary/20 border-t-brand-primary rounded-full animate-spin" />
                <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">Initializing Spatial Engine...</p>
            </div>
        </div>
    )
});

export default function MarketExplorer() {
    const [selectedState, setSelectedState] = useState('All India');
    const [markets, setMarkets] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedMarket, setSelectedMarket] = useState<any | null>(null);
    const [marketPrices, setMarketPrices] = useState<any[]>([]);
    const [pricesLoading, setPricesLoading] = useState(false);

    useEffect(() => {
        async function load() {
            try {
                const data = await fetchMarkets();
                setMarkets(data);
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        }
        load();
    }, []);

    const handleMarketSelect = async (market: any) => {
        setSelectedMarket(market);
        setPricesLoading(true);
        try {
            const prices = await fetchPrices({ market_id: market.id });
            setMarketPrices(prices);
        } catch (err) {
            console.error("Discovery Failed:", err);
            setMarketPrices([]);
        } finally {
            setPricesLoading(false);
        }
    };

    return (
        <div className="relative space-y-8 max-w-[1600px] mx-auto pb-20 overflow-hidden">
            {/* Header */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
                <div>
                    <h1 className="text-4xl font-bold font-display dark:text-white">India Mandi Explorer</h1>
                    <p className="text-slate-500 font-medium mt-2">Spatial price discovery across {markets.length} major agricultural hubs.</p>
                </div>
                <div className="flex space-x-3 w-full md:w-auto">
                    <div className="relative flex-1 md:w-80">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                        <input
                            type="text"
                            placeholder="Search by Mandi, City, or PIN..."
                            className="w-full pl-12 pr-4 py-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-sm font-medium outline-none focus:ring-2 focus:ring-brand-primary/20 transition-all"
                        />
                    </div>
                    <button className="px-5 py-3 glass-card bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-slate-500 flex items-center space-x-2">
                        <Filter className="w-4 h-4" />
                        <span className="text-sm font-bold">Filters</span>
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 h-[750px] items-stretch">
                {/* Mandi List Panel */}
                <div className="glass-card flex flex-col h-full bg-white dark:bg-slate-900/40">
                    <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center">
                        <h3 className="font-bold dark:text-white">Major Trading Hubs</h3>
                        <span className="text-xs font-bold text-slate-400 uppercase tracking-tighter">Live Traffic</span>
                    </div>
                    <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
                        {markets.map((mandi, i) => (
                            <motion.div
                                key={mandi.id}
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: (i % 10) * 0.05 }}
                                onClick={() => handleMarketSelect(mandi)}
                                className={`p-4 rounded-xl border cursor-pointer transition-all group ${selectedMarket?.id === mandi.id ? 'bg-brand-primary/10 border-brand-primary/40 shadow-inner' : 'border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/60'}`}
                            >
                                <div className="flex justify-between items-start mb-2">
                                    <div className="flex items-center space-x-3">
                                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${selectedMarket?.id === mandi.id ? 'bg-brand-primary text-white' : 'bg-slate-100 dark:bg-slate-800'}`}>
                                            <MapPin className="w-4 h-4" />
                                        </div>
                                        <div>
                                            <h4 className="text-sm font-bold dark:text-slate-200">{mandi.name}</h4>
                                            <p className="text-[10px] text-slate-500 font-medium">Terminal ID: {mandi.id}</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center space-x-2">
                                        <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                                        <div className="text-[10px] font-bold text-emerald-500 uppercase tracking-tighter">
                                            Live Discovery
                                        </div>
                                    </div>
                                </div>
                                <div className="flex justify-between items-end mt-4">
                                    <div>
                                        <p className="text-[10px] text-slate-400 font-bold uppercase tracking-tight">Geospatial Link</p>
                                        <p className="text-xs font-bold dark:text-slate-300">
                                            {mandi.lat?.toFixed(2) || '0.00'}, {mandi.lon?.toFixed(2) || '0.00'}
                                        </p>
                                    </div>
                                    <div className="text-right">
                                        <div className="flex items-center space-x-2 text-brand-primary group-hover:underline">
                                            <span className="text-[10px] font-bold uppercase tracking-widest">Connect Node</span>
                                            <ArrowUpRight className="w-3 h-3" />
                                        </div>
                                    </div>
                                </div>
                            </motion.div>
                        ))}
                    </div>
                    <div className="p-4 bg-slate-50/50 dark:bg-slate-900/60 border-t border-slate-100 dark:border-slate-800">
                        <button className="w-full py-3 bg-brand-primary text-white rounded-xl text-xs font-bold flex items-center justify-center space-x-2 shadow-lg shadow-brand-primary/20">
                            <Navigation className="w-4 h-4" />
                            <span>Route Intelligence</span>
                        </button>
                    </div>
                </div>

                {/* Map Visualization Workspace */}
                <div className="lg:col-span-2 relative glass-card bg-slate-100 dark:bg-slate-900/20 overflow-hidden group">
                    <IndiaMap markets={markets} selectedRegion={selectedState} onNodeClick={handleMarketSelect} />

                    {/* Left Map Controls */}
                    <div className="absolute top-6 left-6 z-[40] flex flex-col space-y-2">
                        <button className="p-2.5 bg-white dark:bg-slate-800 rounded-xl shadow-lg border border-slate-200 dark:border-slate-700 hover:text-brand-primary transition-colors">
                            <Layers className="w-5 h-5" />
                        </button>
                        <button className="p-2.5 bg-white dark:bg-slate-800 rounded-xl shadow-lg border border-slate-200 dark:border-slate-700 hover:text-brand-primary transition-colors">
                            <Maximize2 className="w-5 h-5" />
                        </button>
                    </div>

                    <div className="absolute top-6 right-6 z-[40]">
                        <div className="flex items-center space-x-2 bg-white dark:bg-slate-800 px-4 py-2.5 rounded-xl shadow-lg border border-slate-200 dark:border-slate-700">
                            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
                            <span className="text-xs font-bold dark:text-slate-200">Terminal Heatmap Live</span>
                        </div>
                    </div>

                    {/* Terminal Drill-down Panel (Premium Slide-over) */}
                    <AnimatePresence>
                        {selectedMarket && (
                            <motion.div
                                initial={{ x: '100%' }}
                                animate={{ x: 0 }}
                                exit={{ x: '100%' }}
                                transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                                className="absolute inset-y-0 right-0 w-[400px] z-[50] glass-card bg-white/95 dark:bg-slate-900/95 shadow-2xl border-l border-slate-200 dark:border-slate-800 flex flex-col m-1"
                            >
                                <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center bg-brand-primary/5">
                                    <div className="flex items-center space-x-4">
                                        <div className="w-10 h-10 rounded-2xl bg-brand-primary flex items-center justify-center text-white">
                                            <MapPin className="w-5 h-5" />
                                        </div>
                                        <div>
                                            <h3 className="font-bold dark:text-white leading-tight">{selectedMarket.name}</h3>
                                            <p className="text-[10px] font-black text-brand-primary uppercase tracking-widest">Active Discovery Node</p>
                                        </div>
                                    </div>
                                    <button
                                        onClick={() => setSelectedMarket(null)}
                                        className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-colors"
                                    >
                                        <X className="w-5 h-5 text-slate-400" />
                                    </button>
                                </div>

                                <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
                                    {/* Quick Stats Grid */}
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-700/50">
                                            <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">Daily Volume</p>
                                            <p className="text-lg font-bold text-brand-primary">
                                                {marketPrices.reduce((acc, p) => acc + Number(p.arrival_quantity), 0).toFixed(0)} <span className="text-[10px] text-slate-500">Qtl</span>
                                            </p>
                                        </div>
                                        <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-700/50">
                                            <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">Tracked Varieties</p>
                                            <p className="text-lg font-bold text-emerald-500">{new Set(marketPrices.map(p => p.variety_id)).size || '-'}</p>
                                        </div>
                                    </div>

                                    {/* Pricing Intelligence Feed */}
                                    <div className="space-y-4">
                                        <div className="flex justify-between items-center">
                                            <h4 className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em]">Discovery Feed</h4>
                                            <div className="flex items-center space-x-2 text-[10px] font-bold text-emerald-500 bg-emerald-500/10 px-2 py-0.5 rounded-full">
                                                <div className="w-1 h-1 rounded-full bg-emerald-500 animate-pulse" />
                                                <span>LIVE DATA</span>
                                            </div>
                                        </div>

                                        {pricesLoading ? (
                                            <div className="space-y-4 pt-10">
                                                {[1, 2, 3].map(i => (
                                                    <div key={i} className="h-24 w-full bg-slate-50 dark:bg-slate-800/30 animate-pulse rounded-2xl" />
                                                ))}
                                            </div>
                                        ) : marketPrices.length > 0 ? (
                                            marketPrices.map((price, idx) => (
                                                <motion.div
                                                    key={price.id}
                                                    initial={{ opacity: 0, y: 10 }}
                                                    animate={{ opacity: 1, y: 0 }}
                                                    transition={{ delay: idx * 0.05 }}
                                                    className="p-4 rounded-2xl border border-slate-100 dark:border-slate-800 bg-white dark:bg-slate-900/50 hover:border-brand-primary/20 transition-all hover:bg-white dark:hover:bg-slate-900"
                                                >
                                                    <div className="flex justify-between items-start mb-3">
                                                        <div>
                                                            <h5 className="font-bold text-sm dark:text-white capitalize">{price.commodity_name || 'Terminal Feed'}</h5>
                                                            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">{price.variety_name || 'Standard Grade'}</p>
                                                        </div>
                                                        <div className="px-2 py-1 rounded bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                                                            <span className="text-[9px] font-black text-slate-600 dark:text-slate-400 uppercase">{price.unit}</span>
                                                        </div>
                                                    </div>

                                                    <div className="grid grid-cols-3 gap-2 py-3 border-t border-slate-50 dark:border-slate-800/50">
                                                        <div className="text-center">
                                                            <p className="text-[8px] font-black text-slate-400 uppercase tracking-tighter mb-1">Min Price</p>
                                                            <p className="text-xs font-bold dark:text-slate-300">₹{price.min_price}</p>
                                                        </div>
                                                        <div className="text-center bg-brand-primary/5 rounded-lg py-1">
                                                            <p className="text-[8px] font-black text-brand-primary uppercase tracking-tighter mb-1">Modal Index</p>
                                                            <p className="text-sm font-black text-brand-primary">₹{price.modal_price}</p>
                                                        </div>
                                                        <div className="text-center">
                                                            <p className="text-[8px] font-black text-slate-400 uppercase tracking-tighter mb-1">Max Price</p>
                                                            <p className="text-xs font-bold dark:text-slate-300">₹{price.max_price}</p>
                                                        </div>
                                                    </div>

                                                    <div className="mt-2 flex items-center justify-between text-[8px] font-black uppercase tracking-widest text-slate-400">
                                                        <span>Discovery Source: {price.source_name}</span>
                                                        <span className="text-slate-500">Sync: JUST NOW</span>
                                                    </div>
                                                </motion.div>
                                            ))
                                        ) : (
                                            <div className="text-center py-20 bg-slate-50 dark:bg-slate-800/10 rounded-3xl border-2 border-dashed border-slate-100 dark:border-slate-800">
                                                <div className="w-12 h-12 bg-white dark:bg-slate-900 rounded-full flex items-center justify-center mx-auto mb-4 border border-slate-100 dark:border-slate-800 shadow-sm">
                                                    <AlertCircle className="w-6 h-6 text-slate-300" />
                                                </div>
                                                <p className="text-xs font-bold text-slate-400">No signals detected at this node.</p>
                                                <p className="text-[9px] text-slate-500 mt-1 uppercase tracking-widest">Verify sensor connectivity</p>
                                            </div>
                                        )}
                                    </div>
                                </div>

                                <div className="p-6 bg-slate-50 dark:bg-transparent border-t border-slate-100 dark:border-slate-800">
                                    <button className="w-full py-3.5 bg-brand-primary text-white rounded-2xl text-[10px] font-black uppercase tracking-[0.2em] shadow-xl shadow-brand-primary/20 hover:scale-[1.02] active:scale-95 transition-all flex items-center justify-center space-x-3">
                                        <TrendingUpIcon className="w-4 h-4" />
                                        <span>Export Terminal Intelligence</span>
                                    </button>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>

                    {/* Bottom Map Info Card */}
                    <div className="absolute bottom-10 left-10 right-10 z-[40] flex justify-center">
                        <motion.div
                            initial={{ y: 50, opacity: 0 }}
                            animate={{ y: 0, opacity: 1 }}
                            className="p-1 glass-card bg-white/80 dark:bg-slate-900/60 backdrop-blur-xl border border-white/20"
                        >
                            <div className="flex bg-slate-100/50 dark:bg-slate-800/50 rounded-xl p-1">
                                {['All India', 'North Hub', 'South Hub', 'Marine Ports'].map((region) => (
                                    <button
                                        key={region}
                                        onClick={() => setSelectedState(region)}
                                        className={`px-6 py-2 rounded-lg text-xs font-bold transition-all ${selectedState === region ? 'bg-white dark:bg-slate-700 shadow-sm dark:text-white' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}
                                    >
                                        {region}
                                    </button>
                                ))}
                            </div>
                        </motion.div>
                    </div>
                </div>
            </div>

            {/* Grid of Nearby Mandis Details */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {[
                    { icon: TrendingUp, label: 'Highest Volatility', value: 'Maharashtra' },
                    { icon: Activity, label: 'Highest Liquidity', value: 'Delhi' },
                    { icon: MapPin, label: 'Newly Onboarded', value: 'Kochi Port' },
                    { icon: Navigation, label: 'Transit Delays', value: 'Punjab Hub' },
                ].map((stat, i) => (
                    <div key={i} className="glass-card p-5 flex items-center space-x-4 border-l-4 border-l-brand-primary">
                        <div className="p-3 bg-brand-primary/5 rounded-xl text-brand-primary">
                            <stat.icon className="w-5 h-5" />
                        </div>
                        <div>
                            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">{stat.label}</p>
                            <h4 className="font-bold dark:text-slate-200">{stat.value}</h4>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
