import App from './Obs.svelte';
import { mount, unmount } from 'svelte';

import * as mc from '@uwdata/mosaic-core';
import { Query } from '@uwdata/mosaic-sql';
import * as flech from '@uwdata/flechette';

import { DataTable } from '@manzt/quak';
import { assert } from './utils/assert';

import type * as aw from '@anywidget/types';
import { isFlechetteTable } from './utils/guards';

import { mosaicInitialise } from './utils/mosaic';

type Model = {
	_table_name: string;
	_columns: Array<string>;
	sql: string;
};

export default () => {
	let coordinator = new mc.Coordinator();
	return {
		initialize({ model} : aw.InitializeProps<Model>) {
			mosaicInitialise(coordinator, model)
		},
		async render({ model, el }: aw.RenderProps<Model>) {
			const name = model.get("_table_name")
			const columns =  model.get("_columns")

			const schema = await getTableSchema(coordinator, {
					tableName: name,
					columns: columns
				})
			const dataTable = new DataTable({
				table: name,
				schema: schema
			});
			coordinator.connect(dataTable);
			dataTable.sql.subscribe((sql) => {
				model.set(
					'sql',
					sql || ''
				);
				model.save_changes();
			});

			const app = mount(App, {
				target: el,
				props: { coordinator: coordinator, data: dataTable, schema: schema }
			});
			return () => unmount(app);
		}
	};
};

async function getTableSchema(
	coordinator: mc.Coordinator,
	options: {
		tableName: string;
		columns: Array<string>;
	}
): Promise<flech.Schema> {
	let empty = await coordinator.query(
		Query.from(options.tableName)
			.select(...options.columns)
			.limit(0),
		{ type: 'arrow' }
	);
	assert(isFlechetteTable(empty), 'Expected a flechette table.');
	return empty.schema;
}
