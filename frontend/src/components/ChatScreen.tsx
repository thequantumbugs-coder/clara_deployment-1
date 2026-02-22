import React, { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { ArrowLeft } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import {
  type ChatMessage,
  type OrbState,
  isCardMessage,
  isTextMessage,
  isCollegeBriefMessage,
  isImageCardMessage,
} from '../types/chat';
import VoiceOrbCanvas from './VoiceOrbCanvas';
import { useVoiceAnalyser } from '../hooks/useVoiceAnalyser';
import { useSpeechRecognition } from '../hooks/useSpeechRecognition';
import ClaraBubble from './chat/ClaraBubble';
import UserBubble from './chat/UserBubble';
import CardMessage from './chat/CardMessage';
import CollegeDiaryCard from './chat/CollegeDiaryCard';
import ImageCard from './chat/ImageCard';

const GREETING_TTS_DURATION_MS = 4500;

interface ChatScreenProps {
  messages: ChatMessage[];
  isListening?: boolean;
  isSpeaking?: boolean;
  isProcessing?: boolean;
  isConnected?: boolean;
  payload?: { audioBase64?: string; error?: string } | null;
  onBack: () => void;
  onOrbTap: () => void;
  sendMessage: (msg: object) => void;
}

export default function ChatScreen({
  messages: payloadMessages,
  isListening = false,
  isSpeaking = false,
  isProcessing = false,
  isConnected = true,
  payload,
  onBack,
  onOrbTap,
  sendMessage,
}: ChatScreenProps) {
  const { t, language } = useLanguage();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [recognitionError, setRecognitionError] = useState<string | null>(null);
  const { startListening: startSpeechRecognition } = useSpeechRecognition(sendMessage, language, (_, message) => setRecognitionError(message));
  const [hasStarted, setHasStarted] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>(() => []);
  const [orbState, setOrbState] = useState<OrbState>('idle');
  const [isPlayingBackendAudio, setIsPlayingBackendAudio] = useState(false);
  const userRequestedListeningRef = useRef(false);
  const lastPlayedAudioRef = useRef<string | null>(null);
  const isPlayingRef = useRef(false);

  const voiceAnalyser = useVoiceAnalyser(orbState === 'listening');
  // Use only local playback state so orb returns to idle when audio ends; payload.isSpeaking is not cleared by backend and would otherwise block mic tap forever
  const effectiveSpeaking = isPlayingBackendAudio;

  // Play payload.audioBase64 when present (single playback at a time). Playback error must clear speaking state so the orb does not get stuck.
  useEffect(() => {
    const audioBase64 = payload?.audioBase64;
    if (!audioBase64 || audioBase64 === lastPlayedAudioRef.current || isPlayingRef.current) return;
    lastPlayedAudioRef.current = audioBase64;
    isPlayingRef.current = true;
    setIsPlayingBackendAudio(true);
    try {
      const binary = atob(audioBase64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      const blob = new Blob([bytes], { type: 'audio/wav' });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      const onEnd = () => {
        URL.revokeObjectURL(url);
        isPlayingRef.current = false;
        setIsPlayingBackendAudio(false);
      };
      audio.addEventListener('ended', onEnd);
      audio.addEventListener('error', onEnd);
      audio.play().catch(() => onEnd());
    } catch {
      isPlayingRef.current = false;
      setIsPlayingBackendAudio(false);
    }
  }, [payload?.audioBase64]);

  // Derive orb state: backend flags + playback + silence detection + user tap
  useEffect(() => {
    if (effectiveSpeaking) {
      userRequestedListeningRef.current = false;
      setOrbState('speaking');
      return;
    }
    if (isProcessing) {
      setOrbState('processing');
      return;
    }
    if (isListening || userRequestedListeningRef.current) {
      if (orbState === 'listening' && voiceAnalyser.isSilent) {
        userRequestedListeningRef.current = false;
        setOrbState('off');
      } else {
        setOrbState('listening');
      }
      return;
    }
    if (!hasStarted) return;
    setOrbState('idle');
  }, [isListening, isProcessing, effectiveSpeaking, hasStarted, voiceAnalyser.isSilent]);

  // Initialize with greeting and send conversation_started; fallback idle after 4.5s if no backend audio
  useEffect(() => {
    if (hasStarted) return;
    const greeting: ChatMessage = {
      id: 'greeting',
      role: 'clara',
      text: t('claraGreeting'),
    };
    setMessages((prev) => (prev.length ? prev : [greeting]));
    setHasStarted(true);
    setOrbState('speaking');
    sendMessage({ action: 'conversation_started' });
    const timeoutId = setTimeout(() => {
      if (!isPlayingRef.current) setOrbState('idle');
    }, GREETING_TTS_DURATION_MS);
    return () => clearTimeout(timeoutId);
  }, [t, sendMessage, hasStarted]);

  // Sync with payload messages (backend can append)
  useEffect(() => {
    if (!payloadMessages?.length) return;
    setMessages((prev) => {
      const ids = new Set(prev.map((m) => m.id));
      const next = [...prev];
      for (const m of payloadMessages) {
        if (!ids.has(m.id)) {
          ids.add(m.id);
          next.push(m);
        }
      }
      return next;
    });
  }, [payloadMessages]);

  // Auto-scroll to bottom
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  // Auto-clear recognition error after 6s so message does not stay forever
  useEffect(() => {
    if (!recognitionError) return;
    const id = setTimeout(() => setRecognitionError(null), 6000);
    return () => clearTimeout(id);
  }, [recognitionError]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="w-full h-full flex flex-col bg-stone-950 relative"
      data-testid="chat-screen"
    >
      {/* Warm radial glow - center */}
      <div className="absolute inset-0 warm-glow pointer-events-none z-0" />

      {/* Minimal header */}
      <header className="relative z-10 flex items-center justify-between px-8 py-6 flex-shrink-0">
        <motion.button
          type="button"
          whileTap={{ scale: 0.92 }}
          onClick={onBack}
          className="touch-button min-w-[100px] min-h-[100px] rounded-full glass flex items-center justify-center border-white/10 hover:border-neo-mint/20 transition-colors"
          aria-label={t('chatBack')}
        >
          <ArrowLeft className="w-8 h-8 text-stone-400" />
        </motion.button>
        <h1
          className="text-stone-100 font-display italic tracking-wide"
          style={{ fontSize: 'clamp(1.75rem, 3vw + 16px, 2.25rem)' }}
        >
          CLARA
        </h1>
        <div className="w-[100px]" aria-hidden />
      </header>

      {/* Scrollable chat - no visible scrollbar */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto overflow-x-hidden no-scrollbar px-8 py-6 space-y-8"
      >
        <AnimatePresence mode="popLayout">
          {messages.map((msg) => (
            <div key={msg.id} className="flex flex-col gap-2">
              {isCollegeBriefMessage(msg) ? (
                <CollegeDiaryCard message={msg} />
              ) : isImageCardMessage(msg) ? (
                <ImageCard message={msg} />
              ) : isCardMessage(msg) ? (
                <CardMessage
                  message={msg}
                  listeningLabel={isListening ? t('listening') : undefined}
                />
              ) : isTextMessage(msg) ? (
                msg.role === 'clara' ? (
                  <ClaraBubble message={msg} />
                ) : (
                  <UserBubble message={msg} />
                )
              ) : null}
            </div>
          ))}
        </AnimatePresence>
      </div>

      {/* Payload error (e.g. Groq/TTS failure) */}
      {payload?.error && (
        <div className="relative z-10 px-8 py-2 text-center text-sm text-amber-400/90" role="alert">
          {payload.error}
        </div>
      )}

      {/* Speech recognition error (e.g. mic denied, unsupported browser) */}
      {recognitionError && (
        <div className="relative z-10 px-8 py-2 text-center text-sm text-amber-400/90" role="alert">
          {recognitionError}
        </div>
      )}

      {/* Bottom: orb + contextual bar */}
      <div className="relative z-10 flex-shrink-0 flex flex-col items-center pb-10 pt-6">
        <div className="glass rounded-3xl px-8 py-6 flex items-center justify-center gap-6">
          <VoiceOrbCanvas
            state={orbState}
            onTap={() => {
              setRecognitionError(null);
              if (!isConnected) {
                setRecognitionError('Please wait for connection to backend.');
                return;
              }
              const canStart = (orbState === 'idle' || orbState === 'off') && !isPlayingBackendAudio && !isProcessing;
              if (canStart) {
                userRequestedListeningRef.current = true;
                onOrbTap();
                startSpeechRecognition();
              }
            }}
            label={orbState === 'idle' ? t('tapToSpeak') : orbState === 'listening' ? t('listening') : orbState === 'off' ? t('tapToSpeak') : undefined}
            audio={orbState === 'listening' ? { smoothedRms: voiceAnalyser.smoothedRms, smoothedFrequency: voiceAnalyser.smoothedFrequency } : undefined}
          />
        </div>
      </div>
    </motion.div>
  );
}
