<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from "vue";
import { useI18n } from "vue-i18n";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import { open } from "@tauri-apps/plugin-dialog";
import { isPermissionGranted, requestPermission } from "@tauri-apps/plugin-notification";
import { useSettingsStore, type Locale, type CookieSource, type CodecPref } from "../stores/settings";
import { commands, ok, Event } from "../ipc";
import type { Update } from "@tauri-apps/plugin-updater";
import Icon from "../components/Icon.vue";

const { t, locale } = useI18n();
const settings = useSettingsStore();

const currentTab = ref<"general" | "network" | "appearance" | "notifications" | "about">("general");

/** Tablist container, used to move DOM focus to the newly-selected tab when the
 *  user arrow-keys between tabs (WAI-ARIA roving-tabindex pattern). */
const tablistRef = ref<HTMLElement | null>(null);
function onTabKeydown(e: KeyboardEvent, idx: number) {
  const handled = ["ArrowDown", "ArrowUp", "ArrowRight", "ArrowLeft", "Home", "End"];
  if (!handled.includes(e.key)) return;
  e.preventDefault();
  let next = idx;
  if (e.key === "ArrowDown" || e.key === "ArrowRight") next = (idx + 1) % tabs.length;
  else if (e.key === "ArrowUp" || e.key === "ArrowLeft") next = (idx - 1 + tabs.length) % tabs.length;
  else if (e.key === "Home") next = 0;
  else if (e.key === "End") next = tabs.length - 1;
  currentTab.value = tabs[next].id;
  tablistRef.value?.querySelectorAll<HTMLElement>('[role="tab"]')[next]?.focus();
}

function switchLang(lang: Locale) {
  settings.setLanguage(lang);
  locale.value = lang;
}

async function pickDir() {
  try {
    const dir = await open({ directory: true });
    if (typeof dir === "string") settings.downloadDir = dir;
  } catch { /* dialog dismissed or unavailable */ }
}
async function pickCookieFile() {
  try {
    const f = await open({ filters: [{ name: "Cookies", extensions: ["txt"] }] });
    if (typeof f === "string") settings.cookieFilePath = f;
  } catch { /* dialog dismissed or unavailable */ }
}

const ytdlpV = ref(""), checking = ref(false), updating = ref(false);
const updPct = ref(0), newV = ref(""), updErr = ref("");
const uiV = ref(""), chkUi = ref(false), uiNewV = ref(""), uiInstalled = ref(false);
const ytdlpInstalled = ref(true);
const ffmpegV = ref(""), denoV = ref("");
const notificationPermission = ref<"granted" | "denied" | "default">("default");

let unlistenProgress: UnlistenFn | null = null;

async function checkNotificationPermission() {
  try {
    const granted = await isPermissionGranted();
    notificationPermission.value = granted ? "granted" : "default";
  } catch {
    notificationPermission.value = "default";
  }
}

async function requestNotificationPermission() {
  try {
    const result = await requestPermission();
    notificationPermission.value = result;
  } catch {
    notificationPermission.value = "denied";
  }
}

onMounted(async () => {
  await checkNotificationPermission();
  await Promise.all([
    (async () => {
      try {
        ytdlpV.value = await ok(commands.checkYtdlpVersionCmd());
        ytdlpInstalled.value = true;
      } catch {
        ytdlpV.value = t("err.notInstalled");
        ytdlpInstalled.value = false;
      }
    })(),
    (async () => {
      try { ffmpegV.value = await ok(commands.checkFfmpegVersionCmd()); }
      catch { ffmpegV.value = t("err.notInstalled"); }
    })(),
    (async () => {
      try { denoV.value = await ok(commands.checkDenoVersionCmd()); }
      catch { denoV.value = t("err.notInstalled"); }
    })(),
    (async () => {
      try {
        const { getVersion } = await import("@tauri-apps/api/app");
        uiV.value = await getVersion();
      } catch { uiV.value = "0.1.0"; }
    })(),
  ]);
  unlistenProgress = await listen<{ percent: number }>(
    Event.DEP_UPDATE_PROGRESS,
    e => { updPct.value = e.payload.percent; },
  );
});

