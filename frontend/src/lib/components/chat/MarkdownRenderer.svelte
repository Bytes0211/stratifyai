<script lang="ts">
  import { marked } from 'marked';
  import hljs from 'highlight.js';
  import DOMPurify from 'isomorphic-dompurify';
  
  export let content: string;
  
  // Configure marked for security and syntax highlighting
  const renderer = new marked.Renderer();
  
  renderer.code = ({ text, lang }) => {
    const language = lang && hljs.getLanguage(lang) ? lang : 'plaintext';
    const highlighted = hljs.highlight(text, { language }).value;
    return `<pre><code class="hljs language-${language}">${highlighted}</code></pre>`;
  };
  
  marked.setOptions({
    renderer,
    breaks: true,
    gfm: true,
  });
  
  // Sanitize HTML to prevent XSS attacks
  $: html = DOMPurify.sanitize(marked.parse(content) as string, {
    ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'code', 'pre', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
                   'ul', 'ol', 'li', 'blockquote', 'a', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'hr', 'span'],
    ALLOWED_ATTR: ['href', 'class', 'target', 'rel'],
    ALLOW_DATA_ATTR: false,
  });
</script>

<div class="markdown-content">
  {@html html}
</div>

<style lang="scss">
  @use '../../styles/tokens' as *;
  @use '../../styles/mixins' as *;
  
  .markdown-content {
    line-height: $leading-relaxed;
    
    :global(p) {
      margin: 0 0 $space-3 0;
      
      &:last-child {
        margin-bottom: 0;
      }
    }
    
    :global(h1),
    :global(h2),
    :global(h3),
    :global(h4) {
      margin: $space-4 0 $space-2 0;
      color: var(--text-primary);
      
      &:first-child {
        margin-top: 0;
      }
    }
    
    :global(h1) { font-size: $text-xl; }
    :global(h2) { font-size: $text-lg; }
    :global(h3) { font-size: $text-base; }
    
    :global(pre) {
      margin: $space-3 0;
      padding: $space-3;
      background: var(--code-bg);
      border-radius: $radius-lg;
      overflow-x: auto;
      @include custom-scrollbar;
    }
    
    :global(code) {
      font-family: $font-mono;
      font-size: 0.9em;
    }
    
    :global(:not(pre) > code) {
      padding: 2px $space-1;
      background: var(--bg-elevated);
      border-radius: $radius-sm;
    }
    
    :global(ul),
    :global(ol) {
      margin: $space-2 0;
      padding-left: $space-6;
    }
    
    :global(ul) { list-style-type: disc; }
    :global(ol) { list-style-type: decimal; }
    
    :global(li) {
      margin: $space-1 0;
    }
    
    :global(blockquote) {
      margin: $space-3 0;
      padding-left: $space-4;
      border-left: 3px solid var(--accent);
      color: var(--text-secondary);
    }
    
    :global(a) {
      color: var(--accent);
      text-decoration: underline;
      
      &:hover {
        color: var(--accent-hover);
      }
    }
    
    :global(table) {
      width: 100%;
      margin: $space-3 0;
      border-collapse: collapse;
    }
    
    :global(th),
    :global(td) {
      padding: $space-2;
      border: 1px solid var(--bg-elevated);
      text-align: left;
    }
    
    :global(th) {
      background: var(--bg-elevated);
      font-weight: $font-semibold;
    }
    
    :global(hr) {
      margin: $space-4 0;
      border: none;
      border-top: 1px solid var(--bg-elevated);
    }
    
    // Syntax highlighting (dark theme)
    :global(.hljs) {
      color: var(--code-text);
    }
    
    :global(.hljs-comment),
    :global(.hljs-quote) {
      color: var(--code-comment);
    }
    
    :global(.hljs-keyword),
    :global(.hljs-selector-tag) {
      color: var(--code-keyword);
    }
    
    :global(.hljs-string),
    :global(.hljs-addition) {
      color: var(--code-string);
    }
    
    :global(.hljs-number),
    :global(.hljs-literal) {
      color: var(--code-number);
    }
    
    :global(.hljs-title),
    :global(.hljs-function) {
      color: var(--code-function);
    }
  }
</style>
