<script lang="ts">
  import { get } from 'svelte/store';
  import { Upload, File, X, Image } from 'lucide-svelte';
  import { configStore } from '$lib/stores/config';
  import { fileStore, fileActions } from '$lib/stores/file';
  import Button from '../shared/Button.svelte';
  
  let fileInput: HTMLInputElement;
  
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
    
    // Check file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      fileActions.setError('File size must be less than 10MB');
      return;
    }
    
    const config = get(configStore);
    const isImage = file.type.startsWith('image/');
    
    // Handle image files
    if (isImage) {
      if (!config.supportsVision) {
        fileActions.setError('Selected model does not support vision');
        return;
      }
      
      const reader = new FileReader();
      reader.onload = (e) => {
        const content = e.target?.result as string;
        fileActions.setFile(file, content, content, true);
      };
      reader.readAsDataURL(file);
    } else {
      // Handle text files
      const reader = new FileReader();
      reader.onload = (e) => {
        const text = e.target?.result as string;
        const preview = text.slice(0, 500) + (text.length > 500 ? '...' : '');
        fileActions.setFile(file, text, preview, false);
      };
      reader.readAsText(file);
    }
  }
  
  function clearFile() {
    fileActions.clear();
    if (fileInput) {
      fileInput.value = '';
    }
  }
  
  function triggerFileInput() {
    fileInput?.click();
  }
</script>

<div class="file-upload">
  <input
    type="file"
    bind:this={fileInput}
    accept={acceptedTypes}
    on:change={handleFileSelect}
    hidden
  />
  
  {#if $fileStore.attachedFile}
    <div class="file-selected">
      <div class="file-header">
        {#if $fileStore.attachedFile.isImage}
          <Image size={16} />
        {:else}
          <File size={16} />
        {/if}
        <span class="file-name">{$fileStore.attachedFile.file.name}</span>
        <button class="remove-btn" on:click={clearFile} aria-label="Remove file">
          <X size={14} />
        </button>
      </div>
      
      {#if $fileStore.attachedFile.preview}
        <div class="file-preview">
          {#if $fileStore.attachedFile.isImage}
            <img src={$fileStore.attachedFile.preview} alt="Preview" />
          {:else}
            <pre>{$fileStore.attachedFile.preview}</pre>
          {/if}
        </div>
      {/if}
      
      <div class="file-meta">
        <span>{($fileStore.attachedFile.file.size / 1024).toFixed(1)} KB</span>
        {#if $configStore.chunked}
          <span class="chunk-hint">Will be chunked</span>
        {/if}
      </div>
    </div>
  {:else}
    <button class="upload-area" on:click={triggerFileInput}>
      <Upload size={24} />
      <span class="upload-text">Click to upload a file</span>
      <span class="upload-hint">
        {#if $configStore.supportsVision}
          Text files, code, or images
        {:else}
          Text files and code only
        {/if}
      </span>
    </button>
  {/if}
  
  {#if $fileStore.error}
    <div class="error-message">{$fileStore.error}</div>
  {/if}
</div>

<style lang="scss">
  @use '../../styles/tokens' as *;
  @use '../../styles/mixins' as *;
  
  .file-upload {
    display: flex;
    flex-direction: column;
    gap: $space-3;
  }
  
  .upload-area {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: $space-2;
    padding: $space-6;
    border: 2px dashed var(--bg-hover);
    border-radius: $radius-xl;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all $transition-fast;
    @include focus-visible-ring;
    
    &:hover {
      border-color: var(--accent);
      background: rgba($accent-primary, 0.05);
    }
  }
  
  .upload-text {
    font-size: $text-sm;
    font-weight: $font-medium;
  }
  
  .upload-hint {
    font-size: $text-xs;
    color: var(--text-muted);
  }
  
  .file-selected {
    display: flex;
    flex-direction: column;
    gap: $space-2;
    padding: $space-3;
    background: var(--bg-elevated);
    border-radius: $radius-lg;
    border: 1px solid var(--bg-hover);
  }
  
  .file-header {
    display: flex;
    align-items: center;
    gap: $space-2;
    color: var(--text-secondary);
  }
  
  .file-name {
    flex: 1;
    font-size: $text-sm;
    font-weight: $font-medium;
    color: var(--text-primary);
    @include truncate;
  }
  
  .remove-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    border-radius: $radius-md;
    color: var(--text-muted);
    transition: all $transition-fast;
    
    &:hover {
      background: rgba($error, 0.1);
      color: $error;
    }
  }
  
  .file-preview {
    max-height: 150px;
    overflow: hidden;
    border-radius: $radius-md;
    
    img {
      width: 100%;
      height: auto;
      object-fit: contain;
    }
    
    pre {
      margin: 0;
      padding: $space-2;
      font-size: $text-xs;
      background: var(--bg-surface);
      border-radius: $radius-md;
      overflow: hidden;
      white-space: pre-wrap;
      word-break: break-all;
    }
  }
  
  .file-meta {
    display: flex;
    justify-content: space-between;
    font-size: $text-xs;
    color: var(--text-muted);
  }
  
  .chunk-hint {
    color: var(--accent);
  }
  
  .error-message {
    font-size: $text-sm;
    color: $error;
    padding: $space-2;
    background: rgba($error, 0.1);
    border-radius: $radius-md;
  }
</style>
