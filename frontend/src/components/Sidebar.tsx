"use client";

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
    LayoutDashboard,
    Package,
    Map,
    Satellite,
    BarChart3,
    LineChart,
    Waves,
    FileText,
    Bell,
    Settings,
    Menu
} from 'lucide-react';
import { motion } from 'framer-motion';
import { useUser } from '@/context/UserContext';

const menuItems = [
    { icon: LayoutDashboard, label: 'Dashboard', href: '/' },
    { icon: Package, label: 'Commodities', href: '/commodities' },
    { icon: Map, label: 'Markets / Mandis', href: '/markets' },
    { icon: Satellite, label: 'Geospatial', href: '/geospatial' },
    { icon: BarChart3, label: 'Analytics', href: '/analytics' },
    { icon: LineChart, label: 'Forecasting', href: '/forecasting' },
    { icon: Waves, label: 'Marine Data', href: '/marine' },
    { icon: FileText, label: 'Reports', href: '/reports' },
    { icon: Bell, label: 'Alerts', href: '/alerts' },
    { icon: Settings, label: 'Settings', href: '/settings' },
    { icon: BarChart3, label: 'Terminal', href: '/analytics/terminal', highlight: true },
];

export default function Sidebar() {
    const pathname = usePathname();
    const { userName, userRole } = useUser();

    return (
        <aside className="sticky top-0 z-50 flex h-screen w-72 shrink-0 flex-col border-r border-[var(--panel-border)] bg-[color:var(--panel-bg)]/95 backdrop-blur-xl transition-colors duration-300">
            <div className="p-8 pb-5">
                <div className="flex items-center space-x-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-primary shadow-lg shadow-brand-primary/20">
                        <BarChart3 className="text-white w-6 h-6" />
                    </div>
                    <span className="font-display text-xl font-bold tracking-tight themed-text-strong">NCEL Intelligence</span>
                </div>
            </div>

            <div className="flex-1 min-h-0 overflow-y-auto px-6 pb-6 custom-scrollbar">
                <nav className="space-y-1.5">
                    {menuItems.map((item) => {
                        const isActive = pathname === item.href;
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={`sidebar-nav-item relative ${isActive ? 'active' : ''}`}
                            >
                                {isActive && (
                                    <motion.div
                                        layoutId="activeNav"
                                        className="absolute left-0 w-1 h-6 bg-brand-primary rounded-r-full"
                                        transition={{ type: "spring", stiffness: 300, damping: 30 }}
                                    />
                                )}
                                <item.icon className={`w-5 h-5 ${isActive ? 'text-brand-primary dark:text-blue-400' : item.highlight ? 'text-amber-400' : ''}`} />
                                <span className={item.highlight ? 'text-amber-400 font-bold' : ''}>{item.label}</span>
                            </Link>
                        );
                    })}
                </nav>
            </div>

            <div className="p-8 border-t border-[var(--panel-border)] pb-6">
                <div className="mb-6 flex items-center space-x-3 rounded-xl bg-[color:var(--muted-surface)] p-3 border border-[var(--muted-border)]">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-brand-primary to-cyan-400 border-2 border-white dark:border-slate-800" />
                    <div className="flex-1 overflow-hidden">
                        <p className="truncate text-sm font-bold themed-text-strong">{userName}</p>
                        <p className="text-xs text-slate-500 truncate">{userRole}</p>
                    </div>
                </div>

                <div className="flex items-center space-x-2 px-3">
                    <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.6)]" />
                    <span className="text-[10px] font-black uppercase tracking-widest text-slate-500 dark:text-slate-400">Intelligence Core: Active</span>
                </div>
            </div>
        </aside>
    );
}
