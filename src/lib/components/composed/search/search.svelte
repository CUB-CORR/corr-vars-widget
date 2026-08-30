<script lang="ts">
	// Components
	import * as InputGroup from '$lib/components/ui/input-group/index.js';
	import * as ToggleGroup from '$lib/components/ui/toggle-group/index.js';

	// Icons
	import CaseSensitiveIcon from '@lucide/svelte/icons/case-sensitive';
	import RegexIcon from '@lucide/svelte/icons/regex';
	import SearchIcon from '@lucide/svelte/icons/search';

	// Helpers
	function termLengthFmt(length: number): string {
		if (length === 0) {
			return 'No terms';
		} else if (length === 1) {
			return '1 unique term';
		} else {
			return `${length} unique terms`;
		}
	}

	// Data loading
	let { terms, onfiltered }: { terms: string[]; onfiltered: (filtered: string[]) => void } =
		$props();
	let uniqueTerms = $derived<string[]>(Array.from(new Set(terms)));
	const termLengthDescription = $derived<string>(termLengthFmt(uniqueTerms.length));

	function termsFilterFn(filterValue: string): string[] {
		return uniqueTerms.filter((term) => {
			if (filterValue === '') {
				return false;
			} else {
				if (searchOptions.includes('regex')) {
					const flags = searchOptions.includes('case-insensitive') ? 'i' : '';
					return searchTermValid && new RegExp(searchTerm, flags).test(term);
				}

				if (searchOptions.includes('case-insensitive')) {
					return term.toLowerCase().includes(searchTerm.toLowerCase());
				} else {
					return term.includes(searchTerm);
				}
			}
		});
	}

	// Search setup
	let searchOptions = $state<string[]>([]);
	let searchTerm = $state<string>('');

	const searchTermValid = $derived.by<boolean>(() => {
		if (searchTerm === '') {
			return true;
		}

		if (searchOptions.includes('regex')) {
			try {
				const flags = searchOptions.includes('case-insensitive') ? 'i' : '';
				new RegExp(searchTerm, flags);
				return true;
			} catch (e) {
				return false;
			}
		}

		return true;
	});

	const currentStateDescription = $derived<string>(
		searchTerm === '' ? termLengthDescription : searchTermValid ? '' : 'Invalid regex'
	);

	const onSearchTermChange = (searchTerm: string) => {
		onfiltered(searchTerm ? termsFilterFn(searchTerm) : uniqueTerms);
	};
</script>

<div class="flex flex-col gap-2 md:flex-row">
	<InputGroup.Root class="max-w-md">
		<InputGroup.Input
			bind:value={searchTerm}
			aria-invalid={!searchTermValid}
			placeholder="Filter terms..."
			oninput={(e: Event) => onSearchTermChange((e.target as HTMLInputElement).value)}
			onchange={(e: Event) => onSearchTermChange((e.target as HTMLInputElement).value)}
		/>
		<InputGroup.Addon>
			<SearchIcon />
		</InputGroup.Addon>
		<InputGroup.Addon align="inline-end">{currentStateDescription}</InputGroup.Addon>
	</InputGroup.Root>

	<ToggleGroup.Root
		bind:value={searchOptions}
		onValueChange={() => onSearchTermChange(searchTerm)}
		variant="outline"
		size="default"
		type="multiple"
	>
		<ToggleGroup.Item value="case-insensitive" aria-label="Toggle case insensitive">
			<CaseSensitiveIcon class="size-4.5" />
		</ToggleGroup.Item>
		<ToggleGroup.Item value="regex" aria-label="Toggle regex">
			<RegexIcon class="size-4.5" />
		</ToggleGroup.Item>
	</ToggleGroup.Root>
</div>
