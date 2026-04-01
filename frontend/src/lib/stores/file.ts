// ============================================
// FILE STORE - Shared file attachment state
// ============================================

import { writable, derived, get } from 'svelte/store';

export interface AttachedFile {
  file: File;
  content: string;
  preview: string;
  isImage: boolean;
}

function createFileStore() {
  const attachedFile = writable<AttachedFile | null>(null);
  const error = writable<string>('');

  const store = derived(
    [attachedFile, error],
    ([$attachedFile, $error]) => ({
      attachedFile: $attachedFile,
      error: $error,
      hasFile: $attachedFile !== null,
    })
  );

  return {
    store,
    actions: {
      setFile(file: File, content: string, preview: string, isImage: boolean) {
        attachedFile.set({ file, content, preview, isImage });
        error.set('');
      },

      setError(msg: string) {
        error.set(msg);
        attachedFile.set(null);
      },

      clear() {
        attachedFile.set(null);
        error.set('');
      },

      getFileData() {
        const file = get(attachedFile);
        if (!file) return null;
        return {
          content: file.content,
          name: file.file.name,
          type: file.file.type,
          isImage: file.isImage,
        };
      },
    },
  };
}

const { store, actions } = createFileStore();
export const fileStore = store;
export const fileActions = actions;
