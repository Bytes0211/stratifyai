<script lang="ts">
  import { get } from 'svelte/store';
  import { Send, Square, Trash2, Paperclip, X, File, Image } from 'lucide-svelte';
  import Button from '../shared/Button.svelte';
  import { chatStore, chatActions } from '$lib/stores/chat';
  import { configStore } from '$lib/stores/config';
  import { costActions } from '$lib/stores/cost';
  import { fileStore, fileActions } from '$lib/stores/file';
  import { createChatStream } from '$lib/api/websocket';
  import { chat as chatApi } from '$lib/api/client';
  import type { ChatRequest } from '$lib/api/types';
  
  let inputValue = '';
  let textareaRef: HTMLTextAreaElement;
  let fileInputRef: HTMLInputElement;
  let streamController: { close: () => void } | null = null;
  
  // File attachment state
  let attachedFile: File | null = null;
  let fileContent = '';
  let fileError = '';
  
  // Accepted file types based on vision support
  $: acceptedTypes = (() => {
    const base = '.txt,.md,.json,.csv,.log,.py,.js,.ts,.jsx,.tsx,.html,.css,.scss,.yaml,.yml,.xml,.sql,.sh,.bash';
    if ($configStore.supportsVision) {
      return `${base},.jpg,.jpeg,.png,.gif,.webp`;
    }
    return base;
  })();
  
  function handleFileSelect(e: Event) {
    const target = e.target as HTMLInputElement;
    const file = target.files?.[0];
    if (!file) return;
    
    fileError = '';
    
    // Check file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      fileError = 'File size must be less than 10MB';
      return;
    }
    
    const config = get(configStore);
    
    // Handle image files
    if (file.type.startsWith('image/')) {
      if (!config.supportsVision) {
        fileError = 'Selected model does not support images';
        return;
      }
      
      const reader = new FileReader();
      reader.onload = (e) => {
        fileContent = e.target?.result as string;
        attachedFile = file;
      };
      reader.readAsDataURL(file);
    } else {
      // Handle text files
      const reader = new FileReader();
      reader.onload = (e) => {
        fileContent = e.target?.result as string;
        attachedFile = file;
      };
      reader.readAsText(file);
    }
  }
  
  function clearAttachment() {
    attachedFile = null;
    fileContent = '';
    fileError = '';
    if (fileInputRef) {
      fileInputRef.value = '';
    }
  }
  
  function triggerFileInput() {
    fileInputRef?.click();
  }
  
  async function handleSubmit() {
    const content = inputValue.trim();
    const state = get(chatStore);
    const config = get(configStore);
    const sharedFile = fileActions.getFileData();
    
    // Use shared file store if no local attachment
    const effectiveFile = attachedFile ? { name: attachedFile.name, type: attachedFile.type, content: fileContent, isImage: attachedFile.type.startsWith('image/') } 
      : sharedFile ? { name: sharedFile.name, type: sharedFile.type, content: sharedFile.content, isImage: sharedFile.isImage }
      : null;
    
    // Check if we have either content or an attachment
    if ((!content && !effectiveFile) || state.isStreaming) return;
    
    if (!config.model) {
      chatActions.addErrorMessage('Please select a model first.');
      return;
    }
    
    // Add user message (if there's text content)
    if (content) {
      chatActions.addUserMessage(content);
      inputValue = '';
    } else if (effectiveFile) {
      // Add a placeholder message showing the attachment
      chatActions.addUserMessage(`[Attached: ${effectiveFile.name}]`);
    }
    
    // Resize textarea
    if (textareaRef) {
      textareaRef.style.height = 'auto';
    }
    
    // Build request
    const messages = chatActions.getApiMessages();
    const request: ChatRequest = {
      provider: config.provider,
      model: config.model,
      messages,
      temperature: config.effectiveTemperature,
      max_tokens: config.maxTokens,
      stream: config.stream,
      chunked: config.chunked,
      chunk_size: config.chunkSize,
    };
    
    // Handle file attachment (local or from shared store)
    const hasAttachment = effectiveFile !== null;
    if (hasAttachment && effectiveFile) {
      if (effectiveFile.isImage) {
        // For images: format as [IMAGE:mime_type]\nbase64_data in message content
        // Extract base64 data from data URL (format: data:image/jpeg;base64,<data>)
        
        // Validate data URL format (supports image/jpeg, image/png, image/gif, image/webp, etc.)
        const dataUrlPattern = /^data:(image\/[a-z0-9+.-]+);base64,([A-Za-z0-9+/=]+)$/;
        const match = effectiveFile.content.match(dataUrlPattern);
        
        if (!match) {
          chatActions.addErrorMessage('Invalid image format. Expected data URL with base64 encoding.');
          if (hasAttachment) {
            clearAttachment();
            fileActions.clear();
          }
          return;
        }
        
        const mimeType = match[1];  // e.g., 'image/jpeg'
        const base64Data = match[2];  // Base64 encoded data
        
        // Format for vision models: [IMAGE:mime_type]\nbase64_data
        const imageContent = `[IMAGE:${mimeType}]\n${base64Data}`;
        
        // Add image to the last message content
        if (messages.length > 0 && messages[messages.length - 1].role === 'user') {
          const lastMsg = messages[messages.length - 1];
          lastMsg.content = lastMsg.content ? `${lastMsg.content}\n\n${imageContent}` : imageContent;
        }
      } else {
        // For text files: use file_content and file_name parameters for chunking support
        request.file_content = effectiveFile.content;
        request.file_name = effectiveFile.name;
      }
    }
    
    if (config.stream) {
      // Streaming mode
      chatActions.startStreaming();
      
      streamController = createChatStream(request, {
        onContent: (chunk) => {
          chatActions.appendStreamingContent(chunk);
        },
        onComplete: (usage) => {
          chatActions.completeStreaming(usage);
          if (usage) {
            costActions.addEntry(
              config.provider,
              config.model,
              usage.cost_usd,
              usage.total_tokens
            );
          }
          streamController = null;
          // Clear attachment after streaming completes
          if (hasAttachment) {
            clearAttachment();
            fileActions.clear(); // Clear shared store too
          }
        },
        onError: (error) => {
          chatActions.cancelStreaming();
          chatActions.addErrorMessage(error);
          streamController = null;
          // Clear attachment on error too
          if (hasAttachment) {
            clearAttachment();
            fileActions.clear(); // Clear shared store too
          }
        },
      });
    } else {
      // Non-streaming mode
      try {
        const response = await chatApi(request);
        // Merge cost_usd into usage for per-message display
        const usageWithCost = { ...response.usage, cost_usd: response.cost_usd };
        chatActions.addAssistantMessage(response.content, usageWithCost);
        costActions.addEntry(
          response.provider,
          response.model,
          response.cost_usd,
          response.usage.total_tokens
        );
        // Clear attachment after successful response
        if (hasAttachment) {
          clearAttachment();
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : 'An error occurred';
        chatActions.addErrorMessage(message);
        // Clear attachment on error too
        if (hasAttachment) {
          clearAttachment();
        }
      }
    }
  }
  
  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }
  
  function handleInput() {
    // Auto-resize textarea
    if (textareaRef) {
      textareaRef.style.height = 'auto';
      textareaRef.style.height = `${Math.min(textareaRef.scrollHeight, 200)}px`;
    }
  }
  
  function stopStreaming() {
    if (streamController) {
      streamController.close();
      streamController = null;
    }
    chatActions.cancelStreaming();
  }
  
  function clearChat() {
    chatActions.clear();
    clearAttachment();
  }
