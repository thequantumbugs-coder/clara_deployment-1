import { useState, useEffect, useCallback, useRef } from 'react';

export interface WSMessage {
  state: number;
  payload?: any;
}

// Singleton per URL: cleanup never closes the socket so Strict Mode re-run always reuses it.
interface SharedEntry {
  socket: WebSocket;
  refCount: number;
  onConnected: (connected: boolean) => void;
  onMessage: (state: number, payload: any) => void;
  state: number;
  payload: any;
}
const sharedByUrl = new Map<string, SharedEntry>();

const NOOP = () => {};

export function useWebSocket(url: string) {
  const [state, setState] = useState<number>(0);
  const [payload, setPayload] = useState<any>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [hasAttemptedConnect, setHasAttemptedConnect] = useState(false);
  const [reconnectTrigger, setReconnectTrigger] = useState(0);
  const stateRef = useRef<number>(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const entryRef = useRef<SharedEntry | null>(null);

  useEffect(() => {
    setHasAttemptedConnect(true);

    let entry = sharedByUrl.get(url);
    const needNewSocket = !entry || entry.socket.readyState === WebSocket.CLOSED;

    if (entry && !needNewSocket) {
      entry.refCount++;
      entry.onConnected = (connected) => setIsConnected(connected);
      entry.onMessage = (s, p) => {
        stateRef.current = s;
        setState(s);
        setPayload(p ?? null);
      };
      entryRef.current = entry;
      if (entry.socket.readyState === WebSocket.OPEN) {
        setIsConnecting(false);
        setIsConnected(true);
        setState(entry.state);
        setPayload(entry.payload);
        stateRef.current = entry.state;
      } else if (entry.socket.readyState === WebSocket.CONNECTING) {
        setIsConnecting(true);
        const syncWhenOpen = () => {
          if (entryRef.current?.socket.readyState === WebSocket.OPEN) {
            setIsConnecting(false);
            setIsConnected(true);
            setState(entryRef.current.state);
            setPayload(entryRef.current.payload);
            stateRef.current = entryRef.current.state;
          }
        };
        const t = setTimeout(syncWhenOpen, 100);
        const t2 = setTimeout(syncWhenOpen, 300);
        return () => {
          clearTimeout(t);
          clearTimeout(t2);
          const e = entryRef.current ?? entry;
          if (!e) return;
          e.refCount--;
          e.onConnected = NOOP;
          e.onMessage = NOOP;
          entryRef.current = null;
        };
      }
      return () => {
        const e = entryRef.current ?? entry;
        if (!e) return;
        e.refCount--;
        e.onConnected = NOOP;
        e.onMessage = NOOP;
        entryRef.current = null;
      };
    }

    if (entry && needNewSocket) {
      entry.socket.close();
      sharedByUrl.delete(url);
      entry = null;
    }

    let socket: WebSocket;
    try {
      socket = new WebSocket(url);
    } catch (err) {
      setIsConnecting(false);
      if (import.meta.env?.DEV) console.debug('WebSocket connection error, retrying…', err);
      reconnectTimerRef.current = setTimeout(() => setReconnectTrigger((t) => t + 1), 3000);
      return () => {
        if (reconnectTimerRef.current) {
          clearTimeout(reconnectTimerRef.current);
          reconnectTimerRef.current = null;
        }
      };
    }

    entry = {
      socket,
      refCount: 1,
      onConnected: (connected) => setIsConnected(connected),
      onMessage: (s, p) => {
        stateRef.current = s;
        setState(s);
        setPayload(p ?? null);
      },
      state: 0,
      payload: null,
    };
    sharedByUrl.set(url, entry);
    entryRef.current = entry;

    socket.onopen = () => {
      entry!.onConnected(true);
      if (import.meta.env?.DEV) console.debug('CLARA WebSocket connected');
    };

    socket.onmessage = (event) => {
      try {
        const data: WSMessage = JSON.parse(event.data);
        if (typeof data.state !== 'number') return;
        const next = data.state;
        const current = entry!.state;
        if (next === 0 && current > 0) return;
        if (next === 4 && current === 5) return;
        entry!.state = next;
        entry!.payload = data.payload ?? null;
        entry!.onMessage(next, entry!.payload);
      } catch (err) {
        console.error('Failed to parse WS message:', err);
      }
    };

    socket.onclose = () => {
      sharedByUrl.delete(url);
      // Only notify when someone is still subscribed (avoids stale close from pre-reuse socket)
      if (entry!.refCount > 0) {
        setIsConnecting(false);
        entry!.onConnected(false);
        // Mark as reconnecting so banner stays hidden during the 3s retry delay
        setIsConnecting(true);
      }
      if (import.meta.env?.DEV) {
        console.warn('CLARA WebSocket disconnected at', url, '— Retrying in 3s. Ensure backend is running; if you changed frontend/.env.local, restart npm run dev.');
      }
      reconnectTimerRef.current = setTimeout(() => {
        reconnectTimerRef.current = null;
        setReconnectTrigger((t) => t + 1);
      }, 3000);
    };

    socket.onerror = () => {};

    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      const e = entry!;
      e.refCount--;
      e.onConnected = NOOP;
      e.onMessage = NOOP;
      entryRef.current = null;
    };
  }, [url, reconnectTrigger]);

  const sendMessage = useCallback((msg: any): boolean => {
    const entry = entryRef.current ?? sharedByUrl.get(url);
    if (entry?.socket?.readyState === WebSocket.OPEN) {
      entry.socket.send(JSON.stringify(msg));
      return true;
    }
    return false;
  }, [url]);

  const setManualState = useCallback((newState: number, newPayload?: any) => {
    stateRef.current = newState;
    setState(newState);
    if (newPayload !== undefined) setPayload(newPayload);
  }, []);

  const retryConnect = useCallback(() => {
    const entry = sharedByUrl.get(url);
    if (entry?.socket) {
      entry.socket.close();
      sharedByUrl.delete(url);
    }
    setReconnectTrigger((t) => t + 1);
  }, [url]);

  return {
    state,
    payload,
    isConnected,
    isConnecting,
    hasAttemptedConnect,
    sendMessage,
    setManualState,
    retryConnect,
  };
}
