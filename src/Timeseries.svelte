<script lang="ts">
	import type { Attachment } from 'svelte/attachments';
	import type * as mc from '@uwdata/mosaic-core';
	import { clauseInterval, clausePoint } from '@uwdata/mosaic-core';
	import { createAPIContext } from '@uwdata/vgplot';

	import SettingsIcon from '@lucide/svelte/icons/settings';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import { Checkbox } from '$lib/components/ui/checkbox/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import * as Popover from '$lib/components/ui/popover/index.js';
	import IdNavigator from '$lib/components/composed/IdNavigator.svelte';
	import './app.css';

	// Unique per widget instance, so checkbox ids stay distinct when several
	// widgets share a page.
	const uid = $props.id();

	let {
		coordinator,
		intervals,
		events = [],
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
		overview = true,
		intervalLabels = true,
		eventLabels = false
	}: {
		coordinator: mc.Coordinator;
		intervals: Array<string>;
		events?: Array<string>;
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
		intervalLabels?: boolean;
		eventLabels?: boolean;
	} = $props();

	// Interval lanes first, then event lanes — they share one plot and one y band
	// scale, so this list is the lane order.
	const laneNames = $derived([...intervals, ...events]);

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
	// that is interval bars, event dots, value dots, or a mix.
	const showOverview = $derived(overview && (laneNames.length > 0 || values.length > 0));

	// Every lane and value chart shares this x domain, so panning or zooming any
	// one of them moves them all together. `single` keeps only the latest pan /
	// zoom / brush / reset clause, so those inputs never stack up.
	const domainSel = vg.Selection.single();
	// The current ID's full extent, kept fixed as the overview strip's domain.
	const fullDomain = vg.Param.value(undefined);
	const resetSource = {}; // stable clause source for resetting the shared domain

	// Label visibility is a display toggle: the marks are always drawn, but their
	// opacity is bound to a Param, so flipping it shows/hides them instantly with
	// no plot rebuild (pan/zoom/selection untouched). Two independent toggles.
	let intervalLabelsOn = $state(intervalLabels);
	let eventLabelsOn = $state(eventLabels);
	const intervalLabelParam = $derived(vg.Param.value(intervalLabels ? 1 : 0));
	const eventLabelParam = $derived(vg.Param.value(eventLabels ? 1 : 0));
	$effect(() => intervalLabelParam.update(intervalLabelsOn ? 1 : 0));
	$effect(() => eventLabelParam.update(eventLabelsOn ? 1 : 0));

	// Interval colours are resolved per row in SQL and passed through an identity
	// colour scale. Fill alternates two chart colours by category (or uses the
	// optional `colorCol`, falling back to the palette where null); the border is
	// that fill darkened ~40% via color-mix. Plot shares one colour scale between
	// fill and stroke, so computing them per row is the only way to differ them.
	const intervalChartFallback = () =>
		vg.sql`CASE (DENSE_RANK() OVER (ORDER BY ${vg.column(valueCol)}) - 1) % 2 WHEN 0 THEN 'var(--chart-2)' ELSE 'var(--chart-4)' END`;
	const intervalColor = () =>
		colorCol
			? vg.sql`COALESCE(${vg.column(colorCol)}, ${intervalChartFallback()})`
			: intervalChartFallback();

	// Value marks colour per row from `colorCol` (fallback: the primary colour),
	// so nearby coloured points tint the dots and the area/line between them.
	// Without `colorCol` this must be the plain CSS colour — mosaic's `isColor`
	// only accepts `var(...)`, so a SQL-quoted `'var(...)'` would be read as a
	// column name and the query would fail.
	const valueChartFallback = 'var(--primary)';
	const valueColor = () =>
		colorCol
			? vg.sql`COALESCE(${vg.column(colorCol)}, ${vg.literal(valueChartFallback)})`
			: valueChartFallback;

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
				Math.max(48, Math.ceil(laneNames.reduce((m, l) => Math.max(m, textWidth(l)), 0)) + 16)
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
		// Events and values are point-in-time, so lo and hi are both the start.
		const parts = [
			...intervals.map(
				(t) => `SELECT ${bound(startCol)} AS lo, ${bound(endCol)} AS hi FROM ${quote(t)} ${where}`
			),
			...[...events, ...values].map(
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

	/**
	 * Placeholder shown only when a lane has no rows for the selected ID, so an
	 * empty lane reads as "missing" rather than a bug. The lane must come from an
	 * *aggregate* here: a plain `y` channel would add a GROUP BY, and an empty
	 * table yields no groups — so the row (and the text) would never exist.
	 * `MIN(<literal>)` is NULL on an empty table, hence the COALESCE back.
	 */
	function emptyLanePlaceholder(source: unknown, lane: unknown) {
		return vg.text(source, {
			y: vg.sql`COALESCE(MIN(${lane}), ${lane})`,
			frameAnchor: 'middle',
			text: vg.sql`CASE WHEN count(*) = 0 THEN ${vg.literal('No data for this ' + idCol)} END`,
			fill: 'var(--muted-foreground)',
			fontSize: 11,
			pointerEvents: 'none'
		});
	}

	/** All interval and event tables as lanes of a single plot, sharing one x scale. */
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
					fill: intervalColor(),
					// Semi-transparent so overlapping intervals in a lane read as
					// darker bands rather than hiding one another.
					fillOpacity: 0.1,
					// Border is the fill darkened ~40%, for a crisp edge.
					stroke: intervalColor(),
					strokeWidth: 1.5,
					inset: 3,
					// Default bold-label tip. Add value + pre-formatted start/end as
					// named channels (the times as strings so they need no scale), and
					// hide the raw geometry/colour channels — the fill/stroke are colour
					// strings that would otherwise clutter the tooltip. The names are
					// capitalised so their aliases don't collide with the x1/x2 columns
					// (`start`/`end`), which would make mosaic drop them.
					channels: { Value: valueCol, Start: fmtTime(startCol), End: fmtTime(endCol) },
					tip: {
						format: { x1: false, x2: false, y: false, fill: false, stroke: false }
					},
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
					// Bound to the toggle so labels hide/show without a rebuild.
					opacity: intervalLabelParam,
					clip: true
				}),
				emptyLanePlaceholder(source, lane)
			];
		});

		// Event lanes: a dot per timestamp, the value in the tooltip (or beside the
		// dot when `eventLabels` is on). No y scale for the value — the lane is the
		// y position, which is the whole point of this mark type.
		const eventMarks = events.flatMap((table) => {
			const source = vg.from(table, { filterBy: idSel });
			const lane = vg.literal(table);
			return [
				vg.dot(source, {
					x: startCol,
					y: lane,
					// Diamonds in the primary colour — events read as one kind of thing,
					// rather than borrowing the intervals' alternating palette. A row's
					// `colorCol` still overrides it where set.
					symbol: 'diamond',
					fill: valueColor(),
					r: 3,
					channels: { Value: valueCol, Time: fmtTime(startCol) },
					tip: { format: { x: false, y: false, fill: false, symbol: false } },
					clip: true
				}),
				// Label beside the dot; opacity bound to the toggle (default off).
				vg.text(source, {
					x: startCol,
					y: lane,
					text: valueCol,
					textAnchor: 'start',
					dx: 6,
					fill: 'var(--foreground)',
					stroke: 'var(--background)',
					strokeWidth: 2,
					strokeLinejoin: 'round',
					paintOrder: 'stroke',
					fontSize: 9,
					pointerEvents: 'none',
					opacity: eventLabelParam,
					clip: true
				}),
				emptyLanePlaceholder(source, lane)
			];
		});

		return vg.plot(
			[...marks, ...eventMarks],
			vg.width(width),
			vg.height(laneNames.length * laneHeight + 60),
			vg.marginLeft(gutter),
			vg.marginRight(marginRight),
			vg.marginBottom(hasValues ? 10 : 40),
			vg.xAxis(hasValues ? null : 'bottom'),
			vg.xLabel(null),
			vg.yDomain(laneNames),
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
		// `optimize: false` disables mosaic's M4 downsampling on the line/area.
		// M4 keeps only first/last/min/max per pixel-bin AND bins over the whole
		// (unfiltered) table extent — years across every patient — so one patient's
		// handful of readings collapse into a bin or two and the middle ones get
		// dropped, leaving the line skipping points. There is nothing to downsample
		// in a single-patient view, so we always take the exact, ordered rows.
		const source = vg.from(table, { filterBy: idSel, optimize: false });
		// `panZoomX` binds this plot's x domain to the shared `domainSel`, keeping
		// it in lock-step with the lanes and the other value charts.
		return vg.plot(
			vg.areaY(source, {
				x: startCol,
				y: valueCol,
				z: null,
				fill: valueColor(),
				fillOpacity: 0.1,
				clip: true
			}),
			vg.lineY(source, {
				x: startCol,
				y: valueCol,
				stroke: valueColor(),
				z: null,
				strokeWidth: 1.5,
				clip: true
			}),
			// Hollow markers: a background fill ringed by the (per-row) stroke.
			vg.dot(source, {
				x: startCol,
				y: valueCol,
				fill: 'var(--background)',
				stroke: valueColor(),
				strokeWidth: 1.2,
				r: 2.5,
				// Tooltip: the value (kept numeric via a bare sql wrapper so Plot still
				// number-formats it, and so its alias is `Value` rather than colliding
				// with the `y` channel's `value`) and the pre-formatted time. Hide the
				// raw x/y channels.
				channels: { Value: vg.sql`${vg.column(valueCol)}`, Time: fmtTime(startCol) },
				tip: { format: { x: false, y: false, stroke: false } },
				clip: true
			}),
			// A centred placeholder shown only when this series has no rows for the
			// selected ID (the aggregate yields one row; the text is null otherwise,
			// so nothing renders). Makes an empty lane read as "missing", not a bug.
			vg.text(source, {
				frameAnchor: 'middle',
				text: vg.sql`CASE WHEN count(*) = 0 THEN ${vg.literal('No data for this ' + idCol)} END`,
				fill: 'var(--muted-foreground)',
				fontSize: 11,
				pointerEvents: 'none'
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
			vg.yGrid(true),
			// Colours are resolved per row, so pass them through as-is.
			...(colorCol ? [vg.colorScale('identity')] : []),
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
				fill: intervalColor(),
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
				fill: valueColor(),
				fillOpacity: 0.35,
				clip: true
			})
		);
		// Event dots too, so the strip reflects the whole timeline.
		const eventDotMarks = events.map((table) =>
			vg.dot(vg.from(table, { filterBy: idSel }), {
				x: startCol,
				y: lane,
				symbol: 'diamond',
				r: 1.5,
				fill: valueColor(),
				fillOpacity: 0.5,
				clip: true
			})
		);
		return vg.plot(
			[...barMarks, ...eventDotMarks, ...dotMarks],
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
			...(laneNames.length ? [intervalPlot()] : []),
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
	<code class="relative rounded bg-muted px-[0.3rem] py-[0.2rem] font-mono text-xs font-medium"
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
			<div class="flex items-center gap-2">
				{#if intervals.length || events.length}
					<Popover.Root>
						<Popover.Trigger>
							{#snippet child({ props })}
								<Button
									variant="outline"
									size="icon"
									class="size-7"
									aria-label="Display settings"
									{...props}
								>
									<SettingsIcon class="size-4" />
								</Button>
							{/snippet}
						</Popover.Trigger>
						<Popover.Content class="w-52" side="bottom" portalProps={{ to: rootEl }}>
							<div class="grid gap-3">
								<p class="text-sm leading-none font-medium">Labels</p>
								{#if intervals.length}
									<div class="flex items-center space-x-2">
										<Checkbox id="{uid}-interval-labels" bind:checked={intervalLabelsOn} />
										<Label for="{uid}-interval-labels" class="text-sm font-normal">
											Interval labels
										</Label>
									</div>
								{/if}
								{#if events.length}
									<div class="flex items-center space-x-2">
										<Checkbox id="{uid}-event-labels" bind:checked={eventLabelsOn} />
										<Label for="{uid}-event-labels" class="text-sm font-normal">Event labels</Label>
									</div>
								{/if}
							</div>
						</Popover.Content>
					</Popover.Root>
				{/if}
				<IdNavigator
					bind:value={selectedId}
					search={searchIds}
					neighbor={neighborId}
					onSelect={selectId}
					label={idCol}
					portalTarget={rootEl}
				/>
			</div>
		</Card.Header>
		<Card.Content>
			<div class="ts-dashboard overflow-x-auto" {@attach attachDashboard}></div>
		</Card.Content>
		<Card.Footer class="items-center justify-between gap-3 py-2">
			<!-- Hidden on narrow widget widths to keep the footer uncluttered. -->
			<p class="hidden text-xs text-muted-foreground @min-[560px]:block">{hint}</p>
			<div class="flex shrink-0 gap-2">
				<Badge variant="outline">{pluralise(intervals.length, 'interval')}</Badge>
				{#if events.length}
					<Badge variant="outline">{pluralise(events.length, 'event')}</Badge>
				{/if}
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
