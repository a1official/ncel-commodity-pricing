"use client";

import React, { useState, useEffect } from 'react';
import {
    Search,
    Filter,
    TrendingUp,
    TrendingDown,
    Package,
    Waves,
    ArrowUpRight,
    ArrowDownRight,
    MoreHorizontal,
    ChevronRight,
    Loader2,
    RefreshCw
} from 'lucide-react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { fetchCommodities, triggerIngestion } from '@/lib/api';

const categories = ['All', 'Grain', 'Vegetable', 'Spices', 'Marine', 'Oilseeds'];

export default function CommoditiesPage() {
    const [commodities, setCommodities] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [syncing, setSyncing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [activeCategory, setActiveCategory] = useState('All');
    const [search, setSearch] = useState('');

    const loadData = async () => {
        try {
            setLoading(true);
            const data = await fetchCommodities();
            setCommodities(data);
        } catch (err) {
            console.error(err);
            setError('Failed to connect to the intelligence engine.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadData();
    }, []);

    const handleSync = async () => {
        try {
            setSyncing(true);
            await triggerIngestion();
            setSyncing(false);

            // Wait for a few seconds for the background task to start before refreshing list
            setTimeout(() => {
                loadData();
            }, 2000);
        } catch (err) {
            console.error(err);
            setSyncing(false);
        }
    };

    const filtered = commodities.filter(c => {
        const matchesCategory = activeCategory === 'All' || c.category === activeCategory;
        const matchesSearch = c.name.toLowerCase().includes(search.toLowerCase());
        return matchesCategory && matchesSearch;
    });

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
                <Loader2 className="w-10 h-10 text-brand-primary animate-spin" />
                <p className="text-slate-500 font-medium animate-pulse">Synchronizing with live terminals...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-6">
                <div className="w-16 h-16 bg-rose-500/10 rounded-2xl flex items-center justify-center text-rose-500">
                    <Package className="w-8 h-8" />
                </div>
                <div className="text-center">
                    <h3 className="text-xl font-bold dark:text-white mb-2">Connection Offline</h3>
                    <p className="text-slate-500 max-w-md mx-auto">{error}</p>
                </div>
                <button
                    onClick={() => window.location.reload()}
                    className="px-6 py-2.5 bg-brand-primary text-white rounded-xl text-sm font-bold shadow-lg shadow-brand-primary/20 hover:scale-[1.02] transition-all"
                >
                    Retry Connection
                </button>
            </div>
        );
    }

    return (
        <div className="space-y-8 max-w-[1600px] mx-auto pb-20">
            {/* Header */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
                <div>
                    <h1 className="text-4xl font-bold font-display dark:text-white">Commodity Universe</h1>
                    <p className="text-slate-500 font-medium mt-2">Browse {commodities.length} tracked varieties across agricultural and marine sectors.</p>
                </div>
                <div className="flex space-x-3">
                    <div className="relative">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                        <input
                            type="text"
                            placeholder="Search commodity..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="pl-11 pr-4 py-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-sm font-medium outline-none focus:ring-2 focus:ring-brand-primary/20 transition-all w-64"
                        />
                    </div>
                    <button
                        onClick={handleSync}
                        disabled={syncing}
                        className={`flex items-center space-x-2 px-6 py-3 bg-brand-primary text-white rounded-xl text-sm font-bold shadow-lg shadow-brand-primary/20 hover:scale-[1.02] transition-all disabled:opacity-50 disabled:hover:scale-100 ${syncing ? 'animate-pulse' : ''}`}
                    >
                        <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
                        <span>{syncing ? 'Syncing...' : 'Sync Global Intelligence'}</span>
                    </button>
                </div>
            </div>

            {/* Category Filter Tabs */}
            <div className="flex space-x-2 overflow-x-auto pb-1">
                {categories.map((cat) => (
                    <button
                        key={cat}
                        onClick={() => setActiveCategory(cat)}
                        className={`px-5 py-2.5 rounded-xl text-xs font-bold whitespace-nowrap transition-all ${activeCategory === cat
                            ? 'bg-brand-primary text-white shadow-lg shadow-brand-primary/20'
                            : 'bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
                            }`}
                    >
                        {cat}
                    </button>
                ))}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
                {filtered.map((c, idx) => (
                    <motion.div
                        key={c.id}
                        initial={{ opacity: 0, y: 16 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.3, delay: idx * 0.04 }}
                    >
                        <Link href={`/commodities/${c.id}`} className="block">
                            <div className="glass-card p-6 group cursor-pointer hover:shadow-xl hover:border-brand-primary/20 transition-all duration-300 h-full flex flex-col">
                                <div className="flex justify-between items-start mb-5">
                                    <div className="w-12 h-12 bg-slate-100 dark:bg-slate-800 rounded-2xl flex items-center justify-center text-2xl group-hover:scale-110 transition-transform duration-300">
                                        {c.category === 'Grain' ? '🌾' : c.category === 'Vegetable' ? '🧅' : c.category === 'Spice' ? '🌿' : '📦'}
                                    </div>
                                    <div className="flex items-center space-x-1 px-2.5 py-1 rounded-lg text-[10px] font-bold bg-emerald-500/10 text-emerald-500">
                                        <ArrowUpRight className="w-3 h-3" />
                                        <span>LIVE</span>
                                    </div>
                                </div>

                                <div className="mb-4">
                                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">{c.category}</p>
                                    <h3 className="text-base font-bold dark:text-white leading-tight">{c.name}</h3>
                                </div>

                                <div className="mt-auto pt-5 border-t border-slate-100 dark:border-slate-800 flex justify-between items-center">
                                    <span className="text-xs font-bold text-brand-primary">Analyze Trends</span>
                                    <ChevronRight className="w-4 h-4 text-slate-300 dark:text-slate-600 group-hover:text-brand-primary group-hover:translate-x-0.5 transition-all" />
                                </div>
                            </div>
                        </Link>
                    </motion.div>
                ))}
            </div>

            {filtered.length === 0 && (
                <div className="text-center py-20 glass-card">
                    <Package className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                    <p className="text-slate-500 font-medium">No results matched your parameters.</p>
                </div>
            )}
        </div>
    );
}
