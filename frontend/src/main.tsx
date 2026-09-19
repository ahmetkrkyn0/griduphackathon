// Yazi tipleri npm paketinden: calisma aninda internet gerekmez (GK4). Turkce karakterler latin-ext alt kumesinde.
// Tek font ailesi (Barlow) — kullanici talebi.
import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "@fontsource/inter/700.css";
import "./theme.css";
import "./app.css";
import "./workspace.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./industrial.css";

const root = document.getElementById("root");
if (!root) throw new Error("#root elemanı bulunamadı");

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
