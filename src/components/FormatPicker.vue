<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useSettingsStore } from "../stores/settings";
import type { FormatInfo } from "../ipc";
import Icon from "./Icon.vue";

interface Meta {
  title: string;
  channel: string;
  duration: string;
  thumbnail: string;
  videoFormats: FormatInfo[];
  audioFormats: FormatInfo[];
}

const props = defineProps<{ meta: Meta }>();
const emit = defineEmits<{
  (e: "start", v: { videoFormatId: string | null; audioFormatId: string | null }): void;
  (e: "cancel"): void;
}>();

const { t } = useI18n();
const settings = useSettingsStore();

type Mode = "best" | "video+audio" | "audio";
const mode = ref<Mode>("best");
const selectedVideo = ref<string | null>(null);
const selectedAudio = ref<string | null>(null);
const thumbOk = ref(true);
function onThumbError() { thumbOk.value = false; }

const filteredVideos = computed(() => {
  let list = props.meta.videoFormats;
  if (settings.maxHeight > 0) list = list.filter(f => f.height === 0 || f.height <= settings.maxHeight);
  if (settings.preferredCodec !== "any") {
    const c = settings.preferredCodec.toLowerCase();
    const matched = list.filter(f => f.codec.toLowerCase().includes(c));
    if (matched.length) list = matched;
  }
  return list;
});

watch(() => props.meta, () => {
  mode.value = "best";
  selectedVideo.value = null;
  selectedAudio.value = null;
  thumbOk.value = true;
}, { deep: false });

function pickVideo(f: FormatInfo) {
  mode.value = "video+audio";
  selectedVideo.value = f.id;
  // A muxed format already carries its own audio — don't pair a separate audio
  // track (that would download + merge a redundant stream).
  if (f.muxed) {
    selectedAudio.value = null;
  } else if (!selectedAudio.value && props.meta.audioFormats.length > 0) {
    selectedAudio.value = props.meta.audioFormats[0].id;
  }
}
function pickAudio(id: string) {
  selectedAudio.value = id;
  if (!selectedVideo.value) mode.value = "audio";
}
function toggleAudioOnly() {
  mode.value = "audio";
  selectedVideo.value = null;
  if (!selectedAudio.value && props.meta.audioFormats.length) {
    selectedAudio.value = props.meta.audioFormats[0].id;
  }
}
function backToBest() {
  mode.value = "best";
  selectedVideo.value = null;
  selectedAudio.value = null;
}

function chooseBest() {
  backToBest();
  emit("start", { videoFormatId: null, audioFormatId: null });
}
function startCustom() {
  if (mode.value === "audio") {
    emit("start", { videoFormatId: null, audioFormatId: selectedAudio.value });
  } else if (mode.value === "video+audio") {
    emit("start", { videoFormatId: selectedVideo.value, audioFormatId: selectedAudio.value });
  } else {
    chooseBest();
  }
}

function onRowKeydown(e: KeyboardEvent, fn: () => void) {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    fn();
    return;
  }
  // Listbox arrow-key navigation: move focus between options in the same listbox.
  if (e.key === "ArrowDown" || e.key === "ArrowUp" || e.key === "Home" || e.key === "End") {
    e.preventDefault();
    const target = e.target as HTMLElement;
    const list = target.closest('[role="listbox"]');
    if (!list) return;
    const items = Array.from(list.querySelectorAll<HTMLElement>('[role="option"]'));
    const i = items.indexOf(target);
    let nextIdx: number;
    if (e.key === "Home") nextIdx = 0;
    else if (e.key === "End") nextIdx = items.length - 1;
    else if (e.key === "ArrowDown") nextIdx = Math.min(items.length - 1, i + 1);
    else nextIdx = Math.max(0, i - 1);
    items[nextIdx]?.focus();
  }
}
</script>

