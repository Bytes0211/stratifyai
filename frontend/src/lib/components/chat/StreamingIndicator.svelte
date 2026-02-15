<script lang="ts">
  // Simple typing indicator dots
</script>

<div class="streaming-indicator" aria-label="AI is typing">
  <span class="dot"></span>
  <span class="dot"></span>
  <span class="dot"></span>
</div>

<style lang="scss">
  @use '../../styles/tokens' as *;
  
  .streaming-indicator {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: $space-2 0;
    margin-left: 44px; // Align with message content (avatar width + gap)
  }
  
  .dot {
    width: 6px;
    height: 6px;
    background: var(--accent);
    border-radius: 50%;
    animation: bounce 1.4s ease-in-out infinite;
    
    &:nth-child(2) {
      animation-delay: 0.16s;
    }
    
    &:nth-child(3) {
      animation-delay: 0.32s;
    }
  }
  
  @keyframes bounce {
    0%, 60%, 100% {
      transform: translateY(0);
      opacity: 0.4;
    }
    30% {
      transform: translateY(-6px);
      opacity: 1;
    }
  }
</style>
