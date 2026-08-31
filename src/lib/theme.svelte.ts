import type { AnyModel } from '@anywidget/types';

/** The values the Python `theme` trait accepts. */
export type Theme = 'auto' | 'light' | 'dark';

/**
 * The traits every widget in this package carries, mirroring `_ThemeMixin`
 * on the Python side. Each widget's own `Model` intersects with this.
 */
export type Themed = { theme: Theme };

/**
 * Whether this widget should render dark, reconciling an explicit choice with
 * what the host notebook appears to be doing.
 *
 * An explicit `theme` always outranks the guess: a host's theme is inferred,
 * not announced, so the inference has to be overridable. `auto` falls back to
 * {@link createHostTheme}.
 *
 * Shared by every widget in this package through `WidgetRoot`, so the rule
 * lives here once rather than in five components.
 */
export function createTheme(model?: AnyModel<{ theme: Theme }>) {
	const host = createHostTheme();
	let preference = $state<Theme>(model?.get('theme') ?? 'auto');

	$effect(() => {
		if (!model) return;

		// `theme` is a live trait, so `widget.theme = "dark"` in a later cell
		// has to reach an already-rendered widget.
		const update = () => (preference = model.get('theme') ?? 'auto');
		update();
		model.on('change:theme', update);
		return () => model.off('change:theme', update);
	});

	return {
		get isDark() {
			return preference === 'auto' ? host.isDark : preference === 'dark';
		}
	};
}

/**
 * Whether the host notebook is showing a dark theme.
 *
 * The widget is a guest, and every host announces its theme differently:
 * JupyterLab sets a data attribute, VS Code sets a body class -- on the outer
 * webview, which the output iframe may not see at all -- and marimo does
 * neither. Matching on host-specific selectors means a list that is wrong
 * somewhere and silently rots.
 *
 * So this asks two host-agnostic questions instead:
 *
 *  1. What colour is the page actually painted? A host that has committed to a
 *     theme has painted a background, and that is the most direct evidence
 *     there is.
 *  2. Failing that -- a transparent body tells us nothing -- what does the
 *     browser report as the colour-scheme preference?
 *
 * The result drives shadcn's standard `.dark` class, applied to the widget's
 * own root rather than to `document.documentElement`. Toggling the document
 * root (as `mode-watcher` does) would restyle the entire notebook page and
 * every other widget on it, which is not a guest's business.
 */
export function createHostTheme() {
	let isDark = $state(detect());

	$effect(() => {
		const media = window.matchMedia('(prefers-color-scheme: dark)');
		const update = () => (isDark = detect());

		media.addEventListener('change', update);

		// Hosts switch theme by restyling the page, so watch for that rather
		// than polling.
		const observer = new MutationObserver(update);
		for (const node of [document.documentElement, document.body]) {
			if (node) {
				observer.observe(node, {
					attributes: true,
					attributeFilter: ['class', 'style', 'data-jp-theme-light', 'data-theme']
				});
			}
		}

		return () => {
			media.removeEventListener('change', update);
			observer.disconnect();
		};
	});

	return {
		get isDark() {
			return isDark;
		}
	};
}

function detect(): boolean {
	return pageIsDark() ?? window.matchMedia('(prefers-color-scheme: dark)').matches;
}

/** `null` when the page has not painted a background we can read. */
function pageIsDark(): boolean | null {
	for (const node of [document.body, document.documentElement]) {
		const colour = node && parseColour(getComputedStyle(node).backgroundColor);
		if (colour) {
			// Rec. 709 luma. Anything below the midpoint is a dark surface.
			const { r, g, b } = colour;
			return 0.2126 * r + 0.7152 * g + 0.0722 * b < 128;
		}
	}
	return null;
}

/** `null` for transparent or unparseable colours, which carry no signal. */
function parseColour(value: string): { r: number; g: number; b: number } | null {
	const parts = value.match(/[\d.]+/g);
	if (!parts || parts.length < 3) return null;

	const [r, g, b, alpha = '1'] = parts.map(Number) as unknown as [
		number,
		number,
		number,
		string | number
	];
	if (Number(alpha) === 0) return null;

	return { r, g, b };
}
