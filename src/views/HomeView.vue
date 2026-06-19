<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { useRoute } from "vue-router";
import { useI18n } from "vue-i18n";
import { useDownloadStore, type Task, type TaskParams } from "../stores/download";
import { useSettingsStore } from "../stores/settings";
import { commands, ok, type FormatInfo, type ErrorKind } from "../ipc";
import UrlInput from "../components/UrlInput.vue";
import FormatPicker from "../components/FormatPicker.vue";
import TaskRow from "../components/TaskRow.vue";

const route = useRoute();
const { t } = useI18n();
const store = useDownloadStore();
const settings = useSettingsStore();

const urlInputRef = ref<InstanceType<typeof UrlInput> | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);
const meta = ref<{
  title: string; channel: string; duration: string; thumbnail: string;
  url: string; videoFormats: FormatInfo[]; audioFormats: FormatInfo[];
} | null>(null);

const filter = computed(() => (route.query.filter as string) || "all");

const filteredTasks = computed(() => {
  if (filter.value === "all") return store.tasks;
  if (filter.value === "running") {
    return store.tasks.filter(t => t.status === "running" || t.status === "pending" || t.status === "paused");
  }
  return [] as Task[];
});

function baseParams(url: string, title: string, thumbnail = ""): TaskParams {
  return {
    url, title, thumbnail,
    videoFormatId: null, audioFormatId: null,
    outputDir: settings.downloadDir,
    cookieSource: settings.cookieSource,
    cookieFilePath: settings.cookieFilePath,
    proxy: settings.proxy,
    rateLimit: settings.rateLimit,
    filenameTemplate: settings.filenameTemplate,
    maxHeight: settings.maxHeight,
    preferredCodec: settings.preferredCodec,
  };
}

/** Cookie + proxy applied to metadata fetch / playlist expansion so cookie-gated
 *  or region-locked content lists formats / expands exactly as it downloads. */
function netOpts() {
  return {
    cookieSource: settings.cookieSource,
    cookieFilePath: settings.cookieFilePath,
    proxy: settings.proxy,
  };
}

/** Map the backend's structured fetch error to a localized string. yt-dlp's
 *  raw stderr never reaches the UI; we show a per-kind message in the user's
 *  language (Unknown carries an already-bilingual internal message). */
function localizeError(e: ErrorKind): string {
  switch (e.kind) {
    case "RateLimited": return t("errors.rateLimited");
    case "VideoUnavailable": return t("errors.videoUnavailable");
    case "NetworkTimeout": return t("errors.networkTimeout");
    case "CookieExpired": return t("errors.cookieExpired");
    case "DiskFull": return t("errors.diskFull");
    case "Unknown": return e.message?.trim() || t("errors.unknown");
  }
}

