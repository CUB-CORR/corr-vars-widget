<script lang="ts">
	import type { Attachment } from 'svelte/attachments';
	import type * as mc from '@uwdata/mosaic-core';
	import { clauseInterval } from '@uwdata/mosaic-core';
	import { createAPIContext } from '@uwdata/vgplot';

	import { Badge } from '$lib/components/ui/badge/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import './app.css';

	let {
		coordinator,
		intervals,
		values,
		idsTable,
		idCol,
		startCol,
		endCol,
		valueCol,
		temporal,
		initialId,
		width = 900,
		laneHeight = 28,
		valueHeight = 90,
		marginLeft = 120,
		marginRight = 12,
		overview = true
	}: {
		coordinator: mc.Coordinator;
		intervals: Array<string>;
		values: Array<string>;
		idsTable: string;
		idCol: string;
		startCol: string;
		endCol: string;
		valueCol: string;
		temporal: boolean;
		initialId: string | number | null;
		width?: number;
		laneHeight?: number;
		valueHeight?: number;
		marginLeft?: number;
		marginRight?: number;
		overview?: boolean;
	} = $props();

	// `plot`, `menu` and `search` resolve their coordinator from `this`, so they
	// must be called as methods on an API context. Destructuring them would
	// silently bind them to the global coordinator singleton instead of the
	// per-widget one backed by this widget's DuckDB connection.
	const vg = createAPIContext({ coordinator });

	// Narrows the menu's options; the menu in turn picks the single ID that
	// every plot is filtered by.
	const searchSel = vg.Selection.intersect();
	const idSel = vg.Selection.single();

	const hasValues = values.length > 0;
	// The overview is useful whenever there is anything on the timeline, whether
	// that is interval bars, value dots, or both.
	const showOverview = overview && (intervals.length > 0 || values.length > 0);

	// Every lane and value chart shares this x domain, so panning or zooming any
	// one of them moves them all together. `single` keeps only the latest pan /
	// zoom / brush / reset clause, so those inputs never stack up.
	const domainSel = vg.Selection.single();
	// The current ID's full extent, kept fixed as the overview strip's domain.
	const fullDomain = vg.Param.value(undefined);
	const resetSource = {}; // stable clause source for resetting the shared domain

	// Interval bars alternate between two chart colours; the value charts use the
	// primary colour. `isColor` in mosaic treats `var(...)` as a constant, so
	// these read as colours rather than column references.
	const barColors = ['var(--chart-1)', 'var(--chart-3)'];

	const toX = temporal ? (v: number) => new Date(v) : (v: number) => v;

	const quote = (identifier: string) => `"${identifier.replaceAll('"', '""')}"`;

	/** Bounds of `col` as a double, so the value survives the JSON round trip. */
	function bound(col: string): string {
		return temporal ? `CAST(epoch_ms(${quote(col)}) AS DOUBLE)` : `CAST(${quote(col)} AS DOUBLE)`;
	}

	let lastId: unknown = undefined;

	/** Reset the shared time range to the selected ID's full data extent. */
	async function resetDomain(id: unknown): Promise<void> {
		if (id == null || id === lastId) return;
		lastId = id;

		const where = `WHERE ${quote(idCol)} = ${vg.literal(id)}`;
		const parts = [
			...intervals.map(
				(t) => `SELECT ${bound(startCol)} AS lo, ${bound(endCol)} AS hi FROM ${quote(t)} ${where}`
			),
			...values.map(
				(t) => `SELECT ${bound(startCol)} AS lo, ${bound(startCol)} AS hi FROM ${quote(t)} ${where}`
			)
		];
		const rows = (await coordinator.query(
			`SELECT min(lo) AS lo, max(hi) AS hi FROM (${parts.join(' UNION ALL ')})`,
			{ type: 'json' }
		)) as Array<{ lo: number | null; hi: number | null }>;

		const { lo, hi } = rows[0] ?? {};
		if (lo == null || hi == null) return;
		// Pad so marks at the very edge stay visible.
		const pad = (hi - lo) * 0.02 || 1;
		const domain = [toX(lo - pad), toX(hi + pad)] as [Date, Date] | [number, number];
		fullDomain.update(domain);
		domainSel.update(clauseInterval(vg.column(startCol), domain, { source: resetSource }));
	}

	// The menu republishes `initialId` on mount, which drives the first reset.
	idSel.addEventListener('value', resetDomain);

	/** All interval tables as lanes of a single plot, sharing one x scale. */
	function intervalPlot() {
		// Midpoint of an interval, for centring its text label.
		const start = vg.column(startCol);
		const midpoint = vg.sql`${start} + (${vg.column(endCol)} - ${start}) / 2`;

		const marks = intervals.flatMap((table) => {
			const source = vg.from(table, { filterBy: idSel });
			const lane = vg.literal(table);
			return [
				vg.barX(source, {
					x1: startCol,
					x2: endCol,
					y: lane,
					fill: valueCol,
					// Semi-transparent so overlapping intervals in a lane read as
					// darker bands rather than hiding one another.
					fillOpacity: 0.7,
					stroke: 'var(--foreground)',
					strokeWidth: 0.5,
					strokeOpacity: 0.35,
					inset: 3,
					tip: true,
					title: valueCol,
					clip: true
				}),
				vg.text(source, {
					x: midpoint,
					y: lane,
					text: valueCol,
					// White fill + `mix-blend-mode: difference` (applied in CSS) keeps
					// the label legible on any bar colour without a halo: the text is
					// painted as the inverse of whatever is behind it.
					fill: 'white',
					fontSize: 9,
					pointerEvents: 'none',
					clip: true
				})
			];
		});

		return vg.plot(
			marks,
			vg.width(width),
			vg.height(intervals.length * laneHeight + 60),
			vg.marginLeft(marginLeft),
			vg.marginRight(marginRight),
			vg.marginBottom(hasValues ? 10 : 40),
			vg.xAxis(hasValues ? null : 'bottom'),
			vg.xLabel(null),
			vg.yDomain(intervals),
			vg.yLabel(null),
			vg.yPadding(0.2),
			vg.colorRange(barColors),
			vg.grid(true),
			// Shares `domainSel` with the value charts, so drag-pan and wheel-zoom
			// move the lanes and the charts together.
			vg.panZoomX({ x: domainSel })
		);
	}

	/** One small line chart per value table. `last` carries the shared x axis. */
	function valuePlot(table: string, last: boolean) {
		const source = vg.from(table, { filterBy: idSel });
		// `panZoomX` binds this plot's x domain to the shared `domainSel`, keeping
		// it in lock-step with the lanes and the other value charts.
		return vg.plot(
			vg.areaY(source, {
				x: startCol,
				y: valueCol,
				fill: 'var(--primary)',
				fillOpacity: 0.1,
				clip: true
			}),
			vg.lineY(source, {
				x: startCol,
				y: valueCol,
				stroke: 'var(--primary)',
				strokeWidth: 1.5,
				clip: true
			}),
			// Hollow markers: a background fill ringed by the primary stroke.
			vg.dot(source, {
				x: startCol,
				y: valueCol,
				fill: 'var(--background)',
				stroke: 'var(--primary)',
				strokeWidth: 1.2,
				r: 2.5,
				tip: true,
				clip: true
			}),
			vg.width(width),
			vg.height(valueHeight),
			vg.marginLeft(marginLeft),
			vg.marginRight(marginRight),
			vg.marginBottom(last ? 40 : 8),
			vg.xAxis(last ? 'bottom' : null),
			vg.xLabel(null),
			vg.yLabel(table),
			// Horizontal label sitting next to the axis, instead of a rotated one
			// stranded out in the left margin.
			vg.yLabelAnchor('top'),
			// A little headroom so the clip does not shave the top marker, which
			// otherwise sits flush against the frame edge.
			vg.yInsetTop(4),
			vg.grid(true),
			vg.panZoomX({ x: domainSel })
		);
	}

	/**
	 * A compressed, full-range strip of the whole timeline: interval bars plus a
	 * dot for every value sample. Brushing it writes the shared domain, jumping
	 * every coupled plot to that window; the strip itself stays at the full
	 * extent as a fixed reference. Collapsing everything onto one lane keeps it
	 * useful even when a case has only values and no intervals.
	 */
	function overviewPlot() {
		// A single hidden lane collapses everything into one strip; it also gives
		// the brush a y scale to size its rectangle against.
		const lane = vg.literal('timeline');
		const barMarks = intervals.map((table) =>
			vg.barX(vg.from(table, { filterBy: idSel }), {
				x1: startCol,
				x2: endCol,
				y: lane,
				fill: valueCol,
				fillOpacity: 0.35,
				clip: true
			})
		);
		// Value samples as a translucent rug of dots; overlapping points darken,
		// so density reads even with many samples. (Swap for `densityX` if a
		// smooth curve is ever preferable.)
		const dotMarks = values.map((table) =>
			vg.dot(vg.from(table, { filterBy: idSel }), {
				x: startCol,
				y: lane,
				r: 1.5,
				fill: 'var(--primary)',
				fillOpacity: 0.35,
				clip: true
			})
		);
		return vg.plot(
			[...barMarks, ...dotMarks],
			vg.width(width),
			vg.height(34),
			vg.marginLeft(marginLeft),
			vg.marginRight(marginRight),
			vg.marginTop(4),
			vg.marginBottom(18),
			vg.xDomain(fullDomain),
			vg.xLabel(null),
			vg.xTickSize(3),
			vg.yDomain(['timeline']),
			vg.yPadding(0),
			vg.yAxis(null),
			vg.colorRange(barColors),
			vg.intervalX({ as: domainSel, field: vg.column(startCol) })
		);
	}

	function buildDashboard(): HTMLElement {
		const controls = vg.hconcat(
			vg.menu({
				label: idCol,
				as: idSel,
				from: idsTable,
				column: idCol,
				filterBy: searchSel,
				value: initialId
			}),
			vg.hspace(10),
			vg.search({
				label: 'Filter',
				as: searchSel,
				from: idsTable,
				column: idCol,
				type: 'contains',
				// `contains` has no overload for numeric ids, so match on the text form.
				field: vg.cast(vg.column(idCol), 'VARCHAR')
			})
		);
		return vg.vconcat(
			controls,
			vg.vspace(10),
			...(intervals.length ? [intervalPlot()] : []),
			...values.map((table, i) => valuePlot(table, i === values.length - 1)),
			...(showOverview ? [vg.vspace(6), overviewPlot()] : [])
		);
	}

	const attachDashboard: Attachment<HTMLElement> = (node) => {
		node.appendChild(buildDashboard());
		return () => coordinator.clear();
	};

	function pluralise(value: number, stem: string): string {
		return `${value.toLocaleString()} ${stem}${value === 1 ? '' : 's'}`;
	}

	const hint =
		'Drag to pan, scroll to zoom.' +
		(showOverview ? ' Brush the overview strip to jump to a range.' : '');