onUnmounted(() => { unlistenProgress?.(); });

function isNewer(latest: string, current: string): boolean {
  const parse = (v: string) => v.trim().split(".").map(p => Number.parseInt(p, 10));
  const a = parse(latest), b = parse(current);
  if (!a.length || !b.length || a.some(Number.isNaN) || b.some(Number.isNaN)) {
    return latest.trim() !== current.trim();
  }
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    const x = a[i] ?? 0, y = b[i] ?? 0;
    if (x !== y) return x > y;
  }
  return false;
}

async function chkYt() {
  checking.value = true; updErr.value = ""; newV.value = "";
  try {
    const latest = await ok(commands.checkLatestReleaseCmd());
    if (latest && ytdlpInstalled.value && isNewer(latest, ytdlpV.value)) newV.value = latest;
  } catch (e) { updErr.value = String(e); }
  finally { checking.value = false; }
}
async function doUpd() {
  updating.value = true; updPct.value = 0; updErr.value = "";
  try {
    await ok(commands.downloadYtdlpUpdateCmd());
    newV.value = "";
    try { ytdlpV.value = await ok(commands.checkYtdlpVersionCmd()); } catch { }
  }
  catch (e) { updErr.value = String(e); }
  finally { updating.value = false; }
}

let pendingUiUpdate: Update | null = null;
async function chkUiUpd() {
  chkUi.value = true; updErr.value = ""; uiInstalled.value = false;
  try {
    const { check } = await import("@tauri-apps/plugin-updater");
    pendingUiUpdate = await check();
    uiNewV.value = pendingUiUpdate ? pendingUiUpdate.version : "";
  } catch (e) { updErr.value = String(e); }
  finally { chkUi.value = false; }
}
async function installUiUpd() {
  if (!pendingUiUpdate) return;
  try {
    await pendingUiUpdate.downloadAndInstall();
    uiInstalled.value = true;
    uiNewV.value = "";
    pendingUiUpdate = null;
  } catch (e) { updErr.value = String(e); }
}

const cookieOptions = [
  { value: "none",    labelKey: "settings.cookieNone" },
  { value: "firefox", labelKey: "settings.cookieFirefox" },
  { value: "chrome",  labelKey: "settings.cookieChrome" },
  { value: "edge",    labelKey: "settings.cookieEdge" },
  { value: "file",    labelKey: "settings.cookieManual" },
] as const;

const codecOptions: { value: CodecPref; label: string }[] = [
  { value: "any",  label: "settings.codecAny" },
  { value: "h264", label: "H.264" },
  { value: "vp9",  label: "VP9" },
  { value: "av1",  label: "AV1" },
];

const heightOptions: { value: number; label: string }[] = [
  { value: 0,    label: "settings.resAny" },
  { value: 720,  label: "720p" },
  { value: 1080, label: "1080p" },
  { value: 1440, label: "1440p" },
  { value: 2160, label: "2160p (4K)" },
];

const filenamePresets = [
  { labelKey: "settings.tplStandard",   value: "%(title)s.%(ext)s" },
  { labelKey: "settings.tplByUploader", value: "%(uploader)s/%(title)s.%(ext)s" },
  { labelKey: "settings.tplByDate",     value: "%(upload_date)s · %(title)s.%(ext)s" },
  { labelKey: "settings.tplPlaylist",   value: "%(playlist_title|na)s/%(playlist_index)03d - %(title)s.%(ext)s" },
];

const proxyError = computed(() => {
  const v = settings.proxy.trim();
  if (!v) return "";
  return /^(?:https?|socks4a?|socks5h?):\/\/\S+$/i.test(v) ? "" : t("settings.proxyInvalid");
});
const rateLimitError = computed(() => {
  const v = settings.rateLimit.trim();
  if (!v) return "";
  return /^\d+(?:\.\d+)?[KMG]?$/i.test(v) ? "" : t("settings.rateLimitInvalid");
});

