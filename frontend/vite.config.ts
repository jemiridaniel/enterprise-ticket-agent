import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "/enterprise-ticket-agent/", // <--- repo name here
});