<template>
  <div class="meta-card">
    <div class="meta-row">
      <div class="thumb">
        <img v-if="meta.thumbnail && thumbOk" :src="meta.thumbnail" alt="" @error="onThumbError" />
        <Icon v-else name="play" :size="32" />
      </div>
      <div class="meta-text">
        <div class="title">{{ meta.title || t("home.untitled") }}</div>
        <div class="sub">
          <span>{{ t("home.channel") }}: {{ meta.channel || "—" }}</span>
          <span v-if="meta.duration">{{ t("home.duration") }}: {{ meta.duration }}</span>
        </div>
      </div>
      <button
        class="btn-best" :class="{ active: mode === 'best' }"
        @click="chooseBest"
        :aria-pressed="mode === 'best'"
      >
        <Icon name="spark" :size="14" />
        <span>{{ t("home.bestQuality") }}</span>
      </button>
    </div>

    <div class="divider" />

    <div class="section-title">{{ t("home.selectFormat") }}</div>

    <div class="group-label">{{ t("home.videoAudio") }}</div>
    <ul v-if="filteredVideos.length" class="format-list" role="listbox" :aria-label="t('home.videoAudio')">
      <li v-for="f in filteredVideos" :key="'v' + f.id"
          class="format-row" :class="{ selected: selectedVideo === f.id }"
          tabindex="0"
          role="option"
          :aria-selected="selectedVideo === f.id"
          @click="pickVideo(f)"
          @keydown="onRowKeydown($event, () => pickVideo(f))">
        <span class="dot" aria-hidden="true" />
        <span class="lbl">
          {{ f.resolution }}
          <span class="codec">{{ f.codec.toUpperCase() }}<template v-if="f.muxed"> · A+V</template></span>
        </span>
        <span class="size">{{ f.filesize }}</span>
      </li>
    </ul>
    <div v-else class="filter-empty">{{ t("home.noFormatsMatch") }}</div>

    <template v-if="meta.audioFormats.length">
      <button type="button"
              class="group-label clickable" :class="{ active: mode === 'audio' }"
              :aria-pressed="mode === 'audio'"
              @click="toggleAudioOnly">
        {{ t("home.audioOnly") }}
      </button>
      <ul class="format-list" role="listbox" :aria-label="t('home.audioOnly')">
        <li v-for="f in meta.audioFormats" :key="'a' + f.id"
            class="format-row" :class="{ selected: selectedAudio === f.id }"
            tabindex="0"
            role="option"
            :aria-selected="selectedAudio === f.id"
            @click="pickAudio(f.id)"
            @keydown="onRowKeydown($event, () => pickAudio(f.id))">
          <span class="dot" aria-hidden="true" />
          <span class="lbl">{{ f.codec.toUpperCase() }} <span class="codec">{{ f.label }}</span></span>
          <span class="size">{{ f.filesize }}</span>
        </li>
      </ul>
    </template>

    <div class="actions">
      <button class="btn-secondary" @click="emit('cancel')">{{ t("home.cancel") }}</button>
      <button class="btn-primary" @click="startCustom">
        <Icon name="play" :size="14" />
        <span>{{ t("home.startDownload") }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.meta-card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
  margin-bottom: 20px;
  /* Arrival animation (DS §3.2 "popover open" class): the card appears after
     an async fetch, so a short ease-out entrance reads as "result arrived". */
  animation: card-enter var(--dur-base) var(--ease-out);
}
@keyframes card-enter {
  from { opacity: 0; transform: translateY(4px); }
  to   { opacity: 1; transform: translateY(0); }
}
.meta-row { display: flex; flex-wrap: wrap; gap: 16px; align-items: flex-start; }
.thumb {
  position: relative;
  width: 160px; height: 90px; border-radius: var(--radius);
  background: var(--bg-elevated);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; overflow: hidden;
  color: var(--text-3);
}
.thumb img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.meta-text { flex: 1; min-width: 0; }
.title {
  font-size: 15px; font-weight: 600;
  letter-spacing: -0.41px;
  color: var(--text-1); line-height: 1.3;
  overflow: hidden; text-overflow: ellipsis;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
}
.sub {
  margin-top: 6px;
  display: flex; gap: 12px;
  font-size: 12px; color: var(--text-2);
}

/* Best button: a subdued *chip*, not a Primary CTA — only the bottom
   Start-Download button is solid brand red.  Active state is ACCENT-soft
   because "Best is selected" is a *selection* (navigation semantic), not
   the download action itself. The actual download is triggered by clicking
   the button, at which point the picker dismisses. */
