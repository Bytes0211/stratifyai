<script lang="ts">
  import { onMount } from 'svelte';
  import AppShell from '$lib/components/layout/AppShell.svelte';
  import { themeActions } from '$lib/stores/theme';
  
  // Initialize theme on mount
  onMount(() => {
    themeActions.init();
  });
</script>

<AppShell />
