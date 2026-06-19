import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import {
  sendNotification,
  isPermissionGranted,
  requestPermission,
} from "@tauri-apps/plugin-notification";
import { commands, ok, Event, type Task, type DownloadParams } from "../ipc";
import i18n from "../i18n";

export type { Task, DownloadParams };
export type TaskParams = DownloadParams; // legacy alias used by views/components
export type TaskStatus = Task["status"];

let idSeq = 0;
function nextId() {
  return `t_${Date.now().toString(36)}_${++idSeq}`;
}

export const useDownloadStore = defineStore("download", () => {
  const tasks = ref<Task[]>([]);   // pending + running + paused
  // Shared count getters so TopBar / Sidebar / App / footer don't each re-filter.
  const runningCount = computed(() => tasks.value.filter(t => t.status === "running").length);
  const pendingCount = computed(() => tasks.value.filter(t => t.status === "pending").length);
  const pausedCount = computed(() => tasks.value.filter(t => t.status === "paused").length);
  // "Active" = any unfinished task, paused included (it's still in the queue).
  const activeCount = computed(() => runningCount.value + pendingCount.value + pausedCount.value);
  /** Failed tasks surfaced in-app as a fallback when system notifications
   *  can't fire (permission denied). Otherwise a failure would vanish silently
   *  since terminal tasks are dropped from `tasks` (ADR 0004). */
  const failedNotices = ref<Task[]>([]);
  /** App.vue writes a URL here when the user drops one onto the window;
   *  HomeView watches and submits.  null after consumption. */
  const droppedUrl = ref<string | null>(null);
  function setDroppedUrl(u: string | null) { droppedUrl.value = u; }

  function dismissFailed(id: string) {
    const i = failedNotices.value.findIndex(t => t.id === id);
    if (i >= 0) failedNotices.value.splice(i, 1);
  }

  let unlisten: UnlistenFn | null = null;
  /** In-flight / completed startListening call. Set synchronously so two
   *  concurrent callers can't both register a listener (the guard used to be
   *  `unlisten`, which is only assigned after several awaits). */
  let startPromise: Promise<void> | null = null;

  function findIndex(id: string) { return tasks.value.findIndex(t => t.id === id); }

  /** Request notification permission once, best-effort. Whether to actually
   *  show a notification is re-checked per event in notifyTerminal, so granting
   *  permission mid-session (e.g. via Settings) takes effect without restart. */
  async function ensureNotificationPermission(): Promise<void> {
    try {
      if (!(await isPermissionGranted())) await requestPermission();
    } catch { /* ignore — best-effort */ }
  }
  /** Show a terminal notification if permission is currently granted; returns
   *  whether it fired. Re-checks permission on every call (no stale cache). */
  async function notifyTerminal(t: Task): Promise<boolean> {
    let granted = false;
    try { granted = await isPermissionGranted(); } catch { granted = false; }
    if (!granted) return false;
    // Use the app's selected locale (kept in sync with settings.language in
    // App.vue) rather than navigator.language, so notifications match the UI.
    const done = t.status === "complete";
    const label = i18n.global.t(done ? "home.notifyComplete" : "home.notifyFailed");
    const title = `${done ? "✓" : "✗"} ${label}`;
    const body = t.params.title || t.params.url;
    try {
      sendNotification({ title, body });
    } catch { return false; }
    return true;
  }

  function startListening(): Promise<void> {
    if (startPromise) return startPromise;
    startPromise = doStartListening().catch(err => {
      // Allow a retry on failure instead of latching a broken state.
      startPromise = null;
      throw err;
    });
    return startPromise;
  }

  /** Apply one task:state event to the live list. */
  async function applyEvent(t: Task) {
    const i = findIndex(t.id);
    const isTerminal = t.status === "complete" || t.status === "failed" || t.status === "cancelled";
    if (!isTerminal) {
      if (i >= 0) tasks.value[i] = t;
      else tasks.value.push(t);
      return;
    }
    if (i >= 0) tasks.value.splice(i, 1);
    if (t.status === "cancelled") return;
    const notified = await notifyTerminal(t);
    // If the notification couldn't fire, a failure would vanish silently —
    // keep an in-app notice so the user still learns the download failed.
    if (t.status === "failed" && !notified) {
      failedNotices.value.push(t);
      if (failedNotices.value.length > 50) failedNotices.value.shift();
    }
  }

  async function doStartListening() {
    await ensureNotificationPermission();

    // Clear any stale state from previous session (HMR / dev refresh)
    // to prevent duplicates when syncing with backend
    tasks.value = [];
    failedNotices.value = [];

    // Subscribe FIRST (buffering events), then hydrate from the snapshot and
    // replay the buffer on top. This closes both race windows:
    //  - snapshot-then-listen: a terminal event arriving before the listener
    //    registers would be lost and the task stuck as running forever;
    //  - listen-then-replace: an event applied while snapshotTasks() is in
    //    flight would be clobbered by the full `tasks.value = live` assignment.
    let buffer: Task[] | null = [];
    unlisten = await listen<{ task: Task }>(Event.TASK_STATE, e => {
      const t = e.payload.task;
      if (buffer) buffer.push(t);
      else void applyEvent(t);
    });
    try {
      const live = await commands.snapshotTasks();
      if (Array.isArray(live)) {
        tasks.value = live;
      }
    } catch { /* ignore */ }
    const queued = buffer;
    buffer = null;
    for (const t of queued!) await applyEvent(t);
  }

  function stopListening() {
    if (unlisten) { unlisten(); unlisten = null; }
    startPromise = null;
  }

  async function enqueue(params: DownloadParams): Promise<string> {
    const id = nextId();
    await ok(commands.enqueueDownload(id, params));
    return id;
  }

  /** Enqueue many tasks in one IPC round-trip (playlist / multi-URL paste).
   *  Returns the count the backend accepted. */
  async function enqueueBatch(paramsList: DownloadParams[]): Promise<number> {
    const items = paramsList.map(params => ({ id: nextId(), params }));
    return await ok(commands.enqueueBatch(items));
  }

  async function cancel(id: string) {
    await ok(commands.cancelTask(id));
  }

  async function pause(id: string) {
    await ok(commands.pauseTask(id));
  }

  async function resume(id: string) {
    await ok(commands.resumeTask(id));
  }

  return {
    tasks, failedNotices, droppedUrl,
    runningCount, pendingCount, activeCount,
    startListening, stopListening,
    enqueue, enqueueBatch, cancel, pause, resume,
    setDroppedUrl, dismissFailed,
  };
});