</script>

<div class="chat-input-container">
  <!-- Hidden file input -->
  <input
    type="file"
    bind:this={fileInputRef}
    accept={acceptedTypes}
    on:change={handleFileSelect}
    hidden
  />
  
  <!-- Attached file preview -->
  {#if attachedFile}
    <div class="attachment-preview">
      <div class="attachment-info">
        {#if attachedFile.type.startsWith('image/')}
          <Image size={14} />
        {:else}
          <File size={14} />
        {/if}
        <span class="attachment-name">{attachedFile.name}</span>
        <span class="attachment-size">({(attachedFile.size / 1024).toFixed(1)} KB)</span>
      </div>
      <button class="remove-attachment" on:click={clearAttachment} aria-label="Remove attachment">
        <X size={14} />
      </button>
    </div>
  {/if}
  
  {#if fileError}
    <div class="file-error">{fileError}</div>
  {/if}
  <div class="input-wrapper">
    <button 
      class="attach-btn" 
      on:click={triggerFileInput}
      disabled={$chatStore.isStreaming}
      aria-label="Attach file"
      title={$configStore.supportsVision ? 'Attach file or image' : 'Attach file'}
    >
      <Paperclip size={18} />
    </button>
    
    <textarea
      bind:this={textareaRef}
      bind:value={inputValue}
      on:keydown={handleKeydown}
      on:input={handleInput}
      placeholder="Type your message... (Shift+Enter for new line)"
      rows="1"
      disabled={$chatStore.isStreaming}
    ></textarea>
    
    <div class="input-actions">
      {#if $chatStore.isStreaming}
        <Button variant="danger" size="sm" on:click={stopStreaming}>
          <Square size={16} />
          Stop
        </Button>
      {:else}
        <Button 
          variant="primary" 
          on:click={handleSubmit}
          disabled={(!inputValue.trim() && !attachedFile) || !$configStore.model}
        >
          <Send size={16} />
          Send
        </Button>
      {/if}
    </div>
  </div>
  
  {#if $chatStore.hasMessages}
    <div class="chat-actions">
      <button class="clear-btn" on:click={clearChat} aria-label="Clear chat">
        <Trash2 size={14} />
        Clear chat
      </button>
    </div>
  {/if}
</div>

<style lang="scss">
  @use '../../styles/tokens' as *;
  @use '../../styles/mixins' as *;
  
  .chat-input-container {
    display: flex;
    flex-direction: column;
    gap: $space-2;
  }
  
  .attachment-preview {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: $space-2 $space-3;
    background: var(--bg-elevated);
    border-radius: $radius-lg;
    font-size: $text-xs;
  }
  
  .attachment-info {
    display: flex;
    align-items: center;
    gap: $space-2;
    color: var(--text-secondary);
    min-width: 0;
  }
  
  .attachment-name {
    color: var(--text-primary);
    font-weight: $font-medium;
    @include truncate;
  }
  
  .attachment-size {
    color: var(--text-muted);
    flex-shrink: 0;
  }
  
  .remove-attachment {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    border-radius: $radius-sm;
    color: var(--text-muted);
    flex-shrink: 0;
    
    &:hover {
      background: rgba($error, 0.1);
      color: $error;
    }
  }
  
  .file-error {
    font-size: $text-xs;
    color: $error;
    padding: $space-2;
    background: rgba($error, 0.1);
    border-radius: $radius-md;
  }
  
  .input-wrapper {
    display: flex;
    align-items: flex-end;
    gap: $space-2;
    padding: $space-3;
    background: var(--bg-surface);
    border: 1px solid var(--bg-elevated);
    border-radius: $radius-xl;
    transition: border-color $transition-fast;
    
    &:focus-within {
      border-color: var(--accent);
    }
  }
  
  .attach-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: $radius-lg;
    color: var(--text-muted);
    transition: all $transition-fast;
    flex-shrink: 0;
    
    &:hover:not(:disabled) {
      background: var(--bg-elevated);
      color: var(--text-primary);
    }
    
    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
  }
  
  textarea {
    flex: 1;
    resize: none;
    border: none;
    background: transparent;
    color: var(--text-primary);
    font-size: $text-sm;
    line-height: $leading-normal;
    min-height: 24px;
    max-height: 200px;
    @include custom-scrollbar;
    
    &::placeholder {
      color: var(--text-muted);
    }
    
    &:focus {
      outline: none;
    }
    
    &:disabled {
      opacity: 0.5;
    }
  }
  
  .input-actions {
    display: flex;
    align-items: flex-end;
  }
  
  .chat-actions {
    display: flex;
    justify-content: center;
  }
  
  .clear-btn {
    display: flex;
    align-items: center;
    gap: $space-1;
    font-size: $text-xs;
    color: var(--text-muted);
    padding: $space-1 $space-2;
    border-radius: $radius-md;
    transition: all $transition-fast;
    
    &:hover {
      color: var(--error);
      background: rgba($error, 0.1);
    }
  }
</style>
