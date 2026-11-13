import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";

import { ApiError } from "./api/client";
import { App } from "./App.tsx";
import "./i18n";
import "./index.css";

const container = document.getElementById("root");
if (container === null) {
  throw new Error("index.html has no #root element to render into");
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // A 4xx will not fix itself; a dropped connection on site often does.
      retry: (failures, error) => !(error instanceof ApiError && error.status < 500) && failures < 2,
      refetchOnWindowFocus: false,
    },
  },
});

function mockRemembered(): boolean {
  try {
    return window.sessionStorage.getItem("mjera.mock") !== null;
  } catch {
    return false;
  }
}

async function start(root: HTMLElement) {
  // Development only: `/?mock` serves engine-made sample data without a database; the tab
  // remembers it, so a reload on any page stays in the demo.
  if (import.meta.env.DEV && (new URLSearchParams(window.location.search).has("mock") || mockRemembered())) {
    const { installMock } = await import("./dev/mock");
    installMock();
  }
  createRoot(root).render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </QueryClientProvider>
    </StrictMode>,
  );
}

void start(container);
