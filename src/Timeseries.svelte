<script lang="ts">
	import type { Attachment } from 'svelte/attachments';
	import type * as mc from '@uwdata/mosaic-core';
	import { clauseInterval, clausePoint } from '@uwdata/mosaic-core';
	import { createAPIContext } from '@uwdata/vgplot';

	import { Badge } from '$lib/components/ui/badge/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import IdNavigator from '$lib/components/composed/IdNavigator.svelte';
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
		colorCol,
		temporal,
		initialId,
		width = 900,
		laneHeight = 28,
		valueHeight = 90,
		marginLeft,
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
		colorCol?: string;
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

	// The combobox picks the single ID that every plot is filtered by.
	const idSel = vg.Selection.single();
	const idSource = {}; // stable clause source for the selected ID

	/** Set the selected ID; drives every plot's `filterBy`. */
	function selectId(id: string | number): void {
		idSel.update(clausePoint(idCol, id, { source: idSource }));
	}

	/** Server-side ID lookup for the combobox (there may be thousands). */
	async function searchIds(query: string): Promise<Array<string | number>> {
		const filter = query
			? `WHERE CAST(${quote(idCol)} AS VARCHAR) ILIKE ${vg.literal('%' + query + '%')}`
			: '';
		const rows = (await coordinator.query(
			`SELECT ${quote(idCol)} AS id FROM ${quote(idsTable)} ${filter} ORDER BY ${quote(idCol)} LIMIT 100`,
			{ type: 'json' }
		)) as Array<{ id: string | number }>;
		return rows.map((r) => r.id);
	}

	/** The previous (-1) or next (+1) ID in sorted order, or null at an edge. */
	async function neighborId(id: string | number, dir: -1 | 1): Promise<string | number | null> {
		const cmp = dir < 0 ? '<' : '>';
		const ord = dir < 0 ? 'DESC' : 'ASC';
		const rows = (await coordinator.query(
			`SELECT ${quote(idCol)} AS id FROM ${quote(idsTable)} WHERE ${quote(idCol)} ${cmp} ${vg.literal(id)} ORDER BY ${quote(idCol)} ${ord} LIMIT 1`,
			{ type: 'json' }
		)) as Array<{ id: string | number }>;
		return rows.length ? rows[0].id : null;
	}

	let selectedId = $derived<string | number | null>(initialId);
	// Portal target for the combobox popover, so it stays inside the widget DOM
	// (this template may render in a shadow root).
	let rootEl = $state<HTMLElement>();

	const hasValues = $derived(values.length > 0);
	// The overview is useful whenever there is anything on the timeline, whether
	// that is interval bars, value dots, or both.
	const showOverview = $derived(overview && (intervals.length > 0 || values.length > 0));

	// Every lane and value chart shares this x domain, so panning or zooming any
	// one of them moves them all together. `single` keeps only the latest pan /
	// zoom / brush / reset clause, so those inputs never stack up.
	const domainSel = vg.Selection.single();
	// The current ID's full extent, kept fixed as the overview strip's domain.
	const fullDomain = vg.Param.value(undefined);
	const resetSource = {}; // stable clause source for resetting the shared domain

	// Interval colours are resolved per row in SQL and passed through an identity
	// colour scale. Fill alternates two chart colours by category (or uses the
	// optional `colorCol`, falling back to the palette where null); the border is
	// that fill darkened ~40% via color-mix. Plot shares one colour scale between
	// fill and stroke, so computing them per row is the only way to differ them.
	const chartFallback = () =>
		vg.sql`CASE (DENSE_RANK() OVER (ORDER BY ${vg.column(valueCol)}) - 1) % 2 WHEN 0 THEN 'var(--chart-1)' ELSE 'var(--chart-2)' END`;
	const fillColor = () =>
		colorCol ? vg.sql`COALESCE(${vg.column(colorCol)}, ${chartFallback()})` : chartFallback();
	const strokeColor = () => vg.sql`('color-mix(in oklab, ' || ${fillColor()} || ' 60%, #000)')`;

	// Measure with Plot's own axis font (it hard-sets `system-ui` 10px on the
	// SVG root), so the gutter width and the ellipsis match what actually renders.
	const measureCtx = document.createElement('canvas').getContext('2d');
	if (measureCtx) measureCtx.font = '10px system-ui, sans-serif';
	const textWidth = (t: string): number =>
		measureCtx ? measureCtx.measureText(t).width : t.length * 6;

	/** Truncate with an ellipsis so a label fits `maxPx` at the axis font. */
	function ellipsize(text: string, maxPx: number): string {
		if (textWidth(text) <= maxPx) return text;
		let lo = 0;
		let hi = text.length;
		while (lo < hi) {
			const mid = (lo + hi + 1) >> 1;
			if (textWidth(text.slice(0, mid) + '…') <= maxPx) lo = mid;
			else hi = mid - 1;
		}
		return text.slice(0, lo).trimEnd() + '…';
	}

	// Auto-size the left gutter to the longest lane name so the (right-aligned)
	// y-axis labels sit against the axis without a hand-tuned margin: no clipping
	// on the left, no crowding the bars on the right. Floored for numeric ticks
	// and capped so one very long name cannot swallow the plot; names past the cap
	// are ellipsised (see `yTickFormat`). The same value goes to every plot,
	// keeping their x axes aligned.
	const gutter = $derived(
		marginLeft ??
			Math.min(
				200,
				Math.max(48, Math.ceil(intervals.reduce((m, l) => Math.max(m, textWidth(l)), 0)) + 16)
			)
	);

	const toX = $derived(temporal ? (v: number) => new Date(v) : (v: number) => v);

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

	idSel.addEventListener('value', resetDomain);
	$effect(() => {
		// Seed the initial selection, which drives the first reset and filters marks.
		if (initialId != null) selectId(initialId);
	});

	/** A timestamp formatted like "2024-02-12 07:00" (or the raw value if not a date). */
	const fmtTime = (c: string) =>
		temporal
			? vg.sql`strftime(${vg.column(c)}, '%Y-%m-%d %H:%M')`
			: vg.sql`CAST(${vg.column(c)} AS VARCHAR)`;

	/** Interval tooltip: the value on one line, the time range on the next. */
	function intervalTitle() {
		return vg.sql`${vg.column(valueCol)} || chr(10) || ${fmtTime(startCol)} || ' – ' || ${fmtTime(endCol)}`;
	}

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
					fill: fillColor(),
					// Semi-transparent so overlapping intervals in a lane read as
					// darker bands rather than hiding one another.
					fillOpacity: 0.7,
					// Border is the fill darkened ~40%, for a crisp edge.
					stroke: strokeColor(),
					strokeWidth: 1,
					inset: 3,
					tip: true,
					// Plot shows only the title channel, so pack value + range into it.
					title: intervalTitle(),
					clip: true
				}),
				vg.text(source, {
					x: midpoint,
					y: lane,
					text: valueCol,
					// Dark text with a background-coloured halo (drawn first via
					// paint-order) stays legible over any bar colour.
					fill: 'var(--foreground)',
					stroke: 'var(--background)',
					strokeWidth: 2,
					strokeLinejoin: 'round',
					paintOrder: 'stroke',
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
			vg.marginLeft(gutter),
			vg.marginRight(marginRight),
			vg.marginBottom(hasValues ? 10 : 40),
			vg.xAxis(hasValues ? null : 'bottom'),
			vg.xLabel(null),
			vg.yDomain(intervals),
			vg.yLabel(null),
			// Ellipsise lane names that exceed the (capped) gutter.
			vg.yTickFormat((d: unknown) => ellipsize(String(d), gutter - 12)),
			vg.yPadding(0.2),
			// Colours are already resolved per row, so pass them through as-is.
			vg.colorScale('identity'),
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
				// Default multi-channel tip (bold field names). Format the time to
				// "2024-02-12 07:00" — in UTC, like DuckDB's strftime — rather than
				// Plot's default ISO string.
				tip: temporal
					? { format: { x: (d: Date) => d.toISOString().slice(0, 16).replace('T', ' ') } }
					: true,
				clip: true
			}),
			vg.width(width),
			// The last chart carries the x axis, which needs a bigger bottom margin.
			// Grow its total height by the same amount so every chart keeps an equal
			// *plotted* area (height − margins) rather than shrinking the last one.
			vg.height(valueHeight + (last ? 32 : 0)),
			vg.marginLeft(gutter),
			vg.marginRight(marginRight),
			vg.marginBottom(last ? 40 : 8),
			vg.xAxis(last ? 'bottom' : null),
			vg.xLabel(null),
			// Horizontal label next to the axis (not a rotated one stranded in the
			// margin), ellipsised so a long series name can't run across the chart.
			vg.yLabel(ellipsize(table, 200)),
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
				fill: fillColor(),
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
			vg.marginLeft(gutter),
			vg.marginRight(marginRight),
			vg.marginTop(4),
			vg.marginBottom(18),
			vg.xDomain(fullDomain),
			vg.xLabel(null),
			vg.xTickSize(3),
			vg.yDomain(['timeline']),
			vg.yPadding(0),
			vg.yAxis(null),
			vg.colorScale('identity'),
			vg.intervalX({ as: domainSel, field: vg.column(startCol) })
		);
	}

	function buildDashboard(): HTMLElement {
		// The ID selector is a Svelte combobox in the template; here we build only
		// the plots.
		return vg.vconcat(
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

	const hint = $derived(
		'Drag to pan, scroll to zoom.' +
			(showOverview ? ' Brush the overview strip to jump to a range.' : '')
	);
</script>

{#snippet codeChip(text: string)}
	<code class="relative rounded bg-muted px-[0.3rem] py-[0.2rem] font-mono text-xs font-semibold"
		>{text}</code
	>
{/snippet}

<div class="@container w-full p-2" bind:this={rootEl}>
	<Card.Root>
		<Card.Header class="flex flex-row items-center justify-between gap-4 space-y-0">
			<div class="grid gap-1.5">
				<Card.Title>Timeseries</Card.Title>
				<Card.Description>Measurements for a single {@render codeChip(idCol)}</Card.Description>
			</div>
			<IdNavigator
				bind:value={selectedId}
				search={searchIds}
				neighbor={neighborId}
				onSelect={selectId}
				label={idCol}
				portalTarget={rootEl}
			/>
		</Card.Header>
		<Card.Content>
			<div class="ts-dashboard overflow-x-auto" {@attach attachDashboard}></div>
		</Card.Content>
		<Card.Footer class="items-center justify-between gap-3 py-2">
			<!-- Hidden on narrow widget widths to keep the footer uncluttered. -->
			<p class="hidden text-xs text-muted-foreground @min-[560px]:block">{hint}</p>
			<div class="flex shrink-0 gap-2">
				<Badge variant="outline">{pluralise(intervals.length, 'interval')}</Badge>
				<Badge variant="default">{pluralise(values.length, 'value')}</Badge>
			</div>
		</Card.Footer>
	</Card.Root>
</div>

<!-- vgplot builds raw DOM (not Svelte-scoped), so the plot internals need :global. -->
<style>
	/* Recolour Observable Plot's grid lines (default: faint currentColor). */
	.ts-dashboard :global([aria-label$='grid'] line) {
		stroke: var(--border, #e5e7eb);
		stroke-opacity: 1;
	}
</style>
