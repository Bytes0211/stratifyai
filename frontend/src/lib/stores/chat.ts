// ============================================
// CHAT STORE - Messages and streaming state
// ============================================

import { writable, derived, get } from 'svelte/store';
import type { Message, UsageStats } from '$lib/api/types';

export interface ChatMessage extends Message {
  id: string;
  timestamp: Date;
  usage?: UsageStats;
  error?: boolean;
}

function generateId(): string {
  return `msg-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function createChatStore() {
  const messages = writable<ChatMessage[]>([]);
  const isStreaming = writable<boolean>(false);
  const streamingContent = writable<string>('');
  const streamingMessageId = writable<string | null>(null);
  
  const hasMessages = derived(messages, $msgs => $msgs.length > 0);
  
  // Combined store for reactive $chatStore access
  const store = derived(
    [messages, isStreaming, streamingContent, streamingMessageId, hasMessages],
    ([$messages, $isStreaming, $streamingContent, $streamingMessageId, $hasMessages]) => ({
      messages: $messages,
      isStreaming: $isStreaming,
      streamingContent: $streamingContent,
      streamingMessageId: $streamingMessageId,
      hasMessages: $hasMessages,
    })
  );
  
  return {
    store,
    actions: {
      addUserMessage(content: string): string {
        const id = generateId();
        messages.update(msgs => [...msgs, {
          id,
          role: 'user',
          content,
          timestamp: new Date(),
        }]);
        return id;
      },
      
      addSystemMessage(content: string): string {
        const id = generateId();
        messages.update(msgs => [...msgs, {
          id,
          role: 'system',
          content,
          timestamp: new Date(),
        }]);
        return id;
      },
      
      addAssistantMessage(content: string, usage?: UsageStats): string {
        const id = generateId();
        messages.update(msgs => [...msgs, {
          id,
          role: 'assistant',
          content,
          timestamp: new Date(),
          usage,
        }]);
        return id;
      },
      
      addErrorMessage(content: string): string {
        const id = generateId();
        messages.update(msgs => [...msgs, {
          id,
          role: 'assistant',
          content,
          timestamp: new Date(),
          error: true,
        }]);
        return id;
      },
      
      startStreaming(): string {
        const id = generateId();
        isStreaming.set(true);
        streamingContent.set('');
        streamingMessageId.set(id);
        return id;
      },
      
      appendStreamingContent(content: string) {
        streamingContent.update(c => c + content);
      },
      
      completeStreaming(usage?: UsageStats) {
        const id = get(streamingMessageId);
        const content = get(streamingContent);
        if (id) {
          // Save message even if empty (e.g., safety filter, token limit)
          const finalContent = content || '(empty response)';
          messages.update(msgs => [...msgs, {
            id,
            role: 'assistant',
            content: finalContent,
            timestamp: new Date(),
            usage,
          }]);
        }
        isStreaming.set(false);
        streamingContent.set('');
        streamingMessageId.set(null);
      },
      
      cancelStreaming() {
        isStreaming.set(false);
        streamingContent.set('');
        streamingMessageId.set(null);
      },
      
      clear() {
        messages.set([]);
        isStreaming.set(false);
        streamingContent.set('');
        streamingMessageId.set(null);
      },
      
      getApiMessages(): Message[] {
        return get(messages)
          .filter(m => !m.error)
          .map(m => ({
            role: m.role,
            content: m.content,
          }));
      },
    },
  };
}

const { store, actions } = createChatStore();
export const chatStore = store;
export const chatActions = actions;
