import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useDownloadStore } from "@/stores/download";
import type { Task, TaskStatus } from "@/stores/download";

// Capture the task:state listener the store registers, so tests can drive the
// real applyEvent path by dispatching events (rather than re-implementing it).
const h = vi.hoisted(() => ({ cb: null as null | ((e: { payload: { task: Task } }) => void) }));

vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn((_name: string, cb: (e: { payload: { task: Task } }) => void) => {
    h.cb = cb;
    return Promise.resolve(() => {}); // unlisten
  }),
}));

vi.mock("@tauri-apps/plugin-notification", () => ({
  sendNotification: vi.fn(),
  // Default: permission granted. Individual tests override with mockResolvedValue.
  isPermissionGranted: vi.fn(() => Promise.resolve(true)),
  requestPermission: vi.fn(() => Promise.resolve("granted")),
}));

vi.mock("@/ipc", () => ({
  // Mirror the real ok(): unwrap on status "ok", throw otherwise.
  ok: vi.fn(async (p: Promise<{ status: string; data?: unknown; error?: unknown }>) => {
    const r = await p;
    if (r.status === "ok") return r.data;
    throw new Error(String(r.error));
  }),
  commands: {
    snapshotTasks: vi.fn(() => Promise.resolve([] as Task[])),
    enqueueDownload: vi.fn(() => Promise.resolve({ status: "ok", data: null })),
    enqueueBatch: vi.fn((items: unknown[]) => Promise.resolve({ status: "ok", data: items.length })),
    cancelTask: vi.fn(() => Promise.resolve({ status: "ok", data: null })),
  },
  Event: { TASK_STATE: "task:state", DEP_UPDATE_PROGRESS: "dep:update-progress" },
}));

function makeTask(id: string, status: TaskStatus, over: Partial<Task> = {}): Task {
  return {
    id,
    status,
    params: { url: `https://example.com/${id}`, title: id } as Task["params"],
    percent: 0,
    speed: "",
    eta: "",
    seq: 0,
    ...over,
  };
}

// Flush microtasks + one macrotask tick so the async applyEvent (which awaits
// notifyTerminal) settles before assertions.
const flush = () => new Promise<void>(r => setTimeout(r, 0));

/** Dispatch a task:state event through the captured listener and let it settle. */
async function emit(task: Task) {
  h.cb?.({ payload: { task } });
  await flush();
}

async function grantNotifications(granted: boolean) {
  const { isPermissionGranted } = await import("@tauri-apps/plugin-notification");
  vi.mocked(isPermissionGranted).mockResolvedValue(granted);
}

