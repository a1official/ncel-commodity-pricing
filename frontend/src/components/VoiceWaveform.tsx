"use client";

import React, { useRef, useEffect } from 'react';
import { motion } from 'framer-motion';

export default function VoiceWaveform({ isRecording }: { isRecording: boolean }) {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        if (!isRecording || !canvasRef.current) return;
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        let animationFrame: number;
        const bars = 10;

        const draw = () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            for (let i = 0; i < bars; i++) {
                const x = i * (canvas.width / bars);
                const width = (canvas.width / bars) - 2;
                // Random height for wave animation
                const minH = 5;
                const maxH = canvas.height * 0.8;
                const height = Math.random() * (maxH - minH) + minH;
                const y = (canvas.height - height) / 2;

                ctx.fillStyle = '#10B981'; // Emerald brand primary
                ctx.beginPath();
                ctx.roundRect(x, y, width, height, 4);
                ctx.fill();
            }
            animationFrame = requestAnimationFrame(draw);
        };

        // Lower frame rate for smoother effect
        const interval = setInterval(() => {
            draw();
        }, 100);

        return () => {
            cancelAnimationFrame(animationFrame);
            clearInterval(interval);
            ctx.clearRect(0, 0, canvas.width, canvas.height);
        };
    }, [isRecording]);

    if (!isRecording) return null;

    return (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="absolute bottom-[60px] right-0 bg-slate-800 p-2 rounded border border-slate-700 shadow-xl">
            <canvas ref={canvasRef} width={60} height={30} className="rounded" />
        </motion.div>
    );
}
