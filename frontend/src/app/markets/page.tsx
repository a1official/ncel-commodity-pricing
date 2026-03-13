"use client";

import dynamic from 'next/dynamic';
import React, { useState, useEffect, useMemo } from 'react';
import {
    MapPin,
    Navigation,
    Search,
    Filter,
    Layers,
    Maximize2,
    TrendingUp,
    Activity,
    ArrowUpRight,
    X,
    AlertCircle,
    ArrowUpRight as ArrowUpRightIcon,
    Box
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { fetchMarkets, fetchPrices } from '@/lib/api';

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
    const [searchQuery, setSearchQuery] = useState('');

    useEffect(() => {
        async function load() {
            try {
                const data = await fetchMarkets();
                setMarkets(Array.isArray(data) ? data : []);
            } catch (err) {
                console.error("Market Discovery Error:", err);
                setMarkets([]);
            } finally {
                setLoading(false);
            }
        }
        load();
    }, []);

    const filteredMarkets = useMemo(() => {
        let result = markets;
        
        // Apply State/Region filter
        if (selectedState !== 'All India') {
            if (selectedState === 'Marine Ports') {
                result = result.filter(m => 
                    m.state_name === 'Coastal Hub' || 
                    (m.name || '').toLowerCase().includes('port') || 
                    (m.name || '').toLowerCase().includes('harbour') ||
                    (m.name || '').toLowerCase().includes('marine') ||
                    (m.name || '').toLowerCase().includes('landing')
                );
            } else {
                result = result.filter(m => m.state_name === selectedState);
            }
        }

        // Apply Search filter
        if (searchQuery.trim()) {
            const query = searchQuery.toLowerCase();
            result = result.filter(m => 
                (m.name || '').toLowerCase().includes(query) || 
                (m.state_name || '').toLowerCase().includes(query) ||
                (m.district_name || '').toLowerCase().includes(query)
            );
        }

        return result;
    }, [markets, selectedState, searchQuery]);

    const handleMarketSelect = async (market: any) => {
        setSelectedMarket(market);
        setPricesLoading(true);
        try {
            const prices = await fetchPrices({ market_id: market.id });
            setMarketPrices(Array.isArray(prices) ? prices : []);
        } catch (err) {
            console.error("Price Discovery Failed:", err);
            setMarketPrices([]);
        } finally {
            setPricesLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="min-h-[80vh] flex flex-col items-center justify-center space-y-6">
                <div className="w-16 h-16 border-4 border-brand-primary/20 border-t-brand-primary rounded-full animate-spin" />
                <p className="text-sm font-bold text-slate-500 uppercase tracking-widest animate-pulse">Synchronizing Market Nodes...</p>
            </div>
        );
    }

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
                            placeholder="Search by Mandi, City, or State..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full pl-12 pr-4 py-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-sm font-medium outline-none focus:ring-2 focus:ring-brand-primary/20 transition-all dark:text-white"
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
                    <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center text-slate-900 dark:text-white">
                        <h3 className="font-bold">Major Trading Hubs</h3>
                        <span className="text-xs font-bold text-slate-400 uppercase tracking-tighter">Live Traffic</span>
                    </div>
                    <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
                        {filteredMarkets.length > 0 ? filteredMarkets.map((mandi, i) => (
                            <motion.div
                                key={mandi.id}
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: Math.min(i * 0.05, 1) }}
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
                                            <div className="flex items-center space-x-2 mt-1">
                                                <p className="text-[10px] text-slate-500 font-medium">{mandi.state_name}</p>
                                                {((mandi.state_name || '').includes('Coastal') || (mandi.name || '').toLowerCase().includes('port')) && (
                                                    <span className="text-[8px] font-black px-1.5 py-0.5 bg-blue-500/10 text-blue-500 rounded uppercase">Port</span>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                    <div className="flex items-center space-x-2">
                                        <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                                        <div className="text-[10px] font-bold text-emerald-500 uppercase tracking-tighter text-slate-900 dark:text-emerald-500">
                                            Discovery
                                        </div>
                                    </div>
                                </div>
                            </motion.div>
                        )) : (
                            <div className="text-center py-20">
                                <Search className="w-10 h-10 text-slate-300 mx-auto mb-4" />
                                <p className="text-slate-500 text-sm font-bold">No nodes found in this region</p>
                            </div>
                        )}
                    </div>
                </div>

                {/* Map Visualization Workspace */}
                <div className="lg:col-span-2 relative glass-card bg-slate-100 dark:bg-slate-900/20 overflow-hidden group">
                    <IndiaMap markets={filteredMarkets} selectedRegion={selectedState} onNodeClick={handleMarketSelect} />

                    <div className="absolute top-6 left-6 z-[40] flex flex-col space-y-2">
                        <button className="p-2.5 bg-white dark:bg-slate-800 rounded-xl shadow-lg border border-slate-200 dark:border-slate-700 hover:text-brand-primary transition-colors">
                            <Layers className="w-5 h-5 text-slate-900 dark:text-white" />
                        </button>
                    </div>

                    <div className="absolute top-6 right-6 z-[40]">
                        <div className="flex items-center space-x-2 bg-white dark:bg-slate-800 px-4 py-2.5 rounded-xl shadow-lg border border-slate-200 dark:border-slate-700">
                            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
                            <span className="text-xs font-bold text-slate-900 dark:text-slate-200">Terminal Heatmap Live</span>
                        </div>
                    </div>

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

                                <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar text-slate-900 dark:text-white">
                                    {pricesLoading ? (
                                        <div className="flex flex-col items-center justify-center py-20 space-y-4">
                                            <Activity className="w-8 h-8 text-brand-primary animate-spin" />
                                            <p className="text-xs font-bold text-slate-400 animate-pulse uppercase tracking-widest">Scanning Terminal Prices...</p>
                                        </div>
                                    ) : marketPrices.length > 0 ? (
                                        <div className="space-y-4">
                                            {marketPrices.map((price, idx) => (
                                                <motion.div
                                                    key={price.id || idx}
                                                    initial={{ opacity: 0, y: 10 }}
                                                    animate={{ opacity: 1, y: 0 }}
                                                    transition={{ delay: idx * 0.05 }}
                                                    className="p-5 rounded-2xl border border-slate-100 dark:border-slate-800 bg-white dark:bg-slate-900/50 hover:border-brand-primary/40 transition-all hover:shadow-xl group"
                                                >
                                                    <div className="flex justify-between items-start mb-4">
                                                        <div>
                                                            <h5 className="font-black text-sm dark:text-white uppercase tracking-tight">{price.commodity_name}</h5>
                                                            <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mt-0.5">{price.variety_name || 'Standard Grade'}</p>
                                                        </div>
                                                        <div className="flex flex-col items-end">
                                                            <span className="text-[10px] font-black text-brand-primary bg-brand-primary/10 px-2 py-0.5 rounded uppercase">{price.unit}</span>
                                                            <p className="text-[9px] text-slate-400 font-bold mt-1">VOL: {price.arrival_quantity}</p>
                                                        </div>
                                                    </div>

                                                    <div className="grid grid-cols-3 gap-2 py-4 border-t border-b border-slate-100 dark:border-slate-800/50 mb-3">
                                                        <div className="text-center">
                                                            <p className="text-[8px] font-black text-slate-400 uppercase tracking-tighter mb-1">Min</p>
                                                            <p className="text-xs font-bold">₹{price.min_price}</p>
                                                        </div>
                                                        <div className="text-center bg-brand-primary/5 rounded-xl py-1 transform group-hover:scale-105 transition-transform">
                                                            <p className="text-[8px] font-black text-brand-primary uppercase tracking-tighter mb-1">Modal</p>
                                                            <p className="text-sm font-black text-brand-primary">₹{price.modal_price}</p>
                                                        </div>
                                                        <div className="text-center">
                                                            <p className="text-[8px] font-black text-slate-400 uppercase tracking-tighter mb-1">Max</p>
                                                            <p className="text-xs font-bold">₹{price.max_price}</p>
                                                        </div>
                                                    </div>

                                                    <div className="flex justify-between items-center text-[8px] font-black uppercase tracking-widest text-slate-400">
                                                        <div className="flex items-center space-x-1">
                                                            <Box className="w-2.5 h-2.5" />
                                                            <span>Source: {price.source_name || 'AGMARKNET'}</span>
                                                        </div>
                                                        <div className="flex items-center space-x-1 text-emerald-500">
                                                            <div className="w-1 h-1 rounded-full bg-emerald-500 animate-pulse" />
                                                            <span>Verified</span>
                                                        </div>
                                                    </div>
                                                </motion.div>
                                            ))}
                                        </div>
                                    ) : (
                                        <div className="text-center py-20 bg-slate-50 dark:bg-slate-800/20 rounded-3xl border-2 border-dashed border-slate-100 dark:border-slate-800">
                                            <AlertCircle className="w-10 h-10 text-slate-300 mx-auto mb-4" />
                                            <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">No nodes discovered</p>
                                            <p className="text-[10px] text-slate-400 mt-1">Terminal signal currently offline</p>
                                        </div>
                                    )}
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
                                {['All India', 'Maharashtra', 'Karnataka', 'Tamil Nadu', 'Marine Ports'].map((region) => (
                                    <button
                                        key={region}
                                        onClick={() => setSelectedState(region)}
                                        className={`px-6 py-2 rounded-lg text-xs font-bold transition-all ${selectedState === region ? 'bg-white dark:bg-slate-700 shadow-sm text-brand-primary dark:text-blue-400' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}
                                    >
                                        {region}
                                    </button>
                                ))}
                            </div>
                        </motion.div>
                    </div>
                </div>
            </div>
        </div>
    );
}
