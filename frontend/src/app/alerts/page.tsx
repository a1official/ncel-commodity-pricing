"use client";

import React, { useState } from 'react';
import {
    Bell,
    AlertTriangle,
    TrendingUp,
    TrendingDown,
    Zap,
    Info,
    CheckCircle2,
    Filter,
    Search,
    Plus,
    MoreHorizontal,
    Mail,
    Smartphone,
    MessageSquare,
    Clock
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const notifications = [
    { id: 1, type: 'spike', title: 'Price Spike Detected', message: 'Basmati Rice modal price increased by 14.2% in Azadpur Mandi.', time: '2 mins ago', read: false, priority: 'High' },
    { id: 2, type: 'forecast', title: 'Forecast Update', message: 'ML models revised Maharashtra Onion outlook to Bearish for Q2.', time: '45 mins ago', read: false, priority: 'Med' },
    { id: 3, type: 'anomaly', title: 'Data Anomaly Flagged', message: 'Inconsistent arrival density detected in Cochin Port for Shrimp.', time: '2 hours ago', read: true, priority: 'High' },
    { id: 4, type: 'system', title: 'Pipeline Sync Complete', message: 'NFDB Marine data feed synchronized successfully.', time: '5 hours ago', read: true, priority: 'Low' },
];

export default function AlertsSystem() {
    const [activeTab, setActiveTab] = useState('All Alerts');

    return (
        <div className="space-y-8 max-w-[1600px] mx-auto pb-20">
            {/* Header */}
            <div className="flex justify-between items-end">
                <div>
                    <h1 className="text-4xl font-bold font-display dark:text-white">Alerts & Notifications</h1>
                    <p className="text-slate-500 font-medium mt-2">Real-time market surveillance, threshold triggers, and anomaly notifications.</p>
                </div>
                <div className="flex space-x-3">
                    <button className="flex items-center space-x-2 px-6 py-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-sm font-bold dark:text-slate-300">
                        <Filter className="w-4 h-4" />
                        <span>Filter Priority</span>
                    </button>
                    <button className="flex items-center space-x-2 px-6 py-3 bg-brand-primary text-white rounded-xl text-sm font-bold shadow-lg shadow-brand-primary/20 hover:scale-[1.02] transition-all">
                        <Plus className="w-4 h-4" />
                        <span>Create Alert Rule</span>
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-4 gap-8">
                {/* Configure Alerts Stats Sidebar */}
                <div className="space-y-6">
                    <div className="glass-card p-6 border-l-4 border-l-rose-500 bg-rose-500/5">
                        <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mb-1">Unresolved High Priority</p>
                        <h3 className="text-2xl font-bold dark:text-white">03</h3>
                        <div className="mt-4 flex items-center text-[10px] font-bold text-rose-500">
                            <AlertTriangle className="w-3 h-3 mr-1" />
                            <span>Action required immediately</span>
                        </div>
                    </div>

                    <div className="glass-card p-6">
                        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-6 border-b border-slate-100 dark:border-slate-800 pb-3">Delivery Channels</h4>
                        <div className="space-y-4">
                            {[
                                { icon: Mail, label: 'Email Digest', status: 'Active' },
                                { icon: Smartphone, label: 'Mobile Push', status: 'Active' },
                                { icon: MessageSquare, label: 'WhatsApp Bot', status: 'Disabled' },
                            ].map((channel, i) => (
                                <div key={i} className="flex justify-between items-center">
                                    <div className="flex items-center space-x-3">
                                        <channel.icon className="w-4 h-4 text-slate-400" />
                                        <span className="text-sm font-bold dark:text-slate-300">{channel.label}</span>
                                    </div>
                                    <span className={`text-[10px] font-bold ${channel.status === 'Active' ? 'text-emerald-500' : 'text-slate-400'}`}>{channel.status}</span>
                                </div>
                            ))}
                        </div>
                        <button className="w-full mt-6 py-3 border border-slate-200 dark:border-slate-800 rounded-xl text-[10px] font-bold uppercase tracking-widest text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors">
                            Notification Settings
                        </button>
                    </div>
                </div>

                {/* Alerts Feed Area */}
                <div className="xl:col-span-3 space-y-6">
                    <div className="flex bg-slate-100 dark:bg-slate-900 p-1.5 rounded-2xl w-fit border border-slate-200 dark:border-slate-800">
                        {['All Alerts', 'Price Triggers', 'Data Quality', 'System'].map((tab) => (
                            <button
                                key={tab}
                                onClick={() => setActiveTab(tab)}
                                className={`px-6 py-2 rounded-xl text-xs font-bold transition-all ${activeTab === tab ? 'bg-white dark:bg-slate-800 shadow-sm dark:text-white' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}
                            >
                                {tab}
                            </button>
                        ))}
                    </div>

                    <div className="space-y-4">
                        <AnimatePresence>
                            {notifications.map((alert, idx) => (
                                <motion.div
                                    key={alert.id}
                                    initial={{ opacity: 0, scale: 0.98 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    transition={{ delay: idx * 0.05 }}
                                    className={`glass-card p-6 border-l-4 transition-all hover:bg-white dark:hover:bg-slate-900/60 cursor-pointer flex items-start justify-between group ${!alert.read ? 'bg-white dark:bg-slate-900/40 shadow-md ring-1 ring-brand-primary/10' : 'bg-slate-50/50 dark:bg-transparent'} ${alert.priority === 'High' ? 'border-l-rose-500' : alert.priority === 'Med' ? 'border-l-amber-500' : 'border-l-slate-300 dark:border-l-slate-700'}`}
                                >
                                    <div className="flex space-x-6">
                                        <div className={`mt-1 p-3 rounded-2xl ${alert.type === 'spike' ? 'bg-rose-500/10 text-rose-500' : alert.type === 'forecast' ? 'bg-brand-primary/10 text-brand-primary' : alert.type === 'anomaly' ? 'bg-amber-500/10 text-amber-500' : 'bg-slate-100 dark:bg-slate-800 text-slate-400'}`}>
                                            {alert.type === 'spike' ? <TrendingUp className="w-5 h-5" /> : alert.type === 'forecast' ? <Zap className="w-5 h-5" /> : alert.type === 'anomaly' ? <AlertTriangle className="w-5 h-5" /> : <Info className="w-5 h-5" />}
                                        </div>
                                        <div>
                                            <div className="flex items-center space-x-3 mb-1">
                                                <h4 className="text-sm font-bold dark:text-slate-100">{alert.title}</h4>
                                                {!alert.read && <div className="w-1.5 h-1.5 rounded-full bg-brand-primary" />}
                                            </div>
                                            <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed mb-4">{alert.message}</p>
                                            <div className="flex items-center space-x-6 text-[10px] font-bold uppercase tracking-widest text-slate-400">
                                                <span className="flex items-center"><Clock className="w-3 h-3 mr-1.5" /> {alert.time}</span>
                                                <span className="flex items-center"><Bell className="w-3 h-3 mr-1.5" /> via {alert.priority} Queue</span>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="flex items-center space-x-2">
                                        <button className="p-2.5 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-brand-primary transition-colors opacity-0 group-hover:opacity-100"><CheckCircle2 className="w-4 h-4" /></button>
                                        <button className="p-2.5 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-brand-primary transition-colors"><MoreHorizontal className="w-4 h-4" /></button>
                                    </div>
                                </motion.div>
                            ))}
                        </AnimatePresence>
                    </div>

                    <div className="p-8 text-center glass-card border-dashed border-2 bg-transparent border-slate-100 dark:border-slate-800/60">
                        <p className="text-sm text-slate-500 mb-4">No more alerts for today.</p>
                        <button className="text-xs font-bold text-brand-primary hover:underline">View Historical Archive</button>
                    </div>
                </div>
            </div>
        </div>
    );
}
