import * as mc from '@uwdata/mosaic-core';
import * as flech from '@uwdata/flechette';
import * as uuid from '@lukeed/uuid';

import { assert } from './assert';

import type * as aw from '@anywidget/types';

interface OpenQuery {
	query: mc.ArrowQueryRequest | mc.JSONQueryRequest | mc.ExecQueryRequest;
	startTime: number;
	resolve: (x: flech.Table | Record<string, unknown>) => void;
	reject: (err?: string) => void;
}

export function mosaicInitialise(coordinator: mc.Coordinator, model: aw.AnyModel): () => void {
	let logger = coordinator.logger(null);
	let openQueries = new Map<string, OpenQuery>();

	function send(
		query: mc.ArrowQueryRequest | mc.JSONQueryRequest | mc.ExecQueryRequest,
		resolve: (value: flech.Table | Record<string, unknown>) => void,
		reject: (reason?: string) => void
	): void {
		let id = uuid.v4();
		openQueries.set(id, {
			query,
			startTime: performance.now(),
			resolve,
			reject
		});
		model.send({ ...query, uuid: id });
	}

	model.on('msg:custom', (msg, buffers) => {
		logger.group(`query ${msg.uuid}`);
		logger.log('received message', msg, buffers);

		const query = openQueries.get(msg.uuid);
		assert(query, 'no open query');

		openQueries.delete(msg.uuid);

		logger.log(query.query.sql, (performance.now() - query.startTime).toFixed(1));
		if (msg.error) {
			query.reject(msg.error);
			logger.error(msg.error);
		} else {
			switch (msg.type) {
				case 'arrow': {
					const buffer = buffers[0].buffer;
					assert(buffer instanceof ArrayBuffer || buffer instanceof Uint8Array);
					const table = mc.decodeIPC(buffer);
					logger.log('table', table);
					query.resolve(table);
					break;
				}
				case 'json': {
					logger.log('json', msg.result);
					query.resolve(msg.result);
					break;
				}
				default: {
					query.resolve({});
					break;
				}
			}
		}
		logger.groupEnd();
	});

	coordinator.databaseConnector({
		query(query) {
			// deno-lint-ignore no-explicit-any
			return new Promise<any>((resolve, reject) => send(query, resolve, reject));
		}
	});
	coordinator.preaggregator.schema = 'mosaic';
	return () => {
		coordinator.clear();
	};
}
