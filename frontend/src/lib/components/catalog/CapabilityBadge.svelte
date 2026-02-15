<script lang="ts">
  import { Eye, Wrench, Brain } from 'lucide-svelte';
  
  export let type: 'vision' | 'tools' | 'reasoning';
  
  const config = {
    vision: { icon: Eye, label: 'Vision', color: 'vision' },
    tools: { icon: Wrench, label: 'Tools', color: 'tools' },
    reasoning: { icon: Brain, label: 'Reasoning', color: 'reasoning' },
  };
  
  const { icon: Icon, label, color } = config[type];
</script>

<span class="capability-badge {color}">
  <Icon size={12} />
  {label}
</span>

<style lang="scss">
  @use '../../styles/tokens' as *;
  
  .capability-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: $text-xs;
    font-weight: $font-medium;
    padding: 2px $space-2;
    border-radius: $radius-full;
    
    &.vision {
      background: rgba($success, 0.15);
      color: $success;
    }
    
    &.tools {
      background: rgba($warning, 0.15);
      color: $warning;
    }
    
    &.reasoning {
      background: rgba($info, 0.15);
      color: $info;
    }
  }
</style>
