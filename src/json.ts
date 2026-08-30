import { defineWidget } from '@anywidget/svelte';
import type { Model } from './JSON.svelte';
import JSON from './JSON.svelte';

export default defineWidget<Model>(JSON);
