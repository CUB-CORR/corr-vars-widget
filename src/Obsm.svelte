<script lang="ts">
	import type { Attachment } from 'svelte/attachments';
	import { DataTable } from '@manzt/quak';
	import * as mc from '@uwdata/mosaic-core';
	import { Query, count } from '@uwdata/mosaic-sql';
	import * as flech from '@uwdata/flechette';

	import * as Accordion from '$lib/components/ui/accordion/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import ChevronsDownUp from '@lucide/svelte/icons/chevrons-down-up';
	import './app.css';

	let {
		coordinator,
		tables
	}: {
		coordinator: mc.Coordinator;
		tables: Record<string, { data: DataTable; schema: flech.Schema }>;
	} = $props();
	let tableEntries = $derived(Object.entries(tables));

	let tableCols = $derived(
		Object.fromEntries(
			tableEntries.map(([name, { schema }]) => [name, schema.fields.length] as const)
		)
	);

	let tableRows = $derived(
		Object.fromEntries(
			await Promise.all(
				tableEntries.map(([name, _]) =>
					coordinator
						.query(Query.select({ count: count() }).from(name), { type: 'arrow' })
						.then((table) => [name, (table as flech.Table).at(0)['count'] as number] as const)
				)
			)
		)
	);

	function pluralise(value: number, stem: string): string {
		return `${value.toLocaleString()} ${stem}${value > 1 ? 's' : ''}`;
	}

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

<div class="w-full p-2">
	<Card.Root>
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
				{#each tableEntries as [name, { data: table }] (name)}
					{@const rows = tableRows[name]}
					{@const cols = tableCols[name]}
					<Accordion.Item value={name}>
						<Accordion.Trigger class="group hover:no-underline"
							><p class="flex items-center gap-2">
								<span class="group-hover:underline">{name}</span>
								<Badge variant="outline" class="bg-accent text-accent-foreground"
									>{pluralise(rows, 'row')} × {pluralise(cols, 'col')}</Badge
								>
							</p>
						</Accordion.Trigger>
						<Accordion.Content class="flex flex-col gap-4 text-balance" {@attach appendTable(table)}
						></Accordion.Content>
					</Accordion.Item>
				{/each}
			</Accordion.Root>
		</Card.Content>
		<Card.Footer class="justify-end py-2">
			<Badge variant="default">{pluralise(tableEntries.length, 'table')}</Badge>
		</Card.Footer>
	</Card.Root>
</div>
