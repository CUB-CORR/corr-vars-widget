<script lang="ts">
	import CheckIcon from '@lucide/svelte/icons/check';
	import ChevronsUpDownIcon from '@lucide/svelte/icons/chevrons-up-down';
	import { tick } from 'svelte';
	import * as Command from '$lib/components/ui/command/index.js';
	import * as Popover from '$lib/components/ui/popover/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { cn } from '$lib/utils.js';

	import type { ButtonSize } from '$lib/components/ui/button/index.js';
	type Id = string | number;

	let {
		value = $bindable(null),
		search,
		onSelect,
		label = 'id',
		placeholder = 'Select…',
		// Size of the trigger button
		size = 'default',
		// Extra classes for the trigger button (e.g. to join a button group).
		class: className = undefined,
		// Portal target — the widget container, so the popover stays inside the
		// (possibly shadow-rooted) widget DOM and keeps its styling.
		portalTarget = undefined
	}: {
		value?: Id | null;
		search: (query: string) => Promise<Id[]>;
		onSelect?: (id: Id) => void;
		label?: string;
		placeholder?: string;
		size?: ButtonSize;
		class?: string;
		portalTarget?: HTMLElement;
	} = $props();

	let open = $state(false);
	let query = $state('');
	let items = $state<Id[]>([]);
	let loading = $state(false);
	let triggerRef = $state<HTMLButtonElement>(null!);

	// Server-side search: bits-ui filtering is disabled (`shouldFilter={false}`)
	// and the list is whatever the last query returned. A token guards against
	// out-of-order responses.
	let token = 0;
	let timer: ReturnType<typeof setTimeout> | undefined;

	async function runSearch(q: string): Promise<void> {
		const mine = ++token;
		loading = true;
		try {
			const res = await search(q);
			if (mine === token) items = res;
		} finally {
			if (mine === token) loading = false;
		}
	}

	$effect(() => {
		const q = query;
		if (!open) return;
		clearTimeout(timer);
		timer = setTimeout(() => runSearch(q), 200);
		return () => clearTimeout(timer);
	});

	function pick(id: Id): void {
		value = id;
		onSelect?.(id);
		open = false;
		tick().then(() => triggerRef?.focus());
	}
</script>

<Popover.Root bind:open>
	<Popover.Trigger bind:ref={triggerRef}>
		{#snippet child({ props })}
			<Button
				variant="outline"
				{size}
				role="combobox"
				aria-expanded={open}
				class={cn('h-7 min-w-30 justify-between gap-1 px-2 font-mono text-xs', className)}
				{...props}
			>
				<span class="truncate">{value ?? placeholder}</span>
				<ChevronsUpDownIcon class="size-3.5 shrink-0 opacity-50" />
			</Button>
		{/snippet}
	</Popover.Trigger>
	<!-- Hardcoded: the popover's top-right corner is anchored to the trigger. -->
	<Popover.Content
		class="w-[16rem] p-0"
		side="bottom"
		align="end"
		avoidCollisions={false}
		portalProps={{ to: portalTarget }}
	>
		<Command.Root shouldFilter={false}>
			<Command.Input placeholder={`Search ${label}…`} bind:value={query} />
			<Command.List>
				{#if loading}
					<Command.Loading class="py-2 text-center text-sm text-muted-foreground">
						Searching…
					</Command.Loading>
				{:else}
					<Command.Empty>No {label} found.</Command.Empty>
				{/if}
				<Command.Group>
					{#each items as id (id)}
						<Command.Item value={String(id)} onSelect={() => pick(id)} class="font-mono">
							<CheckIcon class={cn('me-2 size-4', value !== id && 'text-transparent')} />
							{id}
						</Command.Item>
					{/each}
				</Command.Group>
			</Command.List>
		</Command.Root>
	</Popover.Content>
</Popover.Root>
