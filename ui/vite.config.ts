import { defineConfig } from "vite";
import { resolve } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = resolve(__filename, "..");

export default defineConfig({
    resolve: {
        alias: {
            "@": resolve(__dirname, "./src"),
            "@app": resolve(__dirname, "./src/app"),
            "@core": resolve(__dirname, "./src/core"),
            "@ui": resolve(__dirname, "./src/ui")
        }
    },
    server: {
        port: 5173,
        open: true
    },
    build: {
        outDir: "dist",
        sourcemap: true
    }
});