import { setupServer } from "msw/node";
import { handlers } from "./handlers";

/** For Vitest/Playwright component tests that need the mock API server. */
export const server = setupServer(...handlers);
