"use client";

import React, { useMemo, useState } from "react";
import {
    ComposableMap,
    Geographies,
    Geography,
    Marker
} from "react-simple-maps";
import { motion, AnimatePresence } from "framer-motion";

interface Market {
    id: number;
    name: string;
    lat: number;
    lon: number;
}

interface Props {
    markets: Market[];
    selectedRegion?: string;
    onNodeClick?: (m: Market) => void;
}

const geoUrl = "/india-states.json";

export default function IndiaMap({ markets, selectedRegion = "All India", onNodeClick }: Props) {
    const [hovered, setHovered] = useState<number | null>(null);

    const nodes = useMemo(() => markets, [markets]);

    return (
        <div className="relative w-full h-full bg-[#020512] overflow-hidden">

            {/* GRID BACKGROUND */}
            <div
                className="absolute inset-0 opacity-[0.05]"
                style={{
                    backgroundImage:
                        "linear-gradient(#1e293b 1px, transparent 1px), linear-gradient(90deg, #1e293b 1px, transparent 1px)",
                    backgroundSize: "40px 40px",
                }}
            />

            {/* MAP */}
            <div className="absolute inset-0 flex items-center justify-center">

                <ComposableMap
                    projection="geoMercator"
                    projectionConfig={{
                        scale: 1150,
                        center: [78.9629, 22.5937], // Center of India [lon, lat]
                    }}
                    className="w-[85%] h-[85%]"
                >
                    <defs>
                        <radialGradient id="mapGlow">
                            <stop offset="0%" stopColor="#1e40af" stopOpacity="0.4" />
                            <stop offset="100%" stopColor="#020617" stopOpacity="1" />
                        </radialGradient>
                    </defs>

                    <Geographies geography={geoUrl}>
                        {({ geographies }) =>
                            geographies.map((geo) => (
                                <Geography
                                    key={geo.rsmKey}
                                    geography={geo}
                                    fill="url(#mapGlow)"
                                    stroke="#4f46e5"
                                    strokeWidth={0.3}
                                    style={{
                                        default: { outline: "none" },
                                        hover: { fill: "#1e40af", outline: "none", transition: "all 0.3s" },
                                        pressed: { outline: "none" },
                                    }}
                                />
                            ))
                        }
                    </Geographies>

                    {/* NODES */}
                    {nodes.filter(n => n.lat && n.lon).map((node) => {
                        const isDimmed = selectedRegion !== "All India" &&
                            !node.name.toLowerCase().includes(selectedRegion.toLowerCase().replace(' hub', '').replace(' ports', ''));

                        return (
                            <Marker key={node.id} coordinates={[node.lon, node.lat]}>
                                <motion.circle
                                    r={isDimmed ? 1.5 : 2.5}
                                    fill={isDimmed ? "#334155" : "#a5b4fc"}
                                    className="cursor-pointer"
                                    onClick={() => onNodeClick?.(node)}
                                    onMouseEnter={() => setHovered(node.id)}
                                    onMouseLeave={() => setHovered(null)}
                                    initial={{ scale: 0, opacity: 0 }}
                                    animate={{
                                        scale: [1, 1.3, 1],
                                        opacity: isDimmed ? 0.4 : 1
                                    }}
                                    transition={{
                                        scale: { duration: 2, repeat: Infinity },
                                        opacity: { duration: 0.3 }
                                    }}
                                />

                                {/* Bloom Effect for active nodes */}
                                {!isDimmed && (
                                    <circle
                                        r={6}
                                        fill="#6366f1"
                                        className="opacity-20 pointer-events-none"
                                        style={{ filter: "blur(4px)" }}
                                    />
                                )}

                                <AnimatePresence>
                                    {hovered === node.id && (
                                        <motion.foreignObject
                                            x={10}
                                            y={-30}
                                            width={160}
                                            height={50}
                                            initial={{ opacity: 0, scale: 0.8 }}
                                            animate={{ opacity: 1, scale: 1 }}
                                            exit={{ opacity: 0, scale: 0.8 }}
                                        >
                                            <div className="bg-[#0f172a]/95 text-white p-2 rounded-lg border border-white/20 shadow-2xl backdrop-blur-md">
                                                <div className="flex items-center space-x-2">
                                                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                                                    <span className="text-[10px] font-bold uppercase tracking-widest">{node.name}</span>
                                                </div>
                                                <p className="text-[8px] text-slate-400 mt-1">LAT: {node.lat.toFixed(2)} LON: {node.lon.toFixed(2)}</p>
                                            </div>
                                        </motion.foreignObject>
                                    )}
                                </AnimatePresence>
                            </Marker>
                        );
                    })}
                </ComposableMap>
            </div>

            {/* Technical Metadata Overlays (Sidebar and Bottom) */}
            <div className="absolute top-10 left-10 flex items-start space-x-4 pointer-events-none">
                <div className="w-[2px] h-10 bg-gradient-to-b from-brand-primary to-transparent" />
                <div className="space-y-1">
                    <h4 className="text-[10px] font-black text-brand-primary uppercase tracking-[0.3em]">Sector Surveillance</h4>
                    <p className="text-[16px] font-bold text-white tracking-widest">{selectedRegion.toUpperCase()}</p>
                </div>
            </div>

            <div className="absolute bottom-10 right-10 flex flex-col items-end pointer-events-none">
                <div className="flex space-x-8 mb-4">
                    <div className="text-right">
                        <p className="text-[8px] font-black text-slate-500 uppercase tracking-widest">Global Indexing</p>
                        <p className="text-xs font-bold text-white tracking-widest">{markets.length} NODES</p>
                    </div>
                </div>
                <div className="px-3 py-1 bg-white/5 border border-white/10 rounded text-[9px] font-bold text-slate-400 tracking-tighter uppercase whitespace-nowrap">
                    GEO-JSON ENGINE / SCALE 1.15
                </div>
            </div>
        </div>
    );
}