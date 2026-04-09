<script lang="ts">
	import { Button } from '$lib/components/ui/button/index';
	import { PlusIcon } from '@lucide/svelte';
	import './app.css';

	let { bindings }: { bindings: { value: number } } = $props();
</script>

<Button onclick={() => bindings.value++} class="my-2">
	<PlusIcon />
	Count is {bindings.value}
</Button>
