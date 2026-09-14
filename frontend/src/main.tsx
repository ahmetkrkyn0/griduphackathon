// Yazi tipleri npm paketinden: calisma aninda internet gerekmez (GK4). Turkce karakterler latin-ext alt kumesinde.
// Tek font ailesi (Barlow + Barlow Semi Condensed, ayni ailenin iki genisligi) — kullanici talebi.
import "@fontsource/barlow/400.css";
import "@fontsource/barlow/500.css";
import "@fontsource/barlow/600.css";
import "@fontsource/barlow-semi-condensed/500.css";
import "@fontsource/barlow-semi-condensed/600.css";
import "@fontsource/barlow-semi-condensed/700.css";
import "@fontsource/barlow-semi-condensed/800.css";
import "./theme.css";
import "./app.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";

const root = document.getElementById("root");
if (!root) throw new Error("#root elemanı bulunamadı");

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
