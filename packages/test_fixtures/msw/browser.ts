import { setupWorker } from "msw/browser";
import { handlers } from "./handlers";

/** For apps/web: started from a client component behind NEXT_PUBLIC_USE_MSW. */
export const worker = setupWorker(...handlers);
