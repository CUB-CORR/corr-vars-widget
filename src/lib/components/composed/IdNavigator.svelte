<script lang="ts">
	import ChevronLeftIcon from '@lucide/svelte/icons/chevron-left';
	import ChevronRightIcon from '@lucide/svelte/icons/chevron-right';
	import * as ButtonGroup from '$lib/components/ui/button-group/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import IdCombobox from './IdCombobox.svelte';

	type Id = string | number;

	let {
		value = $bindable(null),
		search,
		neighbor,
		onSelect,
		label = 'id',
		portalTarget = undefined
	}: {
		value?: Id | null;
		search: (query: string) => Promise<Id[]>;
		// Previous (dir -1) / next (dir +1) id in sorted order, or null at an edge.
		neighbor: (id: Id, dir: -1 | 1) => Promise<Id | null>;
		onSelect?: (id: Id) => void;
		label?: string;
		portalTarget?: HTMLElement;
	} = $props();

	let prevId = $state<Id | null>(null);
	let nextId = $state<Id | null>(null);

	// Refresh the neighbours whenever the selection changes, so the arrows can be
	// disabled at the first / last id. A token guards against races.
	let token = 0;
	$effect(() => {
		const id = value;
		const mine = ++token;
		if (id == null) {
			prevId = nextId = null;
			return;
		}
		Promise.all([neighbor(id, -1), neighbor(id, 1)]).then(([p, n]) => {
			if (mine === token) {
				prevId = p;
				nextId = n;
			}
		});
	});

	function step(target: Id | null): void {
		if (target == null) return;
		value = target;
		onSelect?.(target);
	}
</script>

<ButtonGroup.Root>
	<Button
		variant="outline"
		size="icon-sm"
		disabled={prevId == null}
		onclick={() => step(prevId)}
		aria-label="Previous {label}"
	>
		<ChevronLeftIcon />
	</Button>
	<IdCombobox
		bind:value
		{search}
		{onSelect}
		{label}
		{portalTarget}
		size="sm"
		placeholder="Select {label}…"
	/>
	<Button
		variant="outline"
		size="icon-sm"
		disabled={nextId == null}
		onclick={() => step(nextId)}
		aria-label="Next {label}"
	>
		<ChevronRightIcon />
	</Button>
</ButtonGroup.Root>
