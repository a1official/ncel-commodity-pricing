"use client";

import React from 'react';
import {
    FileText,
    Download,
    Search,
    Filter,
    Calendar,
    Clock,
    PieChart,
    CheckCircle2,
    ChevronRight,
    Database,
    Printer,
    Mail,
    MoreVertical
} from 'lucide-react';
import { motion } from 'framer-motion';

const reports = [
    { id: 'REP-001', name: 'National Rice Market Monthly Analysis', date: 'Feb 24, 2026', type: 'Analytical', format: 'PDF', size: '4.2 MB' },
    { id: 'REP-002', name: 'Coastal Shrimp Landing Trends', date: 'Feb 22, 2026', type: 'Marine', format: 'Excel', size: '1.8 MB' },
    { id: 'REP-003', name: 'Mandi Arrival Density - Q1 Projected', date: 'Feb 18, 2026', type: 'Forecasting', format: 'PDF', size: '5.6 MB' },
    { id: 'REP-004', name: 'Daily Price Intelligence Summary', date: 'Today, 08:30', type: 'Operational', format: 'CSV', size: '124 KB' },
    { id: 'REP-005', name: 'Maharashtra Turmeric Price Spike Audit', date: 'Feb 15, 2026', type: 'Anomaly', format: 'PDF', size: '2.1 MB' },
];

export default function ReportsDownloads() {
    return (
        <div className="space-y-8 max-w-[1600px] mx-auto pb-20">
            {/* Header */}
            <div className="flex justify-between items-end">
                <div>
                    <h1 className="text-4xl font-bold font-display dark:text-white">Reports & Archive</h1>
                    <p className="text-slate-500 font-medium mt-2">Access historical intelligence, export data audits, and scheduled report configurations.</p>
                </div>
                <div className="flex space-x-3">
                    <button className="flex items-center space-x-2 px-6 py-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-sm font-bold dark:text-slate-300">
                        <Calendar className="w-4 h-4" />
                        <span>Select Period</span>
                    </button>
                    <button className="flex items-center space-x-2 px-6 py-3 bg-brand-primary text-white rounded-xl text-sm font-bold shadow-lg shadow-brand-primary/20">
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Configure Schedule</span>
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
                {/* Sidebar Filters */}
                <div className="space-y-6">
                    <div className="glass-card p-6">
                        <h3 className="text-sm font-bold dark:text-slate-200 mb-6 uppercase tracking-widest text-slate-400">Report Categories</h3>
                        <div className="space-y-2">
                            {[
                                { label: 'All Intelligence', count: 124, active: true },
                                { label: 'Price Analysis', count: 42, active: false },
                                { label: 'Marine Trade', count: 18, active: false },
                                { label: 'Forecasting', count: 12, active: false },
                                { label: 'Audit Logs', count: 52, active: false },
                            ].map((cat, i) => (
                                <button key={i} className={`w-full flex justify-between items-center px-4 py-3 rounded-xl text-sm font-bold transition-all ${cat.active ? 'bg-brand-primary text-white shadow-lg' : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800'}`}>
                                    <span>{cat.label}</span>
                                    <span className={`text-[10px] px-2 py-0.5 rounded-full ${cat.active ? 'bg-white/20' : 'bg-slate-100 dark:bg-slate-800'}`}>{cat.count}</span>
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="glass-card p-6 bg-slate-900 text-white group cursor-pointer">
                        <Database className="w-8 h-8 text-brand-primary mb-4" />
                        <h4 className="font-bold mb-2">Custom Query Export</h4>
                        <p className="text-xs text-slate-400 leading-relaxed mb-6">Build a custom CSV export by selecting specific mandis, commodities, and date ranges.</p>
                        <button className="text-brand-primary text-xs font-bold flex items-center hover:translate-x-1 transition-transform">
                            Launch Query Builder <ChevronRight className="w-4 h-4 ml-1" />
                        </button>
                    </div>
                </div>

                {/* Reports Table Area */}
                <div className="lg:col-span-3 space-y-6">
                    <div className="relative">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                        <input
                            type="text"
                            placeholder="Search reports by name, type, or ID..."
                            className="w-full pl-12 pr-4 py-4 glass-card bg-white dark:bg-slate-900 border-none outline-none text-sm font-medium shadow-sm transition-shadow focus:shadow-md"
                        />
                    </div>

                    <div className="glass-card overflow-hidden">
                        <div className="p-6 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/40 flex justify-between items-center">
                            <h3 className="font-bold dark:text-white">Generated Reports Archive</h3>
                            <div className="flex space-x-2">
                                <button className="p-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg"><Filter className="w-4 h-4 text-slate-400" /></button>
                                <button className="p-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg"><Clock className="w-4 h-4 text-slate-400" /></button>
                            </div>
                        </div>
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead className="bg-slate-50 dark:bg-slate-900/60 text-[10px] text-slate-400 uppercase tracking-widest font-bold">
                                    <tr>
                                        <th className="px-8 py-5 text-left">Report Name</th>
                                        <th className="px-8 py-5 text-left">Generated</th>
                                        <th className="px-8 py-5 text-left">Type</th>
                                        <th className="px-8 py-5 text-center">Format</th>
                                        <th className="px-8 py-5 text-right">Size</th>
                                        <th className="px-8 py-5 text-right">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-50 dark:divide-slate-800/60">
                                    {reports.map((report, i) => (
                                        <tr key={i} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors group">
                                            <td className="px-8 py-5">
                                                <div className="flex items-center space-x-3">
                                                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${report.format === 'PDF' ? 'bg-rose-500/10 text-rose-500' : report.format === 'Excel' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-brand-primary/10 text-brand-primary'}`}>
                                                        <FileText className="w-5 h-5" />
                                                    </div>
                                                    <div>
                                                        <p className="text-sm font-bold dark:text-slate-200 truncate max-w-xs">{report.name}</p>
                                                        <p className="text-[10px] text-slate-500 font-bold uppercase tracking-tight">{report.id}</p>
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="px-8 py-5 text-sm text-slate-500 dark:text-slate-400 font-medium">{report.date}</td>
                                            <td className="px-8 py-5">
                                                <span className="text-[10px] font-bold px-3 py-1 bg-slate-100 dark:bg-slate-800 dark:text-slate-300 rounded-full">{report.type}</span>
                                            </td>
                                            <td className="px-8 py-5 text-center">
                                                <span className={`text-[10px] font-black ${report.format === 'PDF' ? 'text-rose-500' : 'text-emerald-500'}`}>{report.format}</span>
                                            </td>
                                            <td className="px-8 py-5 text-right text-sm text-slate-500 font-bold">{report.size}</td>
                                            <td className="px-8 py-5 text-right">
                                                <div className="flex items-center justify-end space-x-2">
                                                    <button className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-400 hover:text-brand-primary transition-colors"><Download className="w-4 h-4" /></button>
                                                    <button className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-400 hover:text-brand-primary transition-colors"><Mail className="w-4 h-4" /></button>
                                                    <button className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-400 hover:text-brand-primary transition-colors"><MoreVertical className="w-4 h-4" /></button>
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                        <div className="p-6 bg-slate-50/50 dark:bg-slate-900/40 border-t border-slate-100 dark:border-slate-800 text-center">
                            <button className="text-xs font-bold text-slate-500 hover:text-brand-primary transition-colors">Show Older Reports</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
