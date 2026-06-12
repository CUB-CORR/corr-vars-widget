<script module>
	export type Model = {
		_jsons: Record<string, string>;
	};
</script>

<script lang="ts">
	import type { AnyModel } from '@anywidget/types';
	import './app.css';

	import * as Accordion from '$lib/components/ui/accordion/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import ScrollArea from '$lib/components/ui/scroll-area/scroll-area.svelte';
	import JsonView from '$lib/components/composed/json/json-view.svelte';
	import Search from '$lib/components/composed/search/search.svelte';
	import ChevronsDownUp from '@lucide/svelte/icons/chevrons-down-up';

	let {
		model,
		bindings
	}: {
		model?: AnyModel<Model>;
		bindings?: Model;
	} = $props();

	const items = $derived(Object.entries(bindings?._jsons ?? {}));

	function parseJSON(json: string): any {
		try {
			return JSON.parse(json);
		} catch {
			return null;
		}
	}

	const parsedItems = $derived(items.map(([key, json]) => [key, parseJSON(json)] as const));

	const allKeys = $derived(
		Array.from(
			new Set(
				parsedItems.flatMap(([, obj]) =>
					obj && typeof obj === 'object' && !Array.isArray(obj) ? Object.keys(obj) : []
				)
			)
		)
	);

	let filteredKeys = $state<string[] | null>(null);

	function filteredJSON(obj: any): any {
		if (filteredKeys === null || !obj || typeof obj !== 'object' || Array.isArray(obj)) return obj;
		const result: any = {};
		for (const key of filteredKeys) {
			if (key in obj) result[key] = obj[key];
		}
		return result;
	}

	let opened: string[] = $state([]);
	function openClose() {
		if (opened.length) {
			opened = [];
		} else {
			opened = items.map(([key]) => key);
		}
	}
</script>

<div class="w-full p-2">
	<Card.Root>
		<Card.Header>
			<Card.Title>JSON Dict</Card.Title>
			<Card.Description>Collection of JSON entries</Card.Description>
			<Card.Action>
				<Button variant="ghost" size="icon" onclick={openClose}
					><ChevronsDownUp /><span class="sr-only">Open</span></Button
				>
			</Card.Action>
		</Card.Header>
		<Card.Content>
			<div class="flex flex-col gap-4">
				<Search
					terms={allKeys}
					onfiltered={(value) => {
						filteredKeys = value;
					}}
				/>
				<Accordion.Root type="multiple" class="w-full" bind:value={opened}>
					{#each parsedItems as [key, obj] (key)}
						{@const filtered = filteredJSON(obj)}
						{@const hasMatch = filteredKeys === null || Object.keys(filtered ?? {}).length > 0}
						<Accordion.Item value={key}>
							<Accordion.Trigger class="group hover:no-underline">
								<span class="group-hover:underline">{key}</span>
							</Accordion.Trigger>
							<Accordion.Content class="flex flex-col gap-4 text-balance">
								<ScrollArea class="h-64">
									{#if hasMatch}
										<JsonView json={filtered} depth={1} />
									{:else}
										<div class="grid h-full place-items-center text-2xl">No matching keys found.</div>
									{/if}
								</ScrollArea>
							</Accordion.Content>
						</Accordion.Item>
					{/each}
				</Accordion.Root>
			</div>
		</Card.Content>
		<Card.Footer class="justify-end py-2">
			<Badge variant="default"
				>{items.length}
				{items.length === 1 ? 'entry' : 'entries'}</Badge
			>
		</Card.Footer>
	</Card.Root>
</div>