const tabs = [
  { id: "general", icon: "sliders", labelKey: "settings.general" },
  { id: "network", icon: "globe", labelKey: "settings.network" },
  { id: "appearance", icon: "sun", labelKey: "settings.appearance" },
  { id: "notifications", icon: "bell", labelKey: "settings.notifications" },
  { id: "about", icon: "info", labelKey: "settings.update" },
] as const;

</script>

<template>
  <div class="settings-layout">
    <h1 class="sr-only">{{ t("a11y.pageSettings") }}</h1>

    <div
      class="settings-sidebar"
      ref="tablistRef"
      role="tablist"
      aria-orientation="vertical"
      :aria-label="t('a11y.pageSettings')"
    >
      <button
        v-for="(tab, idx) in tabs"
        :key="tab.id"
        :id="`tab-${tab.id}`"
        type="button"
        role="tab"
        :aria-selected="currentTab === tab.id"
        :aria-controls="`panel-${tab.id}`"
        :tabindex="currentTab === tab.id ? 0 : -1"
        class="tab-btn"
        :class="{ active: currentTab === tab.id }"
        @click="currentTab = tab.id"
        @keydown="onTabKeydown($event, idx)"
      >
        <Icon :name="tab.icon" :size="16" />
        <span>{{ t(tab.labelKey) }}</span>
      </button>
    </div>

    <div class="settings-content">
      <Transition name="pane" mode="out-in">
      <!-- General Tab -->
      <div
        v-if="currentTab === 'general'"
        key="general" id="panel-general" role="tabpanel"
        aria-labelledby="tab-general" tabindex="0" class="tab-pane"
      >
        <section class="card">
          <h2>{{ t("settings.general") }}</h2>
          <div class="field">
            <label for="set-download-dir">{{ t("settings.downloadDir") }}</label>
            <div class="inline">
              <n-input id="set-download-dir" v-model:value="settings.downloadDir" placeholder="~/Downloads" />
              <button class="btn-secondary" @click="pickDir">{{ t("settings.pickDir") }}</button>
            </div>
          </div>
          <div class="field">
            <label for="set-filename-template">{{ t("settings.filenameTemplate") }}</label>
            <n-input id="set-filename-template" v-model:value="settings.filenameTemplate" />
            <div class="presets">
              <button
                v-for="p in filenamePresets" :key="p.value"
                type="button"
                class="preset"
                :class="{ active: settings.filenameTemplate === p.value }"
                :aria-pressed="settings.filenameTemplate === p.value"
                @click="settings.filenameTemplate = p.value"
              >
                {{ t(p.labelKey) }}
              </button>
            </div>
            <div class="helper">{{ t("settings.filenameHint") }}</div>
          </div>
          <div class="field">
            <label for="set-concurrency">{{ t("settings.concurrency") }}: <span class="num">{{ settings.concurrency }}</span></label>
            <div id="set-concurrency" class="segmented" role="radiogroup" :aria-label="t('settings.concurrency')">
              <button
                v-for="n in 5" :key="n"
                type="button"
                class="seg"
                :class="{ active: settings.concurrency === n }"
                :aria-pressed="settings.concurrency === n"
                @click="settings.concurrency = n"
              >{{ n }}</button>
            </div>
          </div>
        </section>

        <section class="card">
          <h2>{{ t("settings.format") }}</h2>
          <div class="field">
            <label for="set-codec">{{ t("settings.preferredCodec") }}</label>
            <n-select
              id="set-codec"
              v-model:value="settings.preferredCodec"
              :options="codecOptions.map(o => ({ value: o.value, label: o.label.startsWith('settings.') ? t(o.label) : o.label }))"
            />
          </div>
          <div class="field">
            <label for="set-height">{{ t("settings.maxHeight") }}</label>
            <n-select
              id="set-height"
              v-model:value="settings.maxHeight"
              :options="heightOptions.map(o => ({ value: o.value, label: o.label.startsWith('settings.') ? t(o.label) : o.label }))"
            />
          </div>
        </section>
      </div>

      <!-- Network Tab -->
      <div
        v-else-if="currentTab === 'network'"
        key="network" id="panel-network" role="tabpanel"
        aria-labelledby="tab-network" tabindex="0" class="tab-pane"
      >
        <section class="card">
          <h2>{{ t("settings.cookie") }}</h2>
          <div class="field">
            <label for="set-cookie-source">{{ t("settings.cookieSource") }}</label>
            <n-select
              id="set-cookie-source"
              v-model:value="settings.cookieSource"
              :options="cookieOptions.map(o => ({ value: o.value as CookieSource, label: t(o.labelKey) }))"
            />
          </div>
          <div v-if="settings.cookieSource === 'file'" class="field">
            <label for="set-cookie-file">{{ t("settings.cookieFile") }}</label>
            <div class="inline">
              <n-input id="set-cookie-file" v-model:value="settings.cookieFilePath" />
              <button class="btn-secondary" @click="pickCookieFile">{{ t("settings.pickCookieFile") }}</button>
            </div>
          </div>
          <div class="helper">{{ t("settings.cookieHint") }}</div>
        </section>

        <section class="card">
          <h2>{{ t("settings.network") }}</h2>
          <div class="field">
            <label for="set-proxy">{{ t("settings.proxy") }}</label>
            <n-input id="set-proxy" v-model:value="settings.proxy" placeholder="http://127.0.0.1:7890" />
            <div v-if="proxyError" class="field-error">{{ proxyError }}</div>
          </div>
          <div class="field">
            <label for="set-rate">{{ t("settings.rateLimit") }}</label>
            <n-input id="set-rate" v-model:value="settings.rateLimit" placeholder="1M" />
            <div v-if="rateLimitError" class="field-error">{{ rateLimitError }}</div>
          </div>
        </section>
      </div>

      <!-- Appearance Tab -->
      <div
        v-else-if="currentTab === 'appearance'"
        key="appearance" id="panel-appearance" role="tabpanel"
        aria-labelledby="tab-appearance" tabindex="0" class="tab-pane"
      >
        <section class="card">
          <h2>{{ t("settings.appearance") }}</h2>
          <n-radio-group v-model:value="settings.theme">
            <n-radio value="dark">{{ t("settings.themeDark") }}</n-radio>
            <n-radio value="light">{{ t("settings.themeLight") }}</n-radio>
          </n-radio-group>
        </section>

        <section class="card">
          <h2>{{ t("settings.language") }}</h2>
          <n-radio-group v-model:value="settings.language" @update:value="switchLang">
            <n-radio value="zh-CN">{{ t("settings.langZh") }}</n-radio>
            <n-radio value="en">{{ t("settings.langEn") }}</n-radio>
          </n-radio-group>
        </section>
      </div>

      <!-- Notifications Tab -->
      <div
        v-else-if="currentTab === 'notifications'"
        key="notifications" id="panel-notifications" role="tabpanel"
        aria-labelledby="tab-notifications" tabindex="0" class="tab-pane"
      >
        <section class="card">
          <h2>{{ t("settings.notifications") }}</h2>
          <div class="field">
            <label>{{ t("settings.notificationStatus") }}</label>
            <div class="notification-status">
              <span v-if="notificationPermission === 'granted'" class="status-badge granted">
                ✓ {{ t("settings.notificationGranted") }}
              </span>
              <span v-else-if="notificationPermission === 'denied'" class="status-badge denied">
                ✗ {{ t("settings.notificationDenied") }}
              </span>
              <span v-else class="status-badge default">
                {{ t("settings.notificationDefault") }}
              </span>
              <button v-if="notificationPermission !== 'granted'" class="btn-secondary" @click="requestNotificationPermission">
                {{ t("settings.requestPermission") }}
              </button>
            </div>
            <div class="helper">{{ t("settings.notificationHint") }}</div>
          </div>
        </section>
      </div>

      <!-- About Tab -->
      <div
        v-else
        key="about" id="panel-about" role="tabpanel"
        aria-labelledby="tab-about" tabindex="0" class="tab-pane"
      >
        <section class="card">
          <h2>{{ t("settings.update") }}</h2>
          <div class="version-row">
            <span class="lbl">{{ t("settings.uiVersion") }}:</span>
            <span class="val">{{ uiV || "0.1.0" }}</span>
            <button class="btn-secondary" :disabled="chkUi" @click="chkUiUpd">
              {{ t("settings.checkUpdate") }}
            </button>
          </div>
          <div v-if="uiNewV" class="update-line">
            <span>{{ t("settings.newVersion", { v: uiNewV }) }}</span>
            <button class="btn-primary" @click="installUiUpd">{{ t("settings.install") }}</button>
          </div>
          <div v-if="uiInstalled" class="update-line">
            <span>{{ t("settings.restartToApply") }}</span>
          </div>
          <div class="version-row">
            <span class="lbl">{{ t("settings.ytdlpVersion") }}:</span>
            <span class="val">{{ ytdlpV || "—" }}</span>
            <button class="btn-secondary" :disabled="checking" @click="chkYt">
              {{ t("settings.checkUpdate") }}
            </button>
          </div>
          <div v-if="newV" class="update-line">
            <span>{{ t("settings.newVersion", { v: newV }) }}</span>
            <button class="btn-primary" :disabled="updating" @click="doUpd">
              {{ updating ? t("settings.updating") : t("settings.install") }}
            </button>
          </div>
          <div class="version-row">
            <span class="lbl">{{ t("settings.ffmpegVersion") }}:</span>
            <span class="val">{{ ffmpegV || "—" }}</span>
          </div>
          <div class="version-row">
            <span class="lbl">{{ t("settings.denoVersion") }}:</span>
            <span class="val">{{ denoV || "—" }}</span>
          </div>
          <n-progress v-if="updating && updPct > 0" type="line" :percentage="updPct" />
          <n-alert v-if="updErr" type="error" style="margin-top:8px">{{ updErr }}</n-alert>
        </section>
      </div>
      </Transition>
    </div>
  </div>