describe("useDownloadStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    h.cb = null;
  });

  it("初始化时队列为空", () => {
    const store = useDownloadStore();
    expect(store.tasks).toEqual([]);
    expect(store.failedNotices).toEqual([]);
    expect(store.activeCount).toBe(0);
  });

  it("计算 pending 和 running 数量", () => {
    const store = useDownloadStore();
    store.tasks = [
      makeTask("1", "pending"),
      makeTask("2", "running", { percent: 50 }),
      makeTask("3", "running", { percent: 80 }),
    ];
    expect(store.pendingCount).toBe(1);
    expect(store.runningCount).toBe(2);
    expect(store.activeCount).toBe(3);
  });

  it("applyEvent 新增 running 任务", async () => {
    const store = useDownloadStore();
    await store.startListening();

    await emit(makeTask("t1", "running", { percent: 50 }));

    expect(store.tasks).toHaveLength(1);
    expect(store.tasks[0].id).toBe("t1");
    expect(store.tasks[0].status).toBe("running");
  });

  it("applyEvent 就地更新进度而不新增", async () => {
    const store = useDownloadStore();
    await store.startListening();

    await emit(makeTask("t1", "running", { percent: 10 }));
    await emit(makeTask("t1", "running", { percent: 75, speed: "2MB/s" }));

    expect(store.tasks).toHaveLength(1);
    expect(store.tasks[0].percent).toBe(75);
    expect(store.tasks[0].speed).toBe("2MB/s");
  });

  it("applyEvent 移除 complete 任务并发送通知", async () => {
    await grantNotifications(true);
    const { sendNotification } = await import("@tauri-apps/plugin-notification");
    const store = useDownloadStore();
    await store.startListening();

    await emit(makeTask("t1", "running", { percent: 99 }));
    expect(store.tasks).toHaveLength(1);

    await emit(makeTask("t1", "complete", { percent: 100 }));

    expect(store.tasks).toHaveLength(0);
    expect(store.failedNotices).toHaveLength(0);
    expect(sendNotification).toHaveBeenCalledTimes(1);
  });

  it("applyEvent 移除 cancelled 任务且不产生通知/notice", async () => {
    await grantNotifications(true);
    const { sendNotification } = await import("@tauri-apps/plugin-notification");
    const store = useDownloadStore();
    await store.startListening();

    await emit(makeTask("t1", "running"));
    await emit(makeTask("t1", "cancelled"));

    expect(store.tasks).toHaveLength(0);
    expect(store.failedNotices).toHaveLength(0);
    expect(sendNotification).not.toHaveBeenCalled();
  });

  it("failed 任务在通知不可用时进入 failedNotices", async () => {
    await grantNotifications(false);
    const store = useDownloadStore();
    await store.startListening();

    await emit(makeTask("bad", "failed", { percent: 30 }));

    expect(store.tasks).toHaveLength(0);
    expect(store.failedNotices).toHaveLength(1);
    expect(store.failedNotices[0].id).toBe("bad");
  });

  it("failed 任务在通知成功时不进入 failedNotices", async () => {
    await grantNotifications(true);
    const { sendNotification } = await import("@tauri-apps/plugin-notification");
    const store = useDownloadStore();
    await store.startListening();

    await emit(makeTask("bad", "failed", { percent: 30 }));

    expect(store.failedNotices).toHaveLength(0);
    expect(sendNotification).toHaveBeenCalledTimes(1);
  });

  it("failedNotices 上限 50（最早的被丢弃）", async () => {
    await grantNotifications(false);
    const store = useDownloadStore();
    await store.startListening();

    for (let i = 0; i < 51; i++) {
      await emit(makeTask(`f${i}`, "failed"));
    }

    expect(store.failedNotices).toHaveLength(50);
    expect(store.failedNotices[0].id).toBe("f1"); // f0 被挤出
  });

  it("dismissFailed 移除指定失败通知", () => {
    const store = useDownloadStore();
    store.failedNotices = [makeTask("a", "failed"), makeTask("b", "failed")];
    store.dismissFailed("a");
    expect(store.failedNotices).toHaveLength(1);
    expect(store.failedNotices[0].id).toBe("b");
  });

  it("setDroppedUrl 设置和清空 URL", () => {
    const store = useDownloadStore();
    expect(store.droppedUrl).toBeNull();
    store.setDroppedUrl("https://youtube.com/watch?v=abc");
    expect(store.droppedUrl).toBe("https://youtube.com/watch?v=abc");
    store.setDroppedUrl(null);
    expect(store.droppedUrl).toBeNull();
  });

  it("enqueue 调用后端命令", async () => {
    const store = useDownloadStore();
    const { commands } = await import("@/ipc");
    await store.enqueue({ url: "https://x/y", title: "t" } as never);
    expect(commands.enqueueDownload).toHaveBeenCalled();
  });

  it("enqueueBatch 批量入队并返回后端接受数量", async () => {
    const store = useDownloadStore();
    const { commands } = await import("@/ipc");
    const count = await store.enqueueBatch([
      { url: "https://x/1", title: "1" } as never,
      { url: "https://x/2", title: "2" } as never,
    ]);
    expect(commands.enqueueBatch).toHaveBeenCalled();
    expect(count).toBe(2);
  });

  it("cancel 调用后端取消命令", async () => {
    const store = useDownloadStore();
    const { commands } = await import("@/ipc");
    await store.cancel("task-123");
    expect(commands.cancelTask).toHaveBeenCalledWith("task-123");
  });
});
