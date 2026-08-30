<script lang="ts">
	import type { AnyModel } from '@anywidget/types';
	import { untrack, type Snippet } from 'svelte';

	import { createTheme, type Theme } from '$lib/theme.svelte';
	import '../../../app.css';

	/**
	 * The outermost element of every widget in this package.
	 *
	 * It exists so that the three things every widget needs identically are
	 * stated once: the stylesheet, the `.corr-vars-widget` class that scopes it,
	 * and the `.dark` toggle driven by the `theme` trait.
	 *
	 * Pass `model` so the widget follows `theme`; without it the root still
	 * renders and simply follows the host.
	 */
	let {
		model,
		class: className = '',
		ref = $bindable(),
		children
	}: {
		model?: AnyModel<{ theme: Theme }>;
		class?: string;
		/** The root element, for anything that needs to portal inside the theme. */
		ref?: HTMLElement;
		children?: Snippet;
	} = $props();

	// anywidget hands each widget one model for its lifetime, and `createTheme`
	// tracks changes through `model.on('change:theme')` rather than through the
	// prop -- so reading it once here is the intent, not an oversight.
	const theme = createTheme(untrack(() => model));
</script>

<div bind:this={ref} class="corr-vars-widget {className}" class:dark={theme.isDark}>
	{@render children?.()}
</div>