</template>

<style scoped>
.settings-layout {
  display: flex;
  height: 100%;
  gap: 24px;
}

.settings-sidebar {
  width: 180px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow-y: auto; /* 允许侧边栏独立滚动，防止纵向被裁切 */
  padding-bottom: 24px;
}

.settings-content {
  flex: 1;
  min-width: 0; /* allows children to truncate */
  max-width: 600px;
  overflow-y: auto;
  padding-right: 16px;
  /* Prevent scrolling layout shift if possible */
  margin-bottom: 24px;
}

/* 响应式：窄窗口时，调整侧边栏宽度和布局间距 */
@media (max-width: 800px) {
  .settings-layout { gap: 16px; }
  .settings-sidebar { width: 140px; }
  .tab-btn { font-size: 12px; padding: 6px 10px; }
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  background: transparent;
  border: none;
  color: var(--label-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  text-align: left;
  transition: background var(--dur-fast) var(--ease-default),
              color var(--dur-fast) var(--ease-default);
}

.tab-btn:hover {
  background: var(--hover-bg);
  color: var(--label);
}

.tab-btn.active {
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 600;
}

.tab-btn.active :deep(svg) {
  stroke: var(--accent);
}

.tab-pane {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Tab-switch micro-interaction. mode="out-in" means the leaving pane fades
   first, then the entering one slides in — so the animation actually fires on
   every switch (a plain v-show keeps the element mounted and never re-triggers). */
.pane-enter-active { transition: opacity var(--dur-fast) var(--ease-out), transform var(--dur-fast) var(--ease-out); }
.pane-leave-active { transition: opacity var(--dur-instant) var(--ease-in), transform var(--dur-instant) var(--ease-in); }
.pane-enter-from { opacity: 0; transform: translateX(6px); }
.pane-leave-to { opacity: 0; transform: translateX(-6px); }

.card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 16px 20px;
}
.card h2 {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: -0.08px;
  color: var(--text-1);
  margin: 0 0 16px;
}
.field {
  margin-bottom: 16px;
  display: flex; flex-direction: column;
  gap: 6px;
}
.field:last-child { margin-bottom: 0; }
.field label {
  font-size: 12px;
  color: var(--text-2);
  font-weight: 500;
  display: flex; align-items: center; gap: 8px;
}
.field label .num {
  color: var(--text-1);
  font-variant-numeric: tabular-nums;
}
.helper {
  font-size: 11px;
  color: var(--text-2);
  margin-top: 2px;
  line-height: 1.4;
}
.field-error {
  font-size: 11px;
  color: var(--err);
  display: inline-flex; align-items: center; gap: 4px;
}
.field-error::before {
  content: "⚠";
  font-size: 12px;
}
.presets {
  display: flex; flex-wrap: wrap; gap: 6px;
  margin-top: 2px;
}
.preset {
  font-size: 11px;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  background: var(--hover-bg);
  color: var(--text-2);
  border: 1px solid transparent;
  cursor: pointer;
  font-family: inherit;
  transition: background var(--dur-fast) var(--ease-default),
              color var(--dur-fast) var(--ease-default),
              border-color var(--dur-fast) var(--ease-default);
}
.preset:hover { background: var(--bg-elevated); color: var(--text-1); }
.preset.active {
  background: var(--accent-soft);
  color: var(--accent);
  border-color: var(--accent-border);
}

/* Segmented control */
.segmented {
  display: inline-flex;
  align-self: flex-start;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 2px;
  gap: 2px;
}
.seg {
  appearance: none;
  background: transparent;
  border: none;
  color: var(--text-2);
  font-family: inherit;
  font-size: 12px;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  min-width: 36px;
  height: 26px;
  padding: 0 10px;
  border-radius: 4px;
  cursor: pointer;
  transition: background var(--dur-fast) var(--ease-default),
              color var(--dur-fast) var(--ease-default);
}
.seg:hover:not(.active) { background: var(--hover-bg); color: var(--text-1); }
.seg.active {
  background: var(--bg-surface);
  color: var(--text-1);
  box-shadow: 0 1px 2px rgba(0,0,0,0.10), 0 0 0 1px var(--border);
}
.inline { display: flex; gap: 8px; }
.inline .n-input { flex: 1; }
.btn-secondary {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-2);
  padding: 0 16px;
  height: 34px;
  border-radius: var(--radius);
  cursor: pointer;
  font-size: 12px;
  font-family: inherit;
  font-weight: 500;
  transition: background var(--dur-fast) var(--ease-default),
              border-color var(--dur-fast) var(--ease-default),
              color var(--dur-fast) var(--ease-default);
}
.btn-secondary:hover:not(:disabled) {
  color: var(--text-1);
  border-color: var(--border-strong);
  background: var(--hover-bg);
}
.btn-secondary:active:not(:disabled) { background: var(--bg-elevated); }
.btn-secondary:disabled { opacity: 0.35; cursor: not-allowed; }
.btn-primary {
  background: var(--brand);
  color: var(--brand-on);
  border: none;
  padding: 0 16px;
  height: 34px;
  border-radius: var(--radius);
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  font-family: inherit;
  transition: background var(--dur-fast) var(--ease-default);
}
.btn-primary:hover:not(:disabled) { background: var(--brand-hover); }
.btn-primary:active:not(:disabled) { background: var(--brand-pressed); }
.btn-primary:disabled { opacity: 0.35; cursor: not-allowed; }
.version-row {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 10px;
  font-size: 12px;
}
.version-row:last-child {
  margin-bottom: 0;
}
.lbl { color: var(--text-2); width: 100px; }
.val { color: var(--text-1); flex: 1; font-family: var(--font-mono); font-size: 11px; font-variant-numeric: tabular-nums; }
.update-line {
  display: flex; align-items: center; gap: 10px;
  margin: 10px 0 14px;
  padding-left: 110px;
  font-size: 12px;
  color: var(--text-1);
}
.notification-status {
  display: flex; align-items: center; gap: 10px;
}
.status-badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: 500;
}
.status-badge.granted {
  background: rgba(52, 199, 89, 0.10);
  color: var(--ok);
  border: 1px solid rgba(52, 199, 89, 0.25);
}
.status-badge.denied {
  background: var(--err-soft);
  color: var(--err);
  border: 1px solid var(--err-border);
}
.status-badge.default {
  background: var(--hover-bg);
  color: var(--text-2);
  border: 1px solid var(--border);
}
</style>
