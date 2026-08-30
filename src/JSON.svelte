<script module>
	import type { Themed } from '$lib/theme.svelte';

	export type Model = Themed & {
		json: string;
	};
</script>

<script lang="ts">
	import type { AnyModel } from '@anywidget/types';

	import * as Card from '$lib/components/ui/card/index.js';
	import WidgetRoot from '$lib/components/composed/WidgetRoot.svelte';
	import ScrollArea from '$lib/components/ui/scroll-area/scroll-area.svelte';

	import JsonView from '$lib/components/composed/json/json-view.svelte';
	import Search from '$lib/components/composed/search/search.svelte';

	let {
		model,
		bindings
	}: {
		model?: AnyModel<Model>;
		bindings?: Model;
	} = $props();

	function parseJSON(json: string): any {
		try {
			return JSON.parse(json);
		} catch (e) {
			console.error('Invalid JSON:', e);
			return null;
		}
	}

	const parsedJSON = $derived(parseJSON(bindings?.json || '{}'));

	function parseKeys(value: any): string[] {
		if (value && typeof value === 'object') {
			return Object.keys(value);
		}
		return [];
	}

	const parsedKeys = $derived(parseKeys(parsedJSON));

	let filteredKeys = $state<string[] | null>(null);
	const filteredJSON = $derived.by(() => {
		if (!filteredKeys) return parsedJSON;
		if (parsedJSON && typeof parsedJSON === 'object') {
			const result: any = {};
			for (const key of filteredKeys) {
				if (key in parsedJSON) {
					result[key] = parsedJSON[key];
				}
			}
			return result;
		}
		return parsedJSON;
	});
</script>

<WidgetRoot {model} class="w-full p-2">
	<Card.Root>
		<Card.Header>
			<Card.Title>JSON Viewer</Card.Title>
		</Card.Header>
		<Card.Content>
			<div class="flex flex-col gap-4">
				<Search
					terms={parsedKeys}
					onfiltered={(value) => {
						filteredKeys = value;
					}}
				/>
				<ScrollArea class="h-96">
					{#if filteredKeys === null || filteredKeys.length > 0}
						<JsonView json={filteredJSON} depth={1} />
					{:else}
						<div class="grid h-full place-items-center text-2xl">No matching keys found.</div>
					{/if}
				</ScrollArea>
			</div>
		</Card.Content>
	</Card.Root>
</WidgetRoot>