</script>

<div class="w-full p-2">
	<Card.Root>
		<Card.Header>
			<Card.Title>Timeseries</Card.Title>
			<Card.Description>Measurements for a single {idCol}</Card.Description>
		</Card.Header>
		<Card.Content>
			<div class="ts-dashboard overflow-x-auto" {@attach attachDashboard}></div>
		</Card.Content>
		<Card.Footer class="items-center justify-between gap-3 py-2">
			<p class="text-xs text-muted-foreground">{hint}</p>
			<div class="flex shrink-0 gap-2">
				<Badge variant="outline">{pluralise(intervals.length, 'interval')}</Badge>
				<Badge variant="default">{pluralise(values.length, 'value')}</Badge>
			</div>
		</Card.Footer>
	</Card.Root>
</div>

<!-- vgplot builds raw DOM (not Svelte-scoped), so the mosaic inputs need :global. -->
<style>
	.ts-dashboard :global(.input) {
		display: inline-flex;
		align-items: baseline;
		gap: 0.4rem;
		margin-right: 0.85rem;
		font-size: 0.8125rem;
	}
	.ts-dashboard :global(.input > label) {
		font-weight: 500;
		white-space: nowrap;
		color: var(--muted-foreground, #6b7280);
	}
	.ts-dashboard :global(.input select),
	.ts-dashboard :global(.input input) {
		padding: 0.15rem 0.45rem;
		border: 1px solid var(--border, #e5e7eb);
		border-radius: 0.375rem;
		background: transparent;
		font-size: 0.8125rem;
		color: inherit;
	}
	/* Recolour Observable Plot's grid lines (default: faint currentColor). */
	.ts-dashboard :global([aria-label$='grid'] line) {
		stroke: var(--border, #e5e7eb);
		stroke-opacity: 1;
	}
	/* Rounded interval bars. `rx` cascades to `ry`, so all corners round. */
	.ts-dashboard :global([aria-label='bar'] rect) {
		rx: var(--radius, 0.5rem);
	}
	/* Bar labels: paint white, then blend against whatever is behind so the text
	   is always the inverse of the bar colour — legible on every chart colour. */
	.ts-dashboard :global([aria-label='text'] text) {
		mix-blend-mode: difference;
	}
	/* Themed, rounded tip callout. Plot draws it as a <path> (already rounded)
	   plus text; recolour the border and surface to match the card. */
	.ts-dashboard :global([aria-label='tip'] path) {
		fill: var(--popover, #fff);
		stroke: var(--border, #e5e7eb);
	}
	.ts-dashboard :global([aria-label='tip'] text) {
		fill: var(--popover-foreground, #000);
	}
</style>
