import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App.tsx";
import "./index.css";

const container = document.getElementById("root");
if (container === null) {
  throw new Error("index.html has no #root element to render into");
}

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
