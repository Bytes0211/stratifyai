// ============================================
// WEBSOCKET CLIENT - Streaming chat
// ============================================

import type { ChatRequest, StreamMessage } from './types';

export interface StreamCallbacks {
  onContent: (content: string) => void;
  onComplete: (message: StreamMessage) => void;
  onError: (error: string) => void;
}

export function createChatStream(
  request: ChatRequest,
  callbacks: StreamCallbacks
): { close: () => void } {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/api/chat/stream`;
  
  const ws = new WebSocket(wsUrl);
  let isClosedIntentionally = false;
  
  ws.onopen = () => {
    // Send the chat request once connected
    ws.send(JSON.stringify(request));
  };
  
  ws.onmessage = (event) => {
    try {
      const data: StreamMessage = JSON.parse(event.data);
      
      if (data.error) {
        callbacks.onError(data.detail ? `${data.error}: ${data.detail}` : data.error);
        return;
      }
      
      if (data.content) {
        callbacks.onContent(data.content);
      }
      
      if (data.done) {
        callbacks.onComplete(data);
      }
    } catch (err) {
      callbacks.onError('Failed to parse stream message');
    }
  };
  
  ws.onerror = () => {
    if (!isClosedIntentionally) {
      callbacks.onError('WebSocket connection error');
    }
  };
  
  ws.onclose = (event) => {
    if (!isClosedIntentionally && !event.wasClean) {
      callbacks.onError('Connection closed unexpectedly');
    }
  };
  
  return {
    close: () => {
      isClosedIntentionally = true;
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
    },
  };
}
