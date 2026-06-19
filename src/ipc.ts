/**
 * tauri-specta wraps every Result<T, E> Rust command into a discriminated
 * union { status: "ok"; data: T } | { status: "error"; error: E }.
 * Our existing call sites use `await invoke(...)` + try/catch, so we unwrap
 * here and re-throw on error to keep the surface ergonomic.
 */

type Result<T, E> = { status: "ok"; data: T } | { status: "error"; error: E };

export async function ok<T, E>(p: Promise<Result<T, E>>): Promise<T> {
  const r = await p;
  if (r.status === "ok") return r.data;
  throw new Error(typeof r.error === "string" ? r.error : JSON.stringify(r.error));
}

export { commands } from "./bindings";
export type {
  AppSettings,
  DownloadParams,
  ErrorKind,
  FormatInfo,
  FormatList,
  QueueEntry,
  Task,
  TaskStatus,
} from "./bindings";

/** Event names — tauri-specta doesn't generate these because we didn't
 *  define Rust event structs.  Centralized here to keep the contract honest. */
export const Event = {
  TASK_STATE: "task:state",
  DEP_UPDATE_PROGRESS: "dep:update-progress",
} as const;
