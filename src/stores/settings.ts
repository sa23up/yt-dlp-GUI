import { defineStore } from "pinia";
import { ref, watch, nextTick } from "vue";
import { commands, ok, type AppSettings } from "../ipc";

export type Theme = "dark" | "light";
export type Locale = "zh-CN" | "en";
export type CookieSource = "none" | "firefox" | "chrome" | "edge" | "file";
export type CodecPref = "any" | "h264" | "vp9" | "av1";

export const useSettingsStore = defineStore("settings", () => {
  const theme = ref<Theme>("dark");
  const language = ref<Locale>(navigator.language.startsWith("zh") ? "zh-CN" : "en");
  const downloadDir = ref("");
  const filenameTemplate = ref("%(title)s.%(ext)s");
  const concurrency = ref(2);
  const cookieSource = ref<CookieSource>("none");
  const cookieFilePath = ref("");
  const proxy = ref("");
  const rateLimit = ref("");
  const preferredCodec = ref<CodecPref>("any");
  const maxHeight = ref<number>(0); // 0 = any

  function toggleTheme() { theme.value = theme.value === "dark" ? "light" : "dark"; }
  function setLanguage(lang: Locale) { language.value = lang; }

  /** True while load() hydrates the refs from disk — the persistence watcher
   *  skips those mutations, otherwise every app start writes the settings file
   *  right back. Cleared after nextTick so the (pre-flush) watcher still sees it. */
  let hydrating = false;

  async function load() {
    hydrating = true;
    try {
      const s = await ok(commands.loadSettings());
      if (s.theme === "dark" || s.theme === "light") theme.value = s.theme;
      if (s.language === "zh-CN" || s.language === "en") language.value = s.language;
      if (typeof s.downloadDir === "string") downloadDir.value = s.downloadDir;
      if (typeof s.filenameTemplate === "string" && s.filenameTemplate.trim()) {
        filenameTemplate.value = s.filenameTemplate;
      }
      if (typeof s.concurrency === "number" && s.concurrency > 0) {
        concurrency.value = Math.max(1, Math.min(5, Math.round(s.concurrency)));
      }
      if (
        s.cookieSource === "none" || s.cookieSource === "firefox" ||
        s.cookieSource === "chrome" || s.cookieSource === "edge" ||
        s.cookieSource === "file"
      ) cookieSource.value = s.cookieSource as CookieSource;
      if (typeof s.cookieFilePath === "string") cookieFilePath.value = s.cookieFilePath;
      if (typeof s.proxy === "string") proxy.value = s.proxy;
      if (typeof s.rateLimit === "string") rateLimit.value = s.rateLimit;
      if (
        s.preferredCodec === "any" || s.preferredCodec === "h264" ||
        s.preferredCodec === "vp9" || s.preferredCodec === "av1"
      ) preferredCodec.value = s.preferredCodec as CodecPref;
      if (typeof s.maxHeight === "number" && [0, 720, 1080, 1440, 2160].includes(s.maxHeight)) {
        maxHeight.value = s.maxHeight;
      }
    } catch (e) {
      console.warn("settings load failed:", e);
    } finally {
      await nextTick();
      hydrating = false;
    }
    // The loaded concurrency still has to reach the Rust queue (hydration
    // skipped the watcher on purpose); this is IPC-only, no file write.
    await pushToRust();
  }

  function asAppSettings(): AppSettings {
    return {
      theme: theme.value,
      language: language.value,
      downloadDir: downloadDir.value,
      filenameTemplate: filenameTemplate.value,
      concurrency: concurrency.value,
      cookieSource: cookieSource.value,
      cookieFilePath: cookieFilePath.value,
      proxy: proxy.value,
      rateLimit: rateLimit.value,
      preferredCodec: preferredCodec.value,
      maxHeight: maxHeight.value,
    };
  }

  /** Push concurrency to the Rust queue. No file I/O. */
  async function pushToRust() {
    await commands.setConcurrency(concurrency.value).catch(() => {});
  }

  let saveTimer: ReturnType<typeof setTimeout> | null = null;

  async function persist() {
    try {
      await ok(commands.saveSettings(asAppSettings()));
    } catch (e) {
      console.warn("settings save failed:", e);
    }
    await pushToRust();
  }

  function scheduleSave() {
    if (hydrating) return;
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(persist, 500);
  }

  /** The 500ms debounce loses a change made right before the window closes —
   *  flush any pending save immediately. Best-effort: the IPC message is
   *  posted before webview teardown. */
  function flushPendingSave() {
    if (saveTimer) {
      clearTimeout(saveTimer);
      saveTimer = null;
      void persist();
    }
  }
  window.addEventListener("beforeunload", flushPendingSave);

  watch(
    [theme, language, downloadDir, filenameTemplate, concurrency,
     cookieSource, cookieFilePath, proxy, rateLimit,
     preferredCodec, maxHeight],
    () => scheduleSave(),
  );

  return {
    theme, language, downloadDir, filenameTemplate, concurrency,
    cookieSource, cookieFilePath, proxy, rateLimit,
    preferredCodec, maxHeight,
    toggleTheme, setLanguage, load, persist, pushToRust,
  };
});
