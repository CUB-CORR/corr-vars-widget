import App from './Timeseries.svelte';
import { mount, unmount } from 'svelte';

import * as mc from '@uwdata/mosaic-core';

import type * as aw from '@anywidget/types';

import { mosaicInitialise } from './utils/mosaic';

export type Model = {
	_intervals: Array<string>;
	_values: Array<string>;
	_ids_table: string;
	_id_col: string;
	_start_col: string;
	_end_col: string;
	_value_col: string;
	_color_col: string;
	_temporal: boolean;
	_initial_id: string | number | null;
};

export default () => {
	let coordinator = new mc.Coordinator();
	return {
		initialize({ model }: aw.InitializeProps<Model>) {
			mosaicInitialise(coordinator, model);
		},
		render({ model, el }: aw.RenderProps<Model>) {
			const app = mount(App, {
				target: el,
				props: {
					coordinator,
					intervals: model.get('_intervals'),
					values: model.get('_values'),
					idsTable: model.get('_ids_table'),
					idCol: model.get('_id_col'),
					startCol: model.get('_start_col'),
					endCol: model.get('_end_col'),
					valueCol: model.get('_value_col'),
					colorCol: model.get('_color_col') || undefined,
					temporal: model.get('_temporal'),
					initialId: model.get('_initial_id')
				}
			});
			return () => unmount(app);
		}
	};
};
