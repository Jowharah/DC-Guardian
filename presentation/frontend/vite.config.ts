import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
// Ports can be overridden when 5173 or 8000 are taken: DCG_FRONTEND_PORT, DCG_BACKEND_URL.
const env = (globalThis as { process?: { env: Record<string, string | undefined> } }).process?.env ?? {};
export default defineConfig({plugins:[react()],server:{host:"127.0.0.1",port:Number(env.DCG_FRONTEND_PORT ?? 5173),strictPort:true,proxy:{"/api":env.DCG_BACKEND_URL ?? "http://127.0.0.1:8000"}}});
