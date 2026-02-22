import { useCallback, useRef } from 'react';
import type { Language } from '../context/LanguageContext';

const LANGUAGE_TO_BCP47: Record<Language, string> = {
  English: 'en-IN',
  Kannada: 'kn-IN',
  Hindi: 'hi-IN',
  Tamil: 'ta-IN',
  Telugu: 'te-IN',
  Malayalam: 'ml-IN',
};

function errorCodeToMessage(code: string): string {
  switch (code) {
    case 'not-allowed':
      return 'Microphone access denied.';
    case 'no-speech':
      return 'No speech heard. Try again.';
    case 'network':
      return 'Network error. Try again.';
    case 'aborted':
      return 'Listening stopped.';
    case 'audio-capture':
      return 'No microphone found.';
    case 'service-not-allowed':
      return 'Browser blocked voice input.';
    default:
      return 'Voice input failed. Try again.';
  }
}

export function useSpeechRecognition(
  sendMessage: (msg: object) => boolean | void,
  language: Language,
  onError?: (errorCode: string, userMessage: string) => void
) {
  const recognitionRef = useRef<{ stop: () => void; abort?: () => void } | null>(null);
  const isListeningRef = useRef(false);
  const sendMessageRef = useRef(sendMessage);
  sendMessageRef.current = sendMessage;

  const startListening = useCallback(() => {
    if (isListeningRef.current) return;

    const win = typeof window !== 'undefined' ? window : null;
    const SpeechRecognitionCtor = win
      ? (win as unknown as { SpeechRecognition?: new () => SpeechRecognition; webkitSpeechRecognition?: new () => SpeechRecognition }).SpeechRecognition ||
        (win as unknown as { webkitSpeechRecognition?: new () => SpeechRecognition }).webkitSpeechRecognition
      : undefined;
    if (!SpeechRecognitionCtor) {
      onError?.('unsupported', 'Voice input is not supported. Please use Chrome or Edge.');
      return;
    }

    const recognition = new SpeechRecognitionCtor();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = LANGUAGE_TO_BCP47[language] || 'en-IN';

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const result = event.results[event.resultIndex];
      const transcript = result?.[0]?.transcript?.trim();
      if (transcript) {
        const sent = sendMessageRef.current({ action: 'user_message', text: transcript });
        if (sent === false) onError?.('network', 'Connection lost. Try again.');
      }
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      const code = event.error || 'unknown';
      onError?.(code, errorCodeToMessage(code));
      recognitionRef.current = null;
      isListeningRef.current = false;
      try {
        if (typeof recognition.abort === 'function') recognition.abort();
      } catch {
        // ignore
      }
    };

    recognition.onend = () => {
      recognitionRef.current = null;
      isListeningRef.current = false;
    };

    try {
      recognition.start();
      recognitionRef.current = recognition;
      isListeningRef.current = true;
    } catch {
      onError?.('start-failed', 'Could not start microphone. Try again.');
      recognitionRef.current = null;
      isListeningRef.current = false;
    }
  }, [language, onError]);

  return { startListening };
}
