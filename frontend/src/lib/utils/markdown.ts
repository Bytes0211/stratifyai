// ============================================
// MARKDOWN UTILITIES
// ============================================

import { marked } from 'marked';
import hljs from 'highlight.js';

// Configure marked for security and code highlighting
const renderer = new marked.Renderer();

renderer.code = ({ text, lang }: { text: string; lang?: string }) => {
  const language = lang && hljs.getLanguage(lang) ? lang : 'plaintext';
  const highlighted = hljs.highlight(text, { language }).value;
  return `<pre><code class="hljs language-${language}">${highlighted}</code></pre>`;
};

marked.setOptions({
  renderer,
  breaks: true,
  gfm: true,
});

export function renderMarkdown(content: string): string {
  return marked.parse(content) as string;
}

export { marked, hljs };
