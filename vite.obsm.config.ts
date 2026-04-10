import tailwindcss from '@tailwindcss/vite';
import { defineConfig, type UserConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import path from 'path';

export const baseConfig: UserConfig = {
    resolve: {
        alias: {
            $lib: path.resolve("./src/lib").replaceAll("\\", "/"),
        },
    },
    plugins: [tailwindcss(), svelte()],
    build: {
        assetsDir: '',
		outDir: './py/corr_vars_widget/static/',
        lib: {
            entry: ["./src/obsm.ts"],
            cssFileName: "main",
            formats: ["es"],
        },
		rollupOptions: {
			output: {
				entryFileNames: `[name].js`,
				chunkFileNames: `[name].js`,
				assetFileNames: `[name].[ext]`,
			},
            preserveEntrySignatures: "allow-extension"
		}
	}
}

// https://vite.dev/config/
export default defineConfig(baseConfig);
