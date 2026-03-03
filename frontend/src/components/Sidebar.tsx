"use client";

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
    LayoutDashboard,
    Package,
    Map,
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
    { icon: BarChart3, label: 'Analytics', href: '/analytics' },
    { icon: LineChart, label: 'Forecasting', href: '/forecasting' },
    { icon: Waves, label: 'Marine Data', href: '/marine' },
    { icon: FileText, label: 'Reports', href: '/reports' },
    { icon: Bell, label: 'Alerts', href: '/alerts' },
    { icon: Settings, label: 'Settings', href: '/settings' },
];

export default function Sidebar() {
    const pathname = usePathname();
    const { userName, userRole } = useUser();

    return (
        <aside className="shrink-0 h-screen w-72 bg-slate-50 dark:bg-slate-950 border-r border-slate-200 dark:border-slate-800/60 z-50 flex flex-col sticky top-0">
            <div className="p-8">
                <div className="flex items-center space-x-3 mb-10">
                    <div className="w-10 h-10 bg-brand-primary rounded-xl flex items-center justify-center shadow-lg shadow-brand-primary/20">
                        <BarChart3 className="text-white w-6 h-6" />
                    </div>
                    <span className="font-display text-xl font-bold tracking-tight dark:text-white">NCEL Intelligence</span>
                </div>

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
                                <item.icon className={`w-5 h-5 ${isActive ? 'text-brand-primary dark:text-blue-400' : ''}`} />
                                <span>{item.label}</span>
                            </Link>
                        );
                    })}
                </nav>
            </div>

            <div className="mt-auto p-8 border-t border-slate-200 dark:border-slate-800/60 pb-6">
                <div className="flex items-center space-x-3 p-3 glass-card bg-slate-100 dark:bg-slate-900/40 rounded-xl mb-6">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-brand-primary to-cyan-400 border-2 border-white dark:border-slate-800" />
                    <div className="flex-1 overflow-hidden">
                        <p className="text-sm font-bold dark:text-white truncate">{userName}</p>
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
