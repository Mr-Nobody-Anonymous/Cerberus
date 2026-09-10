import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { cssVariables } from "@/styles/tokens";
import "@/styles/global.css";

// Inject design tokens as CSS custom properties.
const style = document.createElement("style");
style.textContent = cssVariables;
document.head.appendChild(style);

// Spinner keyframes (used by Basics.tsx).
const spin = document.createElement("style");
spin.textContent = `@keyframes cb-spin { to { transform: rotate(360deg); } }`;
document.head.appendChild(spin);

import App from "@/App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
