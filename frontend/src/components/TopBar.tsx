"use client";

import React from 'react';
import { Search, Bell, Moon, Sun, ChevronDown, Calendar, SearchIcon } from 'lucide-react';
import { motion } from 'framer-motion';

export default function TopBar() {
    return (
        <header className="h-20 flex items-center justify-between px-10 sticky top-0 bg-white/50 dark:bg-slate-950/50 backdrop-blur-md z-40 border-b border-slate-200 dark:border-slate-800/60">
            <div className="flex-1 max-w-2xl">
                <div className="relative group">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 group-focus-within:text-brand-primary transition-colors" />
                    <input
                        type="text"
                        placeholder="Search commodities, markets, or intelligence reports..."
                        className="w-full pl-12 pr-4 py-2.5 bg-slate-100 dark:bg-slate-900/60 rounded-xl border border-transparent focus:border-brand-primary/30 focus:bg-white dark:focus:bg-slate-900 transition-all outline-none text-sm font-medium dark:text-slate-200 shadow-sm"
                    />
                    <div className="absolute right-3 top-1/2 -translate-y-1/2 flex space-x-1">
                        <kbd className="hidden sm:inline-flex items-center px-2 py-0.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-[10px] font-medium text-slate-400">Ctrl</kbd>
                        <kbd className="hidden sm:inline-flex items-center px-2 py-0.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-[10px] font-medium text-slate-400">K</kbd>
                    </div>
                </div>
            </div>

            <div className="flex items-center space-x-6 ml-10">
                <div className="flex items-center space-x-2 bg-slate-100 dark:bg-slate-900/60 px-4 py-2 rounded-xl border border-slate-200 dark:border-slate-800/60 cursor-pointer hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors">
                    <Calendar className="w-4 h-4 text-slate-500" />
                    <span className="text-sm font-semibold dark:text-slate-300">
                        {new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                    </span>
                    <ChevronDown className="w-3 h-3 text-slate-400" />
                </div>

                <div className="flex items-center space-x-4">
                    <button className="p-2.5 rounded-xl bg-slate-100 dark:bg-slate-900/60 text-slate-500 hover:text-brand-primary hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors relative">
                        <Bell className="w-5 h-5" />
                        <span className="absolute top-2 right-2 w-2 h-2 bg-brand-primary rounded-full ring-2 ring-white dark:ring-slate-950" />
                    </button>
                    <button className="p-2.5 rounded-xl bg-slate-100 dark:bg-slate-900/60 text-slate-500 hover:text-brand-primary hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors">
                        <Moon className="w-5 h-5" />
                    </button>
                </div>
            </div>
        </header>
    );
}
