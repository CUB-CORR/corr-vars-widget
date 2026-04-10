<script lang="ts">
	import type { Attachment } from 'svelte/attachments';
	import { DataTable } from '@manzt/quak';
	import * as mc from '@uwdata/mosaic-core';
	import { Query, count } from '@uwdata/mosaic-sql';
	import * as flech from '@uwdata/flechette';

	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import './app.css';

	let {
		coordinator,
		data,
		schema
	}: {
		coordinator: mc.Coordinator;
		data: DataTable;
		schema: flech.Schema;
	} = $props();

	let tableCols = $derived(schema.fields.length);

	let tableRows = $derived(
		await coordinator
			.query(Query.select({ count: count() }).from('obs'), { type: 'arrow' })
			.then((table) => (table as flech.Table).at(0)['count'] as number)
	);

	function pluralise(value: number, stem: string): string {
		return `${value.toLocaleString()} ${stem}${value > 1 ? 's' : ''}`;
	}

	function appendTable(table: DataTable): Attachment<HTMLElement> {
		return (node: HTMLElement) => {
			node.appendChild(table.node());
		};
	}
</script>

<div class="w-full p-2">
	<Card.Root>
		<Card.Header>
			<Card.Title>Obs</Card.Title>
			<Card.Description>Static or aggregated data</Card.Description>
			<!-- <Card.Action>
			<Button variant="ghost" size="icon" onclick={openClose}
				><ChevronsDownUp /><span class="sr-only">Open</span></Button
			>
		</Card.Action> -->
		</Card.Header>
		<Card.Content {@attach appendTable(data)}></Card.Content>
		<Card.Footer class="justify-end py-2">
			<Badge variant="outline" class="bg-accent text-accent-foreground"
				>{pluralise(tableRows, 'row')} × {pluralise(tableCols, 'col')}</Badge
			>
		</Card.Footer>
	</Card.Root>
</div>
