"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Phone, PhoneOff, Loader2 } from 'lucide-react';
import VoiceWaveform from './VoiceWaveform';
import { getMessages, saveMessage } from '@/lib/db';

export default function VoiceChatButton({
    onServerResponse,
    language = 'English'
}: {
    onServerResponse: (msg: any) => void,
    language?: string
}) {
    const [isCallActive, setIsCallActive] = useState(false);
    const [isRecording, setIsRecording] = useState(false);
    const [isProcessing, setIsProcessing] = useState(false);

    // WebSocket & Media
    const wsRef = useRef<WebSocket | null>(null);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);

    // Silence Detection / Flow Control
    const isCallActiveRef = useRef(false);
    const streamRef = useRef<MediaStream | null>(null);
    const silenceDetectorRef = useRef<number | null>(null);

    // TTS Audio Queue (ensures overlapping sentences wait their turn)
    const audioQueueRef = useRef<string[]>([]);
    const isPlayingRef = useRef(false);
    const isLlmDoneRef = useRef(true); // Is the LLM finished answering?

    const playNextAudio = async () => {
        if (isPlayingRef.current) return; // Wait for current to finish
        if (audioQueueRef.current.length === 0) {
            // If queue is empty AND LLM has finished streaming
            if (isLlmDoneRef.current && isCallActiveRef.current && !isRecording) {
                // The AI finished talking. Now we listen again!
                startRecording();
            }
            return;
        }

        isPlayingRef.current = true;
        const nextAudioUrl = audioQueueRef.current.shift()!;
        const audio = new window.Audio(nextAudioUrl);

        audio.onended = () => {
            isPlayingRef.current = false;
            URL.revokeObjectURL(nextAudioUrl); // Cleanup memory
            playNextAudio();
        };

        audio.play().catch(err => {
            console.error("Audio Decode Error", err);
            isPlayingRef.current = false;
            playNextAudio();
        });
    };

    useEffect(() => {
        const connect = () => {
            const ws = new WebSocket('ws://localhost:8000/ws/voice-chat');
            ws.onopen = () => console.log('Voice Socket Connected');
            ws.onmessage = async (e) => {
                if (typeof e.data === 'string') {
                    const msg = JSON.parse(e.data);
                    if (msg.type === 'transcript') {
                        saveMessage({ role: 'user', text: msg.text });
                        // onServerResponse({ role: 'user', text: msg.text });
                        isLlmDoneRef.current = false;
                    }
                    if (msg.type === 'llm_start') {
                        setIsProcessing(true); // AI is "thinking"
                    }
                    if (msg.type === 'llm_chunk') {
                        // onServerResponse({ _type: 'partial', delta: msg.text });
                    }
                    if (msg.type === 'llm_end') {
                        setIsProcessing(false);
                        isLlmDoneRef.current = true;
                        saveMessage({ role: 'bot', text: msg.full_text });
                        // onServerResponse({ _type: 'final', role: 'bot', text: msg.full_text });
                        // Trigger play attempt just in case queue is stuck or was empty
                        playNextAudio();
                    }
                } else if (e.data instanceof Blob) {
                    // It's TTS Audio MP3 chunk! Queue it up.
                    const audioUrl = URL.createObjectURL(e.data);
                    audioQueueRef.current.push(audioUrl);
                    playNextAudio();
                }
            };
            ws.onclose = () => { console.log('Voice socket closed; reconnecting...'); setTimeout(connect, 3000); };
            wsRef.current = ws;
        };
        connect();
        return () => {
            wsRef.current?.close();
            endCall();
        };
    }, []);

    const setupSilenceDetector = (stream: MediaStream) => {
        const audioContext = new window.AudioContext();
        const source = audioContext.createMediaStreamSource(stream);
        const analyser = audioContext.createAnalyser();
        analyser.minDecibels = -60; // Noise floor
        source.connect(analyser);

        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        let silenceStart = Date.now();
        let hasSpoken = false;

        const checkSilence = () => {
            if (!isCallActiveRef.current || !mediaRecorderRef.current || mediaRecorderRef.current.state === 'inactive') return;

            analyser.getByteFrequencyData(dataArray);
            const sum = dataArray.reduce((innerSum, val) => innerSum + val, 0);
            const avg = sum / dataArray.length;

            if (avg > 15) {
                // User is making noise! Reset timer.
                hasSpoken = true;
                silenceStart = Date.now();
            } else {
                if (hasSpoken && Date.now() - silenceStart > 1800) {
                    // 1.8 seconds of silence AFTER they spoke! Turn over to AI.
                    stopRecordingLocally();
                    return; // Stop animation loop
                } else if (!hasSpoken && Date.now() - silenceStart > 5000) {
                    // 5 seconds total silence without ever speaking. Prompt AI or kill
                    stopRecordingLocally();
                    return;
                }
            }
            silenceDetectorRef.current = requestAnimationFrame(checkSilence);
        };
        silenceDetectorRef.current = requestAnimationFrame(checkSilence);
    };

    const startRecording = async () => {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return;
        try {
            if (!streamRef.current) {
                streamRef.current = await navigator.mediaDevices.getUserMedia({ audio: true });
            }
            const stream = streamRef.current;

            // Reinitialize MediaRecorder to clean buffers
            const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
            mediaRecorderRef.current = mediaRecorder;

            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0 && wsRef.current?.readyState === WebSocket.OPEN) {
                    wsRef.current.send(e.data);
                }
            };

            mediaRecorder.onstop = async () => {
                const history = await getMessages(5);
                const historyForBackend = history.map(m => ({ role: m.role, text: m.text }));

                if (wsRef.current?.readyState === WebSocket.OPEN) {
                    wsRef.current.send(JSON.stringify({
                        type: 'audio_end',
                        history: historyForBackend,
                        language: language
                    }));
                }
                setIsRecording(false);
                setIsProcessing(true); // Waiting for LLM
            };

            // Stream chunks
            mediaRecorder.start(500);
            setIsRecording(true);

            // Start listening for silence to auto-turn over
            setupSilenceDetector(stream);

        } catch (err) {
            console.error('Mic access denied or failed', err);
            endCall();
        }
    };

    const stopRecordingLocally = () => {
        if (silenceDetectorRef.current) cancelAnimationFrame(silenceDetectorRef.current);
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            mediaRecorderRef.current.stop();
        }
    };

    const toggleCall = () => {
        if (isCallActive) {
            endCall();
        } else {
            startCall();
        }
    };

    const startCall = () => {
        setIsCallActive(true);
        isCallActiveRef.current = true;

        // Wait for connection
        const triggerInit = async () => {
            if (wsRef.current?.readyState === WebSocket.OPEN) {
                const history = await getMessages(5);
                const historyForBackend = history.map(m => ({ role: m.role, text: m.text }));

                wsRef.current.send(JSON.stringify({
                    type: 'init_call',
                    history: historyForBackend,
                    language: language
                }));
                isLlmDoneRef.current = false;
            } else {
                setTimeout(triggerInit, 500);
            }
        };
        triggerInit();
    };

    const endCall = () => {
        setIsCallActive(false);
        isCallActiveRef.current = false;
        setIsRecording(false);
        setIsProcessing(false);

        stopRecordingLocally();

        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop());
            streamRef.current = null;
        }

        // Clear caches
        audioQueueRef.current = [];
        isPlayingRef.current = false;
    };

    return (
        <div className="relative flex items-center justify-center">
            {isRecording && <VoiceWaveform isRecording={isRecording} />}
            <button
                onClick={toggleCall}
                title={isCallActive ? "End Call" : "Start Voice Call"}
                className={`w-12 h-12 rounded-xl flex items-center justify-center transition-all ${isCallActive
                    ? 'bg-rose-500 hover:bg-rose-600 text-white shadow-rose-500/50 shadow-lg'
                    : 'bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 shadow-lg border border-emerald-500/30'
                    }`}
            >
                {isProcessing && isCallActive ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                ) : isCallActive ? (
                    <PhoneOff className="w-5 h-5" fill="currentColor" />
                ) : (
                    <Phone className="w-5 h-5" fill="currentColor" />
                )}
            </button>
        </div>
    );
}
