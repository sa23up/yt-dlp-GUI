// Vitest global setup
import { beforeAll, afterEach, vi } from "vitest";

// Mock Tauri API
beforeAll(() => {
  global.window = global.window || ({} as any);
  (global.window as any).__TAURI_INTERNALS__ = {
    invoke: vi.fn(),
    listen: vi.fn(),
  };
});

// Clean up after each test
afterEach(() => {
  vi.clearAllMocks();
});
