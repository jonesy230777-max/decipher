import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, path.resolve(__dirname, ".."), "DECIPHER_");
  const webPort = Number(env.DECIPHER_WEB_PORT ?? 55173);
  const apiPort = Number(env.DECIPHER_API_PORT ?? 58080);
  return {
    plugins: [react()],
    server: {
      host: "127.0.0.1",
      port: webPort,
      strictPort: true,
      proxy: { "/api": `http://127.0.0.1:${apiPort}` },
    },
  };
});
