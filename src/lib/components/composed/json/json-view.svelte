<script module>
	export type JsonViewerProps = {
		json: any;
		depth?: number;
		_cur?: number;
		_last?: boolean;
	};
</script>

<script lang="ts">
	let { json, depth = Infinity, _cur = 0, _last = true }: JsonViewerProps = $props();
	import { get } from 'http';
	import Self from './json-view.svelte';

	let items = $derived(getType(json) === 'object' ? Object.keys(json) : []);
	let isArray = $derived(Array.isArray(json));
	let brackets = $derived(isArray ? ['[', ']'] : ['{', '}']);
	let collapsed = $derived(depth < _cur);

	function getType(i: any): string {
		if (i === null) return 'null';
		return typeof i;
	}

	function stringify(i: any): string {
		return JSON.stringify(i);
	}

	function format(i: any): string {
		switch (getType(i)) {
			case 'function':
				return 'f () {...}';
			case 'symbol':
				return i.toString();
			default:
				return stringify(i);
		}
	}

	function clicked() {
		collapsed = !collapsed;
	}

	function pressed(e: Event) {
		if (e instanceof KeyboardEvent && ['Enter', ' '].includes(e.key)) clicked();
	}

	const sepClass = 'text-current';
	const keyClass = 'text-current';
	const bktClass = 'text-current p-1 -m-1 rounded';

	const bktHoverClass = 'hover:bg-gray-200 dark:hover:bg-gray-700';

	const defaultValColor = 'text-gray-600 dark:text-gray-400';
	const valColor = new Map<string, string>([
		['string', 'text-green-600 dark:text-green-400'],
		['number', 'text-orange-600 dark:text-orange-400'],
		['boolean', 'text-blue-600 dark:text-blue-400'],
		['null', 'text-gray-600 dark:text-gray-400'],
		['undefined', 'text-gray-600 dark:text-gray-400'],
		['function', 'text-purple-600 dark:text-purple-400'],
		['symbol', 'text-yellow-600 dark:text-yellow-400']
	]);
</script>

<div class="inline font-mono text-card-foreground">
	{#if !items.length}
		<span class={bktClass}>{brackets[0]}{brackets[1]}</span>{#if !_last}<span class={sepClass}
				>,</span
			>{/if}
	{:else if collapsed}
		<span
			class={[bktClass, bktHoverClass]}
			role="button"
			tabindex="0"
			onclick={clicked}
			onkeydown={pressed}>{brackets[0]}...{brackets[1]}</span
		>{#if !_last && collapsed}<span class={sepClass}>,</span>{/if}
	{:else}
		<span
			class={[bktClass, bktHoverClass]}
			role="button"
			tabindex="0"
			onclick={clicked}
			onkeydown={pressed}>{brackets[0]}</span
		>
		<ul class="m-0 list-none border-l border-dashed border-muted-foreground p-0 pl-4" role="group">
			{#each items as i, idx}
				<li>
					{#if !isArray}
						<span class={keyClass}>{stringify(i)}</span><span class={sepClass}>:</span>
					{/if}
					{#if getType(json[i]) === 'object'}
						<Self json={json[i]} {depth} _cur={_cur + 1} _last={idx === items.length - 1} />
					{:else}
						<span class={valColor.get(getType(json[i])) || defaultValColor}>{format(json[i])}</span
						>{#if idx < items.length - 1}<span class={sepClass}>,</span>{/if}
					{/if}
				</li>
			{/each}
		</ul>
		<span
			class={[bktClass, bktHoverClass]}
			role="button"
			tabindex="0"
			onclick={clicked}
			onkeydown={pressed}>{brackets[1]}</span
		>{#if !_last}<span class={sepClass}>,</span>{/if}
	{/if}
</div>
