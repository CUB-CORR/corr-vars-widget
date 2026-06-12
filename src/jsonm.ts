import { defineWidget } from "@anywidget/svelte";
import type { Model } from "./Jsonm.svelte";
import Jsonm from "./Jsonm.svelte";

export default defineWidget<Model>(Jsonm);
