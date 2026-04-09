<script lang="ts">
	import type { Attachment } from 'svelte/attachments';
	import { DataTable } from '@manzt/quak';
	import { Query } from '@uwdata/mosaic-sql';

	import * as Accordion from '$lib/components/ui/accordion/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import ChevronsDownUp from '@lucide/svelte/icons/chevrons-down-up';
	import './app.css';

	let { tables }: { tables: Record<string, DataTable> } = $props();
	let tableEntries = $derived(Object.entries(tables));

	// let tableShapes = $derived(
	// 	await Promise.all(
	// 		tableEntries.map(([name, table]) =>
	// 			table.requestQuery(Query.select('SELECT COUNT(*)').from(name))
	// 		)
	// 	)
	// );

	function appendTable(table: DataTable): Attachment<HTMLElement> {
		return (node: HTMLElement) => {
			node.appendChild(table.node());
		};
	}

	let opened: string[] = $state([]);
	function openClose() {
		if (opened.length) {
			opened = [];
		} else {
			opened = tableEntries.map(([name]) => name);
		}
	}
</script>

<Card.Root class="mx-2 my-4 max-w-xl bg-background font-sans text-foreground">
	<Card.Header>
		<Card.Title>ObsmDict</Card.Title>
		<Card.Description>Dynamic timeseries data</Card.Description>
		<Card.Action>
			<Button variant="ghost" size="icon" onclick={openClose}
				><ChevronsDownUp /><span class="sr-only">Open</span></Button
			>
		</Card.Action>
	</Card.Header>
	<Card.Content>
		<Accordion.Root type="multiple" class="w-full" bind:value={opened}>
			{#each tableEntries as [name, table] (name)}
				<Accordion.Item value={name}>
					<Accordion.Trigger>{name}</Accordion.Trigger>
					<Accordion.Content class="flex flex-col gap-4 text-balance" {@attach appendTable(table)}
					></Accordion.Content>
				</Accordion.Item>
			{/each}
		</Accordion.Root>
	</Card.Content>
	<Card.Footer class="justify-end py-2">
		<Badge variant="default">{tableEntries.length} table{tableEntries.length > 1 ? 's' : ''}</Badge>
	</Card.Footer>
</Card.Root>
