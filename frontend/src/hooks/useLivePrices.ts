'use client';

import { useEffect, useState } from 'react';

export interface MarketTick {
    symbol: string;
    spot_price: string;
    future_price: string;
    expiry?: string;
    timestamp: string;
}

export function useLiveMarketStream() {
    const [ticks, setTicks] = useState<MarketTick[]>([]);
    const [status, setStatus] = useState<'connecting' | 'open' | 'closed'>('connecting');

    useEffect(() => {
        let socket: WebSocket | null = null;
        let reconnectTimeout: any = null;
        let isStopped = false;

        const connect = () => {
            if (isStopped) return;

            setStatus('connecting');
            console.log('Connecting to NCEL Market stream...');

            try {
                socket = new WebSocket('ws://localhost:8000/ws/market-stream');

                socket.onopen = () => {
                    if (isStopped) {
                        socket?.close();
                        return;
                    }
                    console.log('Connected to NCEL Market stream');
                    setStatus('open');
                };

                socket.onmessage = (event) => {
                    try {
                        const message = JSON.parse(event.data);
                        if (message.type === 'TICKER_UPDATE') {
                            setTicks(message.data);
                        }
                    } catch (err) {
                        console.error('WS parse error:', err);
                    }
                };

                socket.onclose = (event) => {
                    if (isStopped) return;

                    console.log('NCEL Market stream closed:', event.reason || 'No reason provided');
                    setStatus('closed');

                    // Reconnect after 3 seconds
                    reconnectTimeout = setTimeout(connect, 3000);
                };

                socket.onerror = (err) => {
                    console.error('WS Error:', err);
                    // onclose will follow and handle reconnection
                };
            } catch (err) {
                console.error('Failed to create WebSocket:', err);
                reconnectTimeout = setTimeout(connect, 5000);
            }
        };

        // Delay initial connection slightly to avoid Fast Refresh unmount/remount issues
        const initialDelay = setTimeout(connect, 500);

        return () => {
            isStopped = true;
            clearTimeout(initialDelay);
            clearTimeout(reconnectTimeout);
            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.close();
            }
        };
    }, []);

    return { ticks, status };
}
