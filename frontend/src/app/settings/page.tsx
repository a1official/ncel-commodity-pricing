"use client";

import React, { useState, useEffect } from 'react';
import {
    Bell,
    Settings,
    User,
    Shield,
    Globe,
    Database,
    CreditCard,
    Key,
    Zap,
    Monitor,
    Check,
    ChevronRight,
    LogOut,
    RefreshCw,
    AlertCircle,
    Save
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useUser } from '@/context/UserContext';
import { triggerIngestion } from '@/lib/api';

export default function SettingsPage() {
    const { userName, userRole, isDarkMode, updateUser, toggleDarkMode } = useUser();
    const [activeTab, setActiveTab] = useState('Profile Info');
    const [isSaving, setIsSaving] = useState(false);
    const [isIngesting, setIsIngesting] = useState(false);
    const [showSuccess, setShowSuccess] = useState(false);
    const [ingestStatus, setIngestStatus] = useState<string | null>(null);

    // Form States
    const [profile, setProfile] = useState({
        displayName: "",
        email: "akash@ncel.gov.in",
        role: "",
        timezone: "(GMT+5:30) India Standard Time"
    });

    useEffect(() => {
        setProfile(prev => ({
            ...prev,
            displayName: userName,
            role: userRole
        }));
    }, [userName, userRole]);

    const [preferences, setPreferences] = useState({
        themePresence: isDarkMode,
        highDensityCharts: false,
        autoSync: true
    });

    // Sync preferences with actual dark mode
    useEffect(() => {
        setPreferences(prev => ({ ...prev, themePresence: isDarkMode }));
    }, [isDarkMode]);

    const handleThemeToggle = () => {
        toggleDarkMode();
        setPreferences(prev => ({ ...prev, themePresence: !prev.themePresence }));
    };

    const handleSave = () => {
        setIsSaving(true);
        // Simulate API call
        setTimeout(() => {
            updateUser(profile.displayName, profile.role);
            setIsSaving(false);
            setShowSuccess(true);
            setTimeout(() => setShowSuccess(false), 3000);
        }, 1200);
    };

    const handleRunIngestion = async () => {
        setIsIngesting(true);
        setIngestStatus('Initiating Signal Mesh...');
        try {
            await triggerIngestion();
            setIngestStatus('Pipeline executed successfully.');
            setTimeout(() => setIngestStatus(null), 3000);
        } catch (err) {
            console.error(err);
            setIngestStatus('Connection to ingestion node failed.');
            setTimeout(() => setIngestStatus(null), 5000);
        } finally {
            setIsIngesting(false);
        }
    };

    return (
        <div className="space-y-8 max-w-[1200px] mx-auto pb-20">
            {/* Header */}
            <div className="flex justify-between items-start">
                <div>
                    <h1 className="text-4xl font-bold font-display dark:text-white">Account Settings</h1>
                    <p className="text-slate-500 font-medium mt-2">Manage your intelligence profile, data preferences, and API access.</p>
                </div>
                <AnimatePresence>
                    {showSuccess && (
                        <motion.div
                            key="success-toast"
                            initial={{ opacity: 0, y: -20 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -20 }}
                            className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 px-4 py-2 rounded-xl flex items-center space-x-2 text-sm font-bold"
                        >
                            <Check className="w-4 h-4" />
                            <span>Changes saved successfully</span>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
                {/* Settings Navigation */}
                <div className="lg:col-span-1 space-y-2">
                    {[
                        { icon: User, label: 'Profile Info' },
                        { icon: Bell, label: 'Alerts & Notifications' },
                        { icon: Shield, label: 'Security' },
                        { icon: Database, label: 'Data Sources' },
                        { icon: Key, label: 'API Management' },
                        { icon: Globe, label: 'Regional Prefs' },
                        { icon: CreditCard, label: 'Subscription' },
                    ].map((item, i) => (
                        <button
                            key={i}
                            onClick={() => setActiveTab(item.label)}
                            className={`w-full flex items-center space-x-3 px-5 py-3.5 rounded-xl text-sm font-bold transition-all ${activeTab === item.label ? 'bg-brand-primary text-white shadow-lg shadow-brand-primary/20' : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800'}`}
                        >
                            <item.icon className={`w-4 h-4 ${activeTab === item.label ? 'text-white' : 'text-slate-400'}`} />
                            <span>{item.label}</span>
                        </button>
                    ))}
                    <div className="pt-4 mt-4 border-t border-slate-100 dark:border-slate-800">
                        <button className="w-full flex items-center space-x-3 px-5 py-3.5 rounded-xl text-sm font-bold text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-500/10 transition-all">
                            <LogOut className="w-4 h-4" />
                            <span>Sign Out</span>
                        </button>
                    </div>
                </div>

                {/* Content Area */}
                <div className="lg:col-span-3">
                    <AnimatePresence mode="wait">
                        {activeTab === 'Profile Info' && (
                            <motion.div
                                key="profile-info-tab"
                                initial={{ opacity: 0, x: 20 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -20 }}
                                className="space-y-8"
                            >
                                {/* Profile Section */}
                                <div className="glass-card p-8 bg-white dark:bg-slate-900/40">
                                    <h3 className="text-lg font-bold dark:text-white mb-8 border-b border-slate-100 dark:border-slate-800 pb-4">Profile Information</h3>
                                    <div className="flex items-center space-x-8 mb-10">
                                        <div className="relative">
                                            <div className="w-24 h-24 rounded-3xl bg-gradient-to-tr from-brand-primary to-cyan-400 border-4 border-white dark:border-slate-800 shadow-xl" />
                                            <button className="absolute -bottom-2 -right-2 p-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-full shadow-lg">
                                                <Zap className="w-4 h-4 text-brand-primary" />
                                            </button>
                                        </div>
                                        <div>
                                            <h4 className="text-xl font-bold dark:text-white">{profile.displayName}</h4>
                                            <p className="text-sm text-slate-500">{profile.role} • ncel-admin-corp</p>
                                            <button className="mt-3 text-brand-primary text-xs font-bold hover:underline">Change Profile Avatar</button>
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                        <div className="space-y-2">
                                            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest px-1">Full Name</label>
                                            <input
                                                type="text"
                                                value={profile.displayName}
                                                onChange={(e) => setProfile({ ...profile, displayName: e.target.value })}
                                                className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-sm font-medium outline-none focus:ring-2 focus:ring-brand-primary/20 transition-all dark:text-white"
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest px-1">Work Email</label>
                                            <input
                                                type="email"
                                                value={profile.email}
                                                onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                                                className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-sm font-medium outline-none focus:ring-2 focus:ring-brand-primary/20 transition-all dark:text-white"
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest px-1">Role</label>
                                            <select
                                                value={profile.role}
                                                onChange={(e) => setProfile({ ...profile, role: e.target.value })}
                                                className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-sm font-medium outline-none dark:text-white"
                                            >
                                                <option>Senior Market Analyst</option>
                                                <option>Mandi In-charge</option>
                                                <option>Policy Administrator</option>
                                            </select>
                                        </div>
                                        <div className="space-y-2">
                                            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest px-1">Timezone</label>
                                            <select
                                                value={profile.timezone}
                                                onChange={(e) => setProfile({ ...profile, timezone: e.target.value })}
                                                className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-sm font-medium outline-none dark:text-white"
                                            >
                                                <option>(GMT+5:30) India Standard Time</option>
                                                <option>(GMT+0:00) UTC</option>
                                                <option>(GMT+1:00) Central European Time</option>
                                            </select>
                                        </div>
                                    </div>
                                    <div className="mt-10 flex justify-end">
                                        <button
                                            onClick={handleSave}
                                            disabled={isSaving}
                                            className="min-w-[140px] px-8 py-3 bg-brand-primary text-white rounded-xl text-sm font-bold shadow-lg shadow-brand-primary/20 hover:scale-[1.02] active:scale-95 transition-all flex items-center justify-center space-x-2"
                                        >
                                            {isSaving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                                            <span>{isSaving ? 'Saving...' : 'Save Changes'}</span>
                                        </button>
                                    </div>
                                </div>

                                {/* Preferences Section */}
                                <div className="glass-card p-8 bg-white dark:bg-slate-900/40">
                                    <h3 className="text-lg font-bold dark:text-white mb-8 border-b border-slate-100 dark:border-slate-800 pb-4">Theme & Accessibility</h3>
                                    <div className="space-y-6">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center space-x-4">
                                                <div className="p-2.5 bg-slate-100 dark:bg-slate-800 rounded-xl"><Monitor className="w-5 h-5 text-slate-500" /></div>
                                                <div>
                                                    <h4 className="text-sm font-bold dark:text-slate-200">System Theme Presence</h4>
                                                    <p className="text-xs text-slate-500">Automatically switch between light and dark mode based on platform.</p>
                                                </div>
                                            </div>
                                            <div
                                                onClick={handleThemeToggle}
                                                className={`w-12 h-6 rounded-full relative cursor-pointer transition-colors ${preferences.themePresence ? 'bg-brand-primary' : 'bg-slate-200 dark:bg-slate-800'}`}
                                            >
                                                <motion.div
                                                    initial={false}
                                                    animate={{ x: preferences.themePresence ? 26 : 4 }}
                                                    className="absolute top-1 w-4 h-4 bg-white rounded-full shadow-sm"
                                                />
                                            </div>
                                        </div>

                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center space-x-4">
                                                <div className="p-2.5 bg-slate-100 dark:bg-slate-800 rounded-xl"><Zap className="w-5 h-5 text-slate-500" /></div>
                                                <div>
                                                    <h4 className="text-sm font-bold dark:text-slate-200">High-Density Charts</h4>
                                                    <p className="text-xs text-slate-500">Enable data points for granular price discovery visualization.</p>
                                                </div>
                                            </div>
                                            <div
                                                onClick={() => setPreferences({ ...preferences, highDensityCharts: !preferences.highDensityCharts })}
                                                className={`w-12 h-6 rounded-full relative cursor-pointer transition-colors ${preferences.highDensityCharts ? 'bg-brand-primary' : 'bg-slate-200 dark:bg-slate-800'}`}
                                            >
                                                <motion.div
                                                    initial={false}
                                                    animate={{ x: preferences.highDensityCharts ? 26 : 4 }}
                                                    className="absolute top-1 w-4 h-4 bg-white rounded-full shadow-sm"
                                                />
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                {/* Connected Sources */}
                                <div className="glass-card p-8 bg-white dark:bg-slate-900/40">
                                    <div className="flex justify-between items-center mb-8">
                                        <div>
                                            <h3 className="text-lg font-bold dark:text-white">Data Pipeline Integration</h3>
                                            <p className="text-xs text-slate-500 mt-1">Direct feeds currently mapped to your surveillance node.</p>
                                        </div>
                                        <div className="flex items-center space-x-3">
                                            {ingestStatus && (
                                                <span className="text-[10px] font-bold text-brand-primary animate-pulse">{ingestStatus}</span>
                                            )}
                                            <button
                                                onClick={handleRunIngestion}
                                                disabled={isIngesting}
                                                className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${isIngesting ? 'bg-slate-100 text-slate-400' : 'bg-brand-primary text-white shadow-lg shadow-brand-primary/20 hover:scale-[1.05]'}`}
                                            >
                                                {isIngesting ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Zap className="w-3 h-3" />}
                                                <span>{isIngesting ? 'Syncing...' : 'Sync Intelligence'}</span>
                                            </button>
                                        </div>
                                    </div>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        {[
                                            { name: 'Agmarknet API', status: 'Connected', delay: 'Real-time' },
                                            { name: 'NFDB Marine Feed', status: 'Connected', delay: '12h Pull' },
                                            { name: 'SentiPulse Social', status: 'Error', delay: 'N/A' },
                                            { name: 'Volza Global Trade', status: 'Standby', delay: 'Weekly' },
                                        ].map((source, idx) => (
                                            <div key={idx} className="p-4 border border-slate-100 dark:border-slate-800 rounded-2xl flex justify-between items-center group hover:border-brand-primary/20 hover:bg-slate-50 dark:hover:bg-slate-800/20 transition-all">
                                                <div className="flex items-center space-x-3">
                                                    <div className={`w-2 h-2 rounded-full ${source.status === 'Connected' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : source.status === 'Error' ? 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.5)]' : 'bg-slate-400'}`} />
                                                    <span className="text-sm font-bold dark:text-slate-300">{source.name}</span>
                                                </div>
                                                <div className="text-right">
                                                    <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">{source.delay}</p>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </motion.div>
                        )}

                        {activeTab !== 'Profile Info' && (
                            <motion.div
                                key="standby-tab"
                                initial={{ opacity: 0, scale: 0.95 }}
                                animate={{ opacity: 1, scale: 1 }}
                                exit={{ opacity: 0, scale: 0.95 }}
                                className="flex flex-col items-center justify-center h-[500px] glass-card bg-white dark:bg-slate-900/10 border-dashed border-2 border-slate-200 dark:border-slate-800/60"
                            >
                                <div className="p-6 bg-slate-50 dark:bg-slate-900/60 rounded-3xl mb-4">
                                    <AlertCircle className="w-12 h-12 text-slate-300 dark:text-slate-700" />
                                </div>
                                <h3 className="text-xl font-bold dark:text-white">{activeTab}</h3>
                                <p className="text-sm text-slate-500 mt-2 text-center max-w-sm">This module is currently in standby mode within your tier. Upgrade your access to unlock advanced configuration.</p>
                                <button className="mt-8 px-6 py-2.5 bg-brand-primary text-white rounded-xl text-xs font-bold shadow-lg shadow-brand-primary/20 hover:scale-[1.05] transition-all">
                                    Request Access
                                </button>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </div>
        </div>
    );
}
