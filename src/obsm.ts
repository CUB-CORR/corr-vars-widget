import App from './Obsm.svelte';
import { mount, unmount } from 'svelte';

import * as mc from '@uwdata/mosaic-core';
import { Query } from '@uwdata/mosaic-sql';
import * as flech from '@uwdata/flechette';

import { DataTable } from '@manzt/quak';
import { assert } from './utils/assert';

import type * as aw from '@anywidget/types';
import { isFlechetteTable } from './utils/guards';

import { mosaicInitialise } from './utils/mosaic';

type Table = {
	_table_name: string;
	_columns: Array<string>;
	sql: string;
};

type Model = {
	_tables: Array<Table>;
};

export default () => {
	let coordinator = new mc.Coordinator();
	return {
		initialize({ model }: aw.InitializeProps<Model>) {
			mosaicInitialise(coordinator, model);
		},
		async render({ model, el }: aw.RenderProps<Model>) {
			const tables = model.get('_tables');
			const appTables: Record<string, { data: DataTable; schema: flech.Schema }> = {};
			for (const table of tables) {
				const schema = await getTableSchema(coordinator, {
					tableName: table._table_name,
					columns: table._columns
				});
				const dataTable = new DataTable({
					table: table._table_name,
					schema: schema
				});
				coordinator.connect(dataTable);
				dataTable.sql.subscribe((sql) => {
					model.set(
						'_tables',
						tables.map((t) => {
							if (t._table_name === table._table_name) {
								return { ...t, sql: sql || '' };
							}
							return t;
						})
					);
					model.save_changes();
				});
				appTables[table._table_name] = {
					data: dataTable,
					schema: schema
				};
			}

			const app = mount(App, {
				target: el,
				props: { coordinator: coordinator, tables: appTables }
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