async function onSubmit(input: string) {
  // A fetch/resolve is already in flight (e.g. a URL dropped mid-fetch) —
  // letting a second run start would interleave loading/meta state.
  if (loading.value) return;
  const urls = input.split("\n").map(s => s.trim()).filter(Boolean);
  if (!urls.length) return;
  // Drop obvious non-http garbage early; the backend also validates.
  const httpUrls = urls.filter(u => /^https?:\/\//i.test(u));
  if (!httpUrls.length) {
    error.value = t("home.noValidUrls");
    return;
  }
  // Frontend-side dedup against active + pending queue (avoid double-queueing same URL).
  const active = new Set(store.tasks.map(t => t.params.url));
  const fresh = Array.from(new Set(httpUrls.filter(u => !active.has(u))));
  if (!fresh.length) {
    error.value = t("home.alreadyQueued");
    return;
  }
  error.value = null;
  loading.value = true;
  try {
    if (fresh.length === 1 && !fresh[0].includes("/playlist")) {
      // Single URL → fetch formats for selection UI
      const res = await commands.fetchFormats(fresh[0], netOpts());
      if (res.status === "error") {
        error.value = localizeError(res.error);
        return; // keep the input text so the user can fix and resubmit
      }
      const r = res.data;
      meta.value = {
        title: r.title, channel: r.channel,
        duration: r.duration, thumbnail: r.thumbnail,
        url: fresh[0],
        videoFormats: r.videoFormats,
        audioFormats: r.audioFormats,
      };
    } else {
      // Batch / playlist → resolve then enqueue in ONE backend call.
      const entries = await ok(commands.resolveQueue(fresh, netOpts()));
      const params = entries
        .filter(e => !active.has(e.url))
        .map(e => baseParams(e.url, e.title));
      if (params.length) await store.enqueueBatch(params);
    }
    urlInputRef.value?.clear();
  } catch (e) {
    error.value = String(e);
    // Keep input text so the user can fix and resubmit.
  } finally {
    loading.value = false;
  }
}

async function onPickerStart(v: { videoFormatId: string | null; audioFormatId: string | null }) {
  const m = meta.value;
  if (!m) return;
  // Clear optimistically BEFORE awaiting so a fast double-click can't fire a
  // second enqueue (the backend dedups on task id, not URL, so it would queue
  // the same video twice). Restore on failure so the UI isn't left stuck.
  meta.value = null;
  try {
    await store.enqueue({
      ...baseParams(m.url, m.title, m.thumbnail),
      videoFormatId: v.videoFormatId,
      audioFormatId: v.audioFormatId,
    });
  } catch (e) {
    error.value = String(e);
    meta.value = m;
  }
}

async function onCancel(id: string) {
  try { await store.cancel(id); } catch (e) { error.value = String(e); }
}
async function onPause(id: string) {
  try { await store.pause(id); } catch (e) { error.value = String(e); }
}
async function onResume(id: string) {
  try { await store.resume(id); } catch (e) { error.value = String(e); }
}

// React to a URL dropped onto the window (App.vue sets store.droppedUrl).
// `immediate` covers the drop-on-Settings case: App.vue navigates here first,
// so the value is already set by the time this component mounts and a plain
// watch would never fire.
watch(() => store.droppedUrl, async u => {
  if (!u) return;
  store.setDroppedUrl(null);
  await onSubmit(u);
}, { immediate: true });
</script>

<template>
  <div class="home">
    <h1 class="sr-only">{{ t("a11y.pageHome") }}</h1>
    <UrlInput ref="urlInputRef" :loading="loading" @submit="onSubmit" />

    <n-alert v-if="error" type="error" closable @close="error = null" style="margin-bottom:16px">
      {{ error }}
    </n-alert>

    <!-- Failed-download notices: shown only when system notifications are
         unavailable, so a failure isn't completely silent. -->
    <n-alert
      v-for="f in store.failedNotices" :key="f.id"
      type="error" closable @close="store.dismissFailed(f.id)"
      style="margin-bottom:8px"
    >
      {{ t("home.notifyFailed") }} — {{ f.params.title || f.params.url }}
    </n-alert>

    <!-- Loading state for format fetching -->
    <div v-if="loading && !meta" class="loading-state">
      <div class="loading-spinner" aria-hidden="true">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10" opacity="0.25" />
          <path d="M12 2a10 10 0 0 1 10 10" opacity="0.75">
            <animateTransform attributeName="transform" type="rotate" from="0 12 12" to="360 12 12" dur="1s" repeatCount="indefinite" />
          </path>
        </svg>
      </div>
      <span>{{ t("home.fetchingFormats") }}</span>
    </div>

    <FormatPicker
      v-if="meta"
      :meta="meta"
      @start="onPickerStart"
      @cancel="meta = null"
    />

    <!-- Empty state -->
    <div v-if="!loading && !meta && !filteredTasks.length" class="empty">
      <div class="empty-icon" aria-hidden="true">
        <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="7 10 12 15 17 10" />
          <line x1="12" y1="15" x2="12" y2="3" />
        </svg>
      </div>
      <div class="empty-title">{{ t("home.emptyTitle") }}</div>
      <div class="empty-sub">{{ t("home.emptySubtitle") }}</div>
    </div>

    <!-- Active tasks. TransitionGroup gives arrivals/removals the DS §3.2
         treatment: enter eases out (deceleration), exit is faster (HIG). -->
    <TransitionGroup
      v-if="filteredTasks.length"
      tag="section" name="task" class="section"
      :aria-label="t('nav.active')"
    >
      <TaskRow
        v-for="task in filteredTasks" :key="task.id"
        :task="task"
        @cancel="onCancel"
        @pause="onPause"
        @resume="onResume"
      />
    </TransitionGroup>
  </div>
</template>

<style scoped>
.home {
  max-width: 820px;
  margin: 0 auto;
}
.empty {
  text-align: center;
  padding: 80px 0 56px;
  color: var(--text-2);
}
.empty-icon {
  width: 88px;
  height: 88px;
  border-radius: 50%;
  background: transparent;
  color: var(--accent);
  display: flex; align-items: center; justify-content: center;
  margin: 0 auto 32px;
  box-shadow: 0 0 0 0 var(--accent-soft);
  animation: ripple 3s infinite;
}
.empty-icon svg {
  width: 36px;
  height: 36px;
  stroke-width: 1.2;
}
@keyframes ripple {
  0% { box-shadow: 0 0 0 0 var(--accent-border); }
  70% { box-shadow: 0 0 0 30px transparent; }
  100% { box-shadow: 0 0 0 0 transparent; }
}
.empty-title {
  font-size: 24px; font-weight: 800;
  letter-spacing: -0.5px;
  color: var(--text-1);
  margin-bottom: 12px;
}
.empty-sub {
  font-size: 13px;
  letter-spacing: 0;
  color: var(--text-2);
}

.section {
  position: relative; /* anchor for .task-leave-active's absolute positioning */
  margin-bottom: 24px;
  display: flex; flex-direction: column;
  gap: 8px;
}
/* Task arrival / removal / reflow (scoped styles reach TaskRow's root). */
.task-enter-active {
  transition: opacity var(--dur-base) var(--ease-out),
              transform var(--dur-base) var(--ease-out);
}
.task-leave-active {
  /* Take the leaving row out of flow so siblings slide up via .task-move. */
  position: absolute;
  left: 0; right: 0;
  transition: opacity var(--dur-fast) var(--ease-in);
}
.task-enter-from { opacity: 0; transform: translateY(4px); }
.task-leave-to { opacity: 0; }
.task-move { transition: transform var(--dur-base) var(--ease-default); }
.loading-state {
  display: flex; align-items: center; justify-content: center;
  gap: 12px;
  padding: 48px 0;
  color: var(--text-2);
  font-size: 13px;
}
.loading-spinner {
  display: flex; align-items: center; justify-content: center;
  color: var(--accent);
}
</style>
