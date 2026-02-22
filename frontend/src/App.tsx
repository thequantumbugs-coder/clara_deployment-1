import React, { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { useWebSocket } from './hooks/useWebSocket';
import { LanguageProvider } from './context/LanguageContext';

// Components
import SleepScreen from './components/SleepScreen';
import LanguageSelect from './components/LanguageSelect';
import ChatScreen from './components/ChatScreen';
import type { ChatMessage } from './types/chat';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:6969/ws/clara';
const BACKEND_URL = (() => {
  try {
    const u = new URL(WS_URL.replace(/^ws/, 'http'));
    return `${u.origin}`;
  } catch {
    return 'http://localhost:6969';
  }
})();

export default function App() {
  const { state, payload, isConnected, hasAttemptedConnect, setManualState, sendMessage, retryConnect } = useWebSocket(WS_URL);
  const [urlOverrideState, setUrlOverrideState] = React.useState<number | null>(null);

  // E2E / test: ?state=5 opens chat directly; sticky so WS cannot overwrite
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const s = params.get('state');
    if (s !== null) {
      const n = parseInt(s, 10);
      if (n >= 0 && n <= 8) setUrlOverrideState(n);
    }
  }, []);

  const effectiveState = urlOverrideState !== null ? urlOverrideState : state;
  const setEffectiveState = (n: number) => {
    setUrlOverrideState(null);
    setManualState(n);
  };

  // Debug mode: Listen for keys 0-8
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const key = parseInt(e.key);
      if (key >= 0 && key <= 8) {
        console.log(`Debug: Switching to state ${key}`);
        setUrlOverrideState(null);
        setManualState(key);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [setManualState]);

  const renderState = () => {
    switch (effectiveState) {
      case 0:
        return (
          <motion.div key="sleep" className="w-full h-full">
            <SleepScreen 
              onWake={() => {
                sendMessage({ action: 'wake' });
                setUrlOverrideState(null);
                setManualState(3); // Transition to language select
              }} 
            />
          </motion.div>
        );
      case 3:
        return (
          <motion.div key="lang" className="w-full h-full">
            <LanguageSelect 
              onSelect={(language) => {
                sendMessage({ action: 'language_selected', language });
                setUrlOverrideState(null);
                setManualState(5); // Transition to chat (voice) — post-language flow
              }} 
            />
          </motion.div>
        );
      case 4:
      case 5:
        return (
          <motion.div key="voice" className="w-full h-full">
            <ChatScreen
              messages={(payload?.messages as ChatMessage[] | undefined) ?? []}
              isListening={payload?.isListening ?? false}
              isSpeaking={payload?.isSpeaking ?? false}
              isProcessing={payload?.isProcessing ?? false}
              payload={payload}
              isConnected={isConnected}
              onBack={() => setEffectiveState(3)}
              onOrbTap={() => sendMessage({ action: 'toggle_mic' })}
              sendMessage={sendMessage}
            />
          </motion.div>
        );
      default:
        return (
          <motion.div 
            key="fallback"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="w-full h-full flex items-center justify-center"
          >
            <div className="glass p-12 rounded-3xl text-center">
              <h2 className="text-3xl font-display italic mb-4">State {effectiveState}</h2>
              <p className="text-stone-400 tracking-widest uppercase text-sm">
                This interface is currently under development.
              </p>
              <button 
                onClick={() => setEffectiveState(0)}
                className="mt-8 px-8 py-4 border border-white/10 rounded-full hover:bg-white/5 transition-colors"
              >
                Return to Sleep
              </button>
            </div>
          </motion.div>
        );
    }
  };

  return (
    <LanguageProvider>
      <div className="relative w-full h-full bg-stone-950 overflow-hidden">
        {/* Connection banner when backend is unreachable */}
        {hasAttemptedConnect && !isConnected && (
          <div className="absolute top-0 left-0 right-0 z-30 px-4 py-3 bg-amber-500/20 border-b border-amber-500/40 rounded-b-lg text-center text-amber-200 text-sm flex flex-col items-center justify-center gap-1">
            <div className="flex flex-wrap items-center justify-center gap-2">
              <span>Cannot connect to backend at <a href={BACKEND_URL} target="_blank" rel="noopener noreferrer" className="underline">{BACKEND_URL}</a>.</span>
              <button type="button" onClick={retryConnect} className="px-3 py-1 rounded bg-amber-500/40 hover:bg-amber-500/60 text-amber-100 font-medium">Retry</button>
              <span className="text-amber-200/80">or refresh the page.</span>
            </div>
            <div className="text-amber-200/80 text-xs mt-1">
              Start backend from project root: <code className="bg-black/20 px-1 rounded">.\start-backend.ps1</code> or <code className="bg-black/20 px-1 rounded">.\.venv\Scripts\python backend\main.py</code>. Check <a href={`${BACKEND_URL}/health`} target="_blank" rel="noopener noreferrer" className="underline">/health</a>. If you changed frontend/.env.local, restart the frontend (npm run dev).
            </div>
          </div>
        )}
        {/* Global Warm Glow */}
        <div className="absolute inset-0 warm-glow pointer-events-none z-0" />
        
        {/* Main Content */}
        <main className="relative z-10 w-full h-full">
          <AnimatePresence mode="wait">
            {renderState()}
          </AnimatePresence>
        </main>

        {/* Subtle Kiosk Frame/Overlay */}
        <div className="absolute inset-0 border-[24px] border-black/20 pointer-events-none z-50 rounded-[40px]" />
        
        {/* Debug Indicator (Hidden in production) */}
        {process.env.NODE_ENV === 'development' && (
          <div className="absolute bottom-4 right-4 text-[8px] text-stone-800 uppercase tracking-widest pointer-events-none">
            Kiosk Mode Active • State: {effectiveState} • WS: {isConnected ? 'Connected' : 'Disconnected'}
          </div>
        )}
      </div>
    </LanguageProvider>
  );
}
