<script setup lang="ts">
import { computed, onMounted, watch, ref } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter } from "vue-router";
import { darkTheme, lightTheme } from "naive-ui";
import { useSettingsStore } from "./stores/settings";
import { useDownloadStore } from "./stores/download";
import TopBar from "./components/TopBar.vue";
import Sidebar from "./components/Sidebar.vue";
import Icon from "./components/Icon.vue";
import "./assets/theme.css";

const { locale, t } = useI18n();
const router = useRouter();
const settings = useSettingsStore();
const download = useDownloadStore();
const dragOver = ref(false);
let dragOverTimer: ReturnType<typeof setTimeout> | null = null;
// US22: best-effort app-update check on startup. Holds the available version
// for a non-intrusive, dismissible banner. We never auto-download/install —
// the user installs from Settings → Update.
const updateAvailableV = ref<string | null>(null);

// Two-axis accent (Hybrid C):
// - BRAND = YouTube red — used only for download-semantic surfaces
//   (CTA, progress bar, running indicator, brand chip).
// - ACCENT = macOS systemBlue — used for navigation/selection
//   (selected row, focus ring, link, native form-control accent).
// Values mirror the per-theme tokens in src/assets/theme.css (dark uses the
// lifted variants per DS §1.1). When changing values, update theme.css too.
// We can't read CSS vars at theme-overrides eval time.
const BRAND = {
  dark:  { primary: "#FF2222", hover: "#FF4444", pressed: "#FF0F0F" },
  light: { primary: "#FF0000", hover: "#E60000", pressed: "#CC0000" },
} as const;
const ACCENT = {
  dark:  { primary: "#0A84FF", hover: "#1F8FFF", pressed: "#5AB0FF", halo: "rgba(10, 132, 255, 0.30)", borderHover: "rgba(10, 132, 255, 0.50)" },
  light: { primary: "#007AFF", hover: "#0066CC", pressed: "#0050A8", halo: "rgba(0, 122, 255, 0.30)", borderHover: "rgba(0, 122, 255, 0.50)" },
} as const;

const theme = computed(() => (settings.theme === "dark" ? darkTheme : lightTheme));
const themeOverrides = computed(() => {
  const brand = BRAND[settings.theme];
  const accent = ACCENT[settings.theme];
  return {
    common: {
      // naive-ui's "primary" drives selection / focus / slider / radio /
      // checkbox / select. Under Hybrid C those are NAVIGATION → ACCENT blue.
      primaryColor:        accent.primary,
      primaryColorHover:   accent.hover,
      primaryColorPressed: accent.pressed,
      primaryColorSuppl:   accent.hover,
      borderRadius: "10px",
    },
    // Progress is a download indicator → BRAND.
    Progress: { fillColor: brand.primary },
    // Tighten focus glow on inputs so it doesn't read as a "blue overlay" on
    // dark Settings cards. 2px halo at 30% alpha is the macOS norm.
    Input:    {
      boxShadowFocus: `0 0 0 2px ${accent.halo}`,
      borderFocus:   `1px solid ${accent.primary}`,
      borderHover:   `1px solid ${accent.borderHover}`,
    },
    InternalSelection: {
      boxShadowFocus: `0 0 0 2px ${accent.halo}`,
      borderFocus:    `1px solid ${accent.primary}`,
      borderHover:    `1px solid ${accent.borderHover}`,
    },
  };
});

const footerStatus = computed(() => {
  const running = download.runningCount;
  const pending = download.pendingCount;
  if (running === 0 && pending === 0) return t("app.ready");
  const parts: string[] = [];
  if (running) parts.push(t("app.downloads", { count: running }, running));
  if (pending) parts.push(t("app.pendingCount", { count: pending }));
  return parts.join(" · ");
});

onMounted(async () => {
  await settings.load(); // also pushes loaded concurrency to the Rust queue
  locale.value = settings.language;
  document.documentElement.lang = settings.language;
  await download.startListening();
  // queue restoration is owned by Rust (lib.rs setup hook); the frontend
  // hydrates via task:state events as Rust re-emits restored tasks.

  // US22: best-effort startup check for app updates. Non-intrusive — surfaces
  // a dismissible banner only; never auto-downloads/installs. Swallow all
  // errors so startup never breaks when offline.
  try {
    const { check } = await import("@tauri-apps/plugin-updater");
    const update = await check();
    if (update) updateAvailableV.value = update.version;
  } catch { /* ignore — offline / no updater configured */ }
});

// Apply the theme to <html> (not .shell) so the token overrides reach :root —
// where accent-color / color-scheme are declared — and any naive-ui layer
// teleported to <body> still resolves the right per-theme CSS variables.
watch(() => settings.theme, th => {
  document.documentElement.dataset.theme = th;
}, { immediate: true });

watch(() => settings.language, lang => {
  locale.value = lang;
  document.documentElement.lang = lang;
});

