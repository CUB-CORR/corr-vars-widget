<script lang="ts">
	import type { Attachment } from 'svelte/attachments';
	import { DataTable } from '@manzt/quak';
	import * as mc from '@uwdata/mosaic-core';
	import { Query, count } from '@uwdata/mosaic-sql';
	import * as flech from '@uwdata/flechette';

	import { Badge } from '$lib/components/ui/badge/index.js';
	// import { Button } from '$lib/components/ui/button/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import './app.css';

	let {
		coordinator,
		data,
		schema,
		obsLevel,
		creationTime
	}: {
		coordinator: mc.Coordinator;
		data: DataTable;
		schema: flech.Schema;
		obsLevel: string;
		creationTime: Date | null;
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

	function formatDate(date: Date | string | number): string {
		var d = new Date(date),
			month = '' + (d.getMonth() + 1),
			day = '' + d.getDate(),
			year = d.getFullYear();

		if (month.length < 2) month = '0' + month;
		if (day.length < 2) day = '0' + day;

		return [year, month, day].join('-');
	}

	function formatTime(date: Date | string | number): string {
		var d = new Date(date),
			h = '' + d.getHours(),
			min = '' + d.getMinutes(),
			sec = '' + d.getSeconds();

		if (h.length < 2) h = '0' + h;
		if (min.length < 2) min = '0' + min;
		if (sec.length < 2) sec = '0' + sec;

		return [h, min, sec].join(':');
	}

	// type FieldId =
	// 	| 0
	// 	| 2
	// 	| 1
	// 	| 3
	// 	| 4
	// 	| 5
	// 	| 6
	// 	| 7
	// 	| 8
	// 	| 9
	// 	| 10
	// 	| 11
	// 	| 12
	// 	| 13
	// 	| 14
	// 	| 15
	// 	| 16
	// 	| 17
	// 	| 18
	// 	| 19
	// 	| 20
	// 	| 21
	// 	| 22
	// 	| 23
	// 	| 24
	// 	| 25
	// 	| 26
	// 	| -1;
	// const fieldIdMapping: Map<FieldId, string> = new Map([
	// 	[-1, 'Dictionary'],
	// 	[1, 'Null'],
	// 	[2, 'Int'],
	// 	[3, 'Float'],
	// 	[4, 'Binary'],
	// 	[5, 'Utf8'],
	// 	[6, 'Bool'],
	// 	[7, 'Decimal'],
	// 	[8, 'Date'],
	// 	[9, 'Time'],
	// 	[10, 'Timestamp'],
	// 	[11, 'Interval'],
	// 	[12, 'List'],
	// 	[13, 'Struct'],
	// 	[14, 'Union'],
	// 	[15, 'FixedSizeBinary'],
	// 	[16, 'FixedSizeList'],
	// 	[17, 'Map'],
	// 	[18, 'Duration'],
	// 	[19, 'LargeBinary'],
	// 	[20, 'LargeUtf8'],
	// 	[21, 'LargeList'],
	// 	[22, 'RunEndEncoded'],
	// 	[23, 'BinaryView'],
	// 	[24, 'Utf8View'],
	// 	[25, 'ListView'],
	// 	[26, 'LargeListView']
	// ]);

	// const fieldTypeEntries = $derived(
	// 	schema.fields.map((field) => [field.name, field.type] as const)
	// );

	// const fieldTypeEntriesFmt = $derived(
	// 	fieldTypeEntries.map(
	// 		([name, fieldType]) => [name, fieldIdMapping.get(fieldType.typeId) ?? 'Unknown'] as const
	// 	)
	// );

	// const groupedByType = $derived(
	// 	fieldTypeEntriesFmt.reduce(
	// 		(acc, [value, category]) => {
	// 			(acc[category] ??= []).push(value);
	// 			return acc;
	// 		},
	// 		{} as Record<string, string[]>
	// 	)
	// );
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
		<Card.Content>
			<div {@attach appendTable(data)}></div>
			<!-- <div>
				{#each Object.entries(groupedByType) as [fieldType, fields]}
					{fieldType}: {fields.join(', ')} <br />
				{/each}
			</div> -->
		</Card.Content>
		<Card.Footer class="items-center justify-between gap-2 py-2">
			<p class="flex flex-col font-medium text-muted-foreground">
				{#if obsLevel}
					<span>
						Obs Level – {obsLevel}
					</span>
				{/if}
				{#if creationTime}
					<span class="text-[0.8em] text-muted-foreground">
						Created at {formatDate(creationTime)}
						{formatTime(creationTime)}
					</span>
				{/if}
			</p>
			<Badge variant="outline" class="bg-accent text-accent-foreground"
				>{pluralise(tableRows, 'row')} × {pluralise(tableCols, 'col')}</Badge
			>
		</Card.Footer>
	</Card.Root>
</div>
