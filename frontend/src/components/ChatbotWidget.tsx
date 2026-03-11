"use client";

import React, { useState, useRef, useEffect } from 'react';
import { Bot, X, Send, User, ChevronUp, Loader2, BarChart2, TrendingUp, TrendingDown, DollarSign } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import VoiceChatButton from './VoiceChatButton';
import { getMessages, saveMessage } from '@/lib/db';

type Message = {
    id: string;
    role: 'user' | 'bot';
    text: string;
    data?: any;
    intent?: string;
    commodity?: string;
};

export default function ChatbotWidget() {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState<Message[]>([
        {
            id: 'welcome',
            role: 'bot',
            text: 'Hello! I am your AI Market Analyst. I can provide real-time prices, future forecasts, and trend explanations across 21 commodities. How can I help you today?',
        }
    ]);
    const [inputValue, setInputValue] = useState('');
    const [isTyping, setIsTyping] = useState(false);
    const [language, setLanguage] = useState('English');
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        const loadHistory = async () => {
            const history = await getMessages(20);
            if (history.length > 0) {
                setMessages(history.map(m => ({
                    id: m.timestamp.toString(),
                    role: m.role,
                    text: m.text
                })));
            }
        };
        loadHistory();
    }, []);

    useEffect(() => {
        scrollToBottom();
    }, [messages, isTyping]);

    const handleSendMessage = async () => {
        if (!inputValue.trim()) return;

        const userText = inputValue;
        setInputValue('');

        const newUserMsg: Message = { id: Date.now().toString(), role: 'user', text: userText };
        setMessages(prev => [...prev, newUserMsg]);
        saveMessage({ role: 'user', text: userText });
        setIsTyping(true);

        try {
            // Prepare history for backend
            const historyForBackend = messages.slice(-5).map(m => ({ role: m.role, text: m.text }));

            const res = await fetch('http://localhost:8000/api/v1/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: userText,
                    language: language,
                    history: historyForBackend
                })
            });
            const data = await res.json();

            const botMsg: Message = {
                id: (Date.now() + 1).toString(),
                role: 'bot',
                text: data.text,
                data: data.data,
                intent: data.intent,
                commodity: data.commodity
            };
            setMessages(prev => [...prev, botMsg]);
            saveMessage({ role: 'bot', text: data.text });
        } catch (error) {
            console.error('Chat error:', error);
            setMessages(prev => [...prev, {
                id: (Date.now() + 1).toString(),
                role: 'bot',
                text: "I couldn't reach the intelligence engine. Please try again later."
            }]);
        } finally {
            setIsTyping(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') handleSendMessage();
    };

    const renderDataWidget = (msg: Message) => {
        if (!msg.data || msg.intent === 'error' || msg.intent === 'unknown') return null;

        if (msg.intent === 'price') {
            return (
                <div className="mt-3 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-bold text-sm flex items-center gap-2">
                    <DollarSign className="w-4 h-4" />
                    Latest: ₹{msg.data.price} per quintal
                </div>
            );
        }

        if (msg.intent === 'trend') {
            const isUp = msg.data.change_percentage > 0;
            return (
                <div className={`mt-3 p-3 rounded-lg border text-sm flex items-center gap-2 font-bold ${isUp ? 'bg-rose-500/10 border-rose-500/20 text-rose-400' : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'}`}>
                    {isUp ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                    {Math.abs(msg.data.change_percentage)}% {isUp ? 'Increase' : 'Decrease'}
                </div>
            );
        }

        if (msg.intent === 'forecast' && !msg.data.error) {
            const isBullish = msg.data.trend === 'Bullish';
            return (
                <div className="mt-3 p-3 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-sm space-y-2">
                    <div className="flex items-center gap-2 font-bold text-indigo-400">
                        <BarChart2 className="w-4 h-4" />
                        AI Forecast Prediction
                    </div>
                    <div className="flex justify-between items-center bg-black/20 p-2 rounded">
                        <span className="text-slate-300">Trend Signal</span>
                        <span className={`px-2 py-0.5 rounded text-xs font-bold ${isBullish ? 'bg-rose-500/20 text-rose-400' : 'bg-emerald-500/20 text-emerald-400'}`}>
                            {msg.data.trend}
                        </span>
                    </div>
                    <div className="flex justify-between items-center bg-black/20 p-2 rounded">
                        <span className="text-slate-300">Confidence</span>
                        <span className="text-white font-bold">{Math.round(msg.data.confidence_score)}%</span>
                    </div>
                </div>
            );
        }

        return null;
    };

    return (
        <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end">
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0, y: 20, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 20, scale: 0.95 }}
                        className="mb-4 w-[380px] max-w-[calc(100vw-48px)] h-[550px] max-h-[80vh] flex flex-col rounded-2xl overflow-hidden glass-card border border-brand-primary/20 shadow-2xl shadow-brand-primary/10 bg-slate-900/90 backdrop-blur-xl"
                    >
                        {/* Header */}
                        <div className="flex items-center justify-between p-4 bg-gradient-to-r from-brand-primary/20 to-indigo-500/20 border-b border-white/5">
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-full bg-brand-primary/20 flex items-center justify-center border border-brand-primary/50 relative">
                                    <Bot className="w-5 h-5 text-brand-primary" />
                                    <span className="absolute -bottom-1 -right-1 w-3 h-3 rounded-full bg-emerald-500 border border-slate-900 shadow-lg"></span>
                                </div>
                                <div>
                                    <h3 className="font-bold text-slate-100">Market Analyst AI</h3>
                                    <p className="text-xs text-brand-secondary">powered by Llama 3</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <select
                                    value={language}
                                    onChange={(e) => setLanguage(e.target.value)}
                                    className="bg-slate-800 border border-slate-700 text-white text-xs rounded px-2 py-1 outline-none"
                                >
                                    <option value="English">English</option>
                                    <option value="Hindi">Hindi</option>
                                    <option value="Tamil">Tamil</option>
                                    <option value="Telugu">Telugu</option>
                                    <option value="Marathi">Marathi</option>
                                    <option value="Gujarati">Gujarati</option>
                                    <option value="Bengali">Bengali</option>
                                </select>
                                <button
                                    onClick={() => setIsOpen(false)}
                                    className="p-1.5 rounded-full hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
                                >
                                    <X className="w-5 h-5" />
                                </button>
                            </div>
                        </div>

                        {/* Chat Messages */}
                        <div className="flex-1 overflow-y-auto p-4 space-y-4">
                            {messages.map((msg) => (
                                <div
                                    key={msg.id}
                                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                                >
                                    <div className={`flex flex-col max-w-[85%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                                        <div
                                            className={`p-3 rounded-2xl ${msg.role === 'user'
                                                ? 'bg-brand-primary text-white rounded-tr-sm'
                                                : 'bg-slate-800 text-slate-200 border border-slate-700/50 rounded-tl-sm shadow-md'
                                                }`}
                                        >
                                            <div className="text-sm leading-relaxed prose prose-invert prose-p:my-1 prose-headings:my-2 prose-ul:my-1 prose-li:my-0">
                                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                    {msg.text}
                                                </ReactMarkdown>
                                            </div>
                                        </div>
                                        {renderDataWidget(msg)}
                                    </div>
                                </div>
                            ))}
                            {isTyping && (
                                <div className="flex justify-start">
                                    <div className="bg-slate-800 border border-slate-700/50 p-4 rounded-2xl rounded-tl-sm flex items-center gap-2">
                                        <Loader2 className="w-4 h-4 text-brand-primary animate-spin" />
                                        <span className="text-xs text-slate-400 font-medium">Analyzing market signals...</span>
                                    </div>
                                </div>
                            )}
                            <div ref={messagesEndRef} />
                        </div>

                        {/* Input Area */}
                        <div className="p-4 bg-slate-950/50 border-t border-white/5 pb-[60px]">
                            <div className="flex items-center gap-2">
                                <VoiceChatButton
                                    language={language}
                                    onServerResponse={(msg) => {
                                        if (msg._type === 'partial') {
                                            // Ignore UI update for streaming, or append to a streaming message buffer
                                        } else if (msg._type === 'final') {
                                            setMessages(prev => [...prev, { id: Date.now().toString(), role: 'bot', text: msg.text }]);
                                            saveMessage({ role: 'bot', text: msg.text });
                                            setIsTyping(false);
                                        } else if (msg.role === 'user') {
                                            setMessages(prev => [...prev, { id: Date.now().toString(), role: 'user', text: msg.text }]);
                                            saveMessage({ role: 'user', text: msg.text });
                                            setIsTyping(true); // Wait for bot LLM
                                        }
                                    }} />
                                <input
                                    type="text"
                                    value={inputValue}
                                    onChange={(e) => setInputValue(e.target.value)}
                                    onKeyDown={handleKeyDown}
                                    placeholder="Ask about prices, forecasts, or trends..."
                                    className="flex-1 bg-slate-800/80 border border-slate-700 text-white placeholder:text-slate-500 text-sm rounded-xl px-4 py-3 focus:outline-none focus:border-brand-primary focus:ring-1 focus:ring-brand-primary transition-all"
                                />
                                <button
                                    onClick={handleSendMessage}
                                    disabled={!inputValue.trim() || isTyping}
                                    className="w-12 h-12 rounded-xl bg-brand-primary text-white flex items-center justify-center hover:bg-brand-primary/80 disabled:opacity-50 disabled:cursor-not-allowed transition-all shrink-0 shadow-lg"
                                >
                                    <Send className="w-5 h-5 -ml-0.5" />
                                </button>
                            </div>
                            <div className="mt-2 text-[10px] text-center text-slate-500">
                                Try: "Onion forecast", or "Wheat trends en español"
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Toggle Button */}
            <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setIsOpen(!isOpen)}
                className={`w-14 h-14 rounded-full flex items-center justify-center shadow-2xl transition-all ${isOpen
                    ? 'bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700'
                    : 'bg-brand-primary text-white border-2 border-brand-primary/50 hover:shadow-brand-primary/50'
                    }`}
            >
                <AnimatePresence mode="wait">
                    {isOpen ? (
                        <motion.div
                            key="close"
                            initial={{ rotate: -90, opacity: 0 }}
                            animate={{ rotate: 0, opacity: 1 }}
                            exit={{ rotate: 90, opacity: 0 }}
                        >
                            <ChevronUp className="w-6 h-6 rotate-180" />
                        </motion.div>
                    ) : (
                        <motion.div
                            key="bot"
                            initial={{ rotate: 90, opacity: 0 }}
                            animate={{ rotate: 0, opacity: 1 }}
                            exit={{ rotate: -90, opacity: 0 }}
                        >
                            <Bot className="w-6 h-6" />
                        </motion.div>
                    )}
                </AnimatePresence>
            </motion.button>
        </div>
    );
}