function extractUrl(e: DragEvent): string | null {
  const dt = e.dataTransfer;
  if (!dt) return null;
  // Prefer URI list, fall back to plain text.
  const uri = dt.getData("text/uri-list") || dt.getData("text/plain") || "";
  // text/uri-list format allows comment lines starting with '#' (RFC 2483)
  // Filter them out to avoid false positives
  const first = uri
    .split(/\r?\n/)
    .map(l => l.trim())
    .filter(l => l && !l.startsWith('#'))
    .find(l => /^https?:\/\//i.test(l));
  return first ?? null;
}
function onDragOver(e: DragEvent) {
  // Only show drop affordance if the drag contains plausible URL data.
  const types = e.dataTransfer?.types;
  if (!types || (!types.includes("text/plain") && !types.includes("text/uri-list"))) return;
  e.preventDefault();
  dragOver.value = true;
  if (dragOverTimer) clearTimeout(dragOverTimer);
  dragOverTimer = setTimeout(() => { dragOver.value = false; }, 400);
}
function onDragLeave() { dragOver.value = false; }
function onDrop(e: DragEvent) {
  e.preventDefault();
  dragOver.value = false;
  const url = extractUrl(e);
  if (!url) return;
  // Route to Home so the dropped URL has a UI surface to land on.
  if (router.currentRoute.value.name !== "home") {
    router.push({ name: "home", query: { filter: "all" } });
  }
  download.setDroppedUrl(url);
}
</script>

<template>
  <n-config-provider :theme="theme" :theme-overrides="themeOverrides">
    <n-message-provider>
      <div class="shell"
           @dragover="onDragOver"
           @dragleave="onDragLeave"
           @drop="onDrop">
        <a class="sr-only focusable" href="#main">{{ t("a11y.skipToMain") }}</a>
        <TopBar />
        <div class="middle">
          <Sidebar />
          <main id="main" class="content" tabindex="-1">
            <n-alert
              v-if="updateAvailableV"
              type="info"
              closable
              class="update-banner"
              @close="updateAvailableV = null"
            >
              {{ t("app.updateAvailable", { v: updateAvailableV }) }}
            </n-alert>
            <router-view />
          </main>
        </div>
        <footer class="footer">
          <span>{{ footerStatus }}</span>
          <span class="dir">
            <Icon name="folder" :size="12" />
            <span>{{ settings.downloadDir || '~/Downloads' }}</span>
          </span>
        </footer>
        <Transition name="drop">
          <div v-if="dragOver" class="drop-overlay" aria-hidden="true">
            <div class="drop-overlay-inner">
              <Icon name="download" :size="32" />
              <div>{{ t("home.dropHint") }}</div>
            </div>
          </div>
        </Transition>
      </div>
    </n-message-provider>
  </n-config-provider>
</template>

<style scoped>
.shell {
  position: relative;
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg-base);
}
.shell::after {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: var(--noise-bg);
  /* Sits just above the base background as a faint film-grain texture. Kept
     low (not above interactive overlays) and WITHOUT mix-blend-mode, which
     would shift every color beneath it — including the calibrated brand/accent
     palette. Teleported layers (naive popovers/dialogs) render in <body>, so
     they're intentionally outside this texture. */
  z-index: 1;
}
.middle {
  display: flex;
  flex: 1;
  overflow: hidden;
}
.content {
  flex: 1;
  overflow: auto;
  padding: 24px 40px 40px;
  outline: none;
}
/* 响应式：当窗口小于 900px 时，缩小左右留白，为内容争取空间 */
@media (max-width: 900px) {
  .content { padding: 20px 24px 24px; }
}
/* 响应式：当窗口极窄时（类似手机比例），进一步压缩留白 */
@media (max-width: 600px) {
  .content { padding: 16px; }
}
.update-banner {
  max-width: 820px;
  margin: 0 auto 16px;
}
.footer {
  display: flex; align-items: center; justify-content: space-between;
  gap: 16px;
  padding: 6px 24px;
  height: 32px;
  box-sizing: border-box;
  background: var(--bg-sidebar);
  border-top: 1px solid var(--border);
  font-size: 11px;
  color: var(--text-2); /* upgraded from text-3 — A11Y-1 contrast */
}
.footer > span:first-of-type {
  flex: 1;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.dir {
  display: inline-flex; align-items: center; gap: 6px;
  flex-shrink: 0;
  max-width: 60%;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.dir > span:last-child {
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.drop-overlay {
  position: absolute;
  inset: 0;
  background: var(--accent-soft);
  border: 2px dashed var(--accent);
  display: flex; align-items: center; justify-content: center;
  pointer-events: none;
  z-index: 1000;
}
.drop-overlay-inner {
  display: flex; flex-direction: column; align-items: center; gap: 10px;
  color: var(--accent);
  font-size: 14px; font-weight: 600;
}
.drop-enter-active, .drop-leave-active { transition: opacity var(--dur-fast) var(--ease-default); }
.drop-enter-from, .drop-leave-to { opacity: 0; }
</style>
