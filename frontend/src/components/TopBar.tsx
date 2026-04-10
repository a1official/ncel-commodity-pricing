"use client";

import React from 'react';
import { Search, Bell, Moon, Sun, ChevronDown, Calendar } from 'lucide-react';
import { useUser } from '@/context/UserContext';

export default function TopBar() {
    const { isDarkMode, toggleDarkMode } = useUser();
    
    const [mounted, setMounted] = React.useState(false);

    React.useEffect(() => {
        setMounted(true);
    }, []);

    return (
        <header className="sticky top-0 z-40 border-b border-[var(--panel-border)] bg-[color:var(--panel-bg)]/90 backdrop-blur-xl transition-colors duration-300">
            <div className="flex h-20 items-center justify-between gap-4 px-4 md:px-8 xl:px-10">
            <div className="flex-1 max-w-2xl">
                <div className="relative group">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 group-focus-within:text-brand-primary transition-colors" />
                    <input
                        type="text"
                        placeholder="Search commodities, markets, or intelligence reports..."
                        className="w-full rounded-2xl border border-[var(--muted-border)] bg-[color:var(--muted-surface)] pl-12 pr-4 py-3 text-sm font-medium text-[color:var(--text-strong)] shadow-sm outline-none transition-all placeholder:text-slate-400 focus:border-brand-primary/30 focus:bg-white/80 dark:focus:bg-slate-900"
                    />
                    <div className="absolute right-3 top-1/2 -translate-y-1/2 flex space-x-1">
                        <kbd className="hidden sm:inline-flex items-center rounded-lg border border-[var(--muted-border)] bg-white/70 px-2 py-0.5 text-[10px] font-medium text-slate-500 dark:bg-slate-800 dark:text-slate-400">Ctrl</kbd>
                        <kbd className="hidden sm:inline-flex items-center rounded-lg border border-[var(--muted-border)] bg-white/70 px-2 py-0.5 text-[10px] font-medium text-slate-500 dark:bg-slate-800 dark:text-slate-400">K</kbd>
                    </div>
                </div>
            </div>

            <div className="ml-2 flex items-center space-x-3 md:space-x-4 xl:space-x-6">
                <div className="hidden sm:flex items-center space-x-2 rounded-2xl border border-[var(--muted-border)] bg-[color:var(--muted-surface)] px-4 py-2.5 cursor-pointer transition-colors hover:bg-white/70 dark:hover:bg-slate-800">
                    <Calendar className="w-4 h-4 text-slate-500" />
                    <span className="text-sm font-semibold text-[color:var(--text-strong)]">
                        {mounted ? new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '---'}
                    </span>
                    <ChevronDown className="w-3 h-3 text-slate-400" />
                </div>

                <div className="flex items-center space-x-2 md:space-x-3">
                    <button className="relative rounded-2xl border border-[var(--muted-border)] bg-[color:var(--muted-surface)] p-2.5 text-slate-500 transition-colors hover:bg-white/70 hover:text-brand-primary dark:hover:bg-slate-800">
                        <Bell className="w-5 h-5" />
                        <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-brand-primary ring-2 ring-[color:var(--app-bg)]" />
                    </button>

                    <button
                        onClick={toggleDarkMode}
                        aria-label={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
                        className="group relative flex items-center gap-2 rounded-2xl border border-[var(--muted-border)] bg-[color:var(--muted-surface)] px-2 py-2 text-slate-600 shadow-sm transition-all hover:-translate-y-0.5 hover:bg-white/80 dark:text-slate-300 dark:hover:bg-slate-800"
                    >
                        <div className={`absolute inset-y-1 w-10 rounded-xl bg-gradient-to-br transition-all duration-300 ${isDarkMode ? 'left-[calc(100%-2.75rem)] from-amber-300 to-orange-400' : 'left-1 from-sky-300 to-cyan-400'}`} />
                        <span className={`relative z-10 flex h-8 w-8 items-center justify-center rounded-xl transition-colors ${!isDarkMode ? 'text-slate-950' : 'text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-200'}`}>
                            <Sun className="w-4 h-4" />
                        </span>
                        <span className={`relative z-10 flex h-8 w-8 items-center justify-center rounded-xl transition-colors ${isDarkMode ? 'text-slate-950' : 'text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-200'}`}>
                            <Moon className="w-4 h-4" />
                        </span>
                    </button>
                </div>
            </div>
            </div>
        </header>
    );
}