.btn-best {
  display: inline-flex; align-items: center; gap: 6px;
  background: transparent;
  color: var(--label);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius);
  padding: 6px 12px;
  font-size: 12px; font-weight: 600;
  cursor: pointer;
  flex-shrink: 0;
  transition: background var(--dur-fast) var(--ease-default),
              border-color var(--dur-fast) var(--ease-default),
              color var(--dur-fast) var(--ease-default);
}
.btn-best:hover { background: var(--hover-bg); border-color: var(--label-tertiary); }
.btn-best.active {
  background: var(--accent-soft);
  color: var(--accent);
  border-color: var(--accent-border);
}
.btn-best.active :deep(svg) { color: var(--accent); }
/* The spark icon stays brand-tinted when inactive — it carries the brand. */
.btn-best :deep(svg) { color: var(--brand); }

.divider { height: 1px; background: var(--border); margin: 16px 0; }
.section-title {
  font-size: 13px; font-weight: 700;
  letter-spacing: -0.08px;
  color: var(--label);
  margin-bottom: 12px;
}

/* Group label is a real <button> now so it gets keyboard activation and
   focus ring for free. Reset native button styling. */
.group-label {
  font-size: 12px; font-weight: 600;
  color: var(--text-2);
  margin: 12px 0 6px;
  display: inline-flex; align-items: center; gap: 6px;
  padding: 0;
  background: none;
  border: none;
  font-family: inherit;
}
.group-label.clickable { cursor: pointer; }
.group-label.clickable:hover { color: var(--label); }
.group-label.clickable.active { color: var(--accent); }
.group-label.clickable.active::before {
  content: "";
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--accent);
}

.format-list {
  list-style: none;
  display: flex; flex-direction: column; gap: 4px;
  /* Long videos expose 20+ formats — cap the list so the action row below
     stays in view; ~6 rows visible, rest scroll. */
  max-height: 246px;
  overflow-y: auto;
  /* 2px inset keeps the focus ring of edge rows from being clipped by the
     scroll box; negative margin cancels it out of the layout. */
  padding: 2px;
  margin: -2px;
}
.format-row {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg-surface);
  cursor: pointer;
  user-select: none;
  transition: background var(--dur-fast) var(--ease-default),
              border-color var(--dur-fast) var(--ease-default);
}
.format-row:hover { background: var(--hover-bg); border-color: var(--border-strong); }
.format-row:active { background: var(--bg-elevated); }
.format-row.selected {
  background: var(--accent-soft);
  border-color: var(--accent-border);
}
/* Selected row reads as Headline (13/600) per DS §2.3 format-row pairing. */
.format-row.selected .lbl { font-weight: 600; }
.dot {
  width: 14px; height: 14px;
  border-radius: 50%;
  border: 2px solid var(--label-tertiary);
  flex-shrink: 0;
  transition: border-color var(--dur-fast) var(--ease-default),
              background var(--dur-fast) var(--ease-default);
}
.format-row.selected .dot {
  border-color: var(--accent);
  background: radial-gradient(circle at center, var(--accent) 4px, transparent 5px);
}
.lbl { flex: 1; font-size: 13px; color: var(--label); }
.codec { font-size: 11px; color: var(--label-secondary); margin-left: 8px; }
.size { font-size: 11px; color: var(--label-secondary); }

.filter-empty {
  padding: 12px;
  border: 1px dashed var(--border);
  border-radius: var(--radius);
  font-size: 12px;
  color: var(--label-secondary);
  background: var(--bg-elevated);
}

.format-row:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.actions {
  display: flex; justify-content: space-between;
  margin-top: 16px;
}
.btn-secondary {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-2);
  padding: 0 16px;
  height: 40px;
  border-radius: var(--radius);
  cursor: pointer;
  font-size: 13px;
  transition: background var(--dur-fast) var(--ease-default),
              border-color var(--dur-fast) var(--ease-default),
              color var(--dur-fast) var(--ease-default);
}
.btn-secondary:hover { color: var(--text-1); border-color: var(--border-strong); background: var(--hover-bg); }
.btn-secondary:active { background: var(--bg-elevated); }
.btn-primary {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--brand);
  color: var(--brand-on);
  border: none;
  font-weight: 700;
  font-size: 13px;
  height: 40px;
  padding: 0 20px;
  border-radius: var(--radius);
  cursor: pointer;
  transition: background var(--dur-fast) var(--ease-default);
}
.btn-primary:hover { background: var(--brand-hover); }
.btn-primary:active { background: var(--brand-pressed); }
</style>
