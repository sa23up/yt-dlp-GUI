<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import type { Task } from "../stores/download";
import Icon from "./Icon.vue";

const props = defineProps<{ task: Task }>();
const emit = defineEmits<{
  (e: "cancel", id: string): void;
  (e: "pause", id: string): void;
  (e: "resume", id: string): void;
}>();

const { t } = useI18n();
const clampedPercent = computed(() => Math.max(0, Math.min(100, props.task.percent)));
</script>

<template>
  <div class="row" :class="task.status">
    <!-- Running -->
    <template v-if="task.status === 'running'">
      <div class="row-head">
        <div v-if="task.params.thumbnail" class="thumb-mini" aria-hidden="true">
          <img :src="task.params.thumbnail" alt="" />
        </div>
        <span class="indicator running" aria-hidden="true" />
        <span class="title">{{ task.params.title || task.params.url }}</span>
        <span class="percent" :aria-label="t('status.running') + ' ' + Math.round(clampedPercent) + '%'">
          {{ Math.round(clampedPercent) }}%
        </span>
      </div>
      <div class="bar" role="progressbar"
           :aria-valuenow="Math.round(clampedPercent)"
           aria-valuemin="0" aria-valuemax="100">
        <div class="fill" :style="{ width: clampedPercent + '%' }" />
      </div>
      <div class="row-meta">
        <span>{{ task.speed }}</span>
        <span>{{ t("home.eta") }} {{ task.eta || '—' }}</span>
      </div>
      <div class="row-actions">
        <button class="btn-ghost" @click="emit('pause', task.id)">
          <Icon name="pause" :size="12" />
          <span>{{ t("home.pause") }}</span>
        </button>
        <button class="btn-ghost danger" @click="emit('cancel', task.id)">
          <Icon name="x" :size="12" />
          <span>{{ t("home.cancelTask") }}</span>
        </button>
      </div>
    </template>

    <!-- Paused -->
    <template v-else-if="task.status === 'paused'">
      <div class="row-head">
        <div v-if="task.params.thumbnail" class="thumb-mini" aria-hidden="true">
          <img :src="task.params.thumbnail" alt="" />
        </div>
        <span class="indicator paused" aria-hidden="true" />
        <span class="title">{{ task.params.title || task.params.url }}</span>
        <span class="percent" :aria-label="t('status.paused') + ' ' + Math.round(clampedPercent) + '%'">
          {{ Math.round(clampedPercent) }}%
        </span>
      </div>
      <div class="bar" role="progressbar"
           :aria-valuenow="Math.round(clampedPercent)"
           aria-valuemin="0" aria-valuemax="100">
        <div class="fill paused-fill" :style="{ width: clampedPercent + '%' }" />
      </div>
      <div class="row-meta">
        <span>{{ t("status.paused") }}</span>
      </div>
      <div class="row-actions">
        <button class="btn-ghost" @click="emit('resume', task.id)">
          <Icon name="play" :size="12" />
          <span>{{ t("home.resume") }}</span>
        </button>
        <button class="btn-ghost danger" @click="emit('cancel', task.id)">
          <Icon name="x" :size="12" />
          <span>{{ t("home.cancelTask") }}</span>
        </button>
      </div>
    </template>

    <!-- Pending -->
    <template v-else-if="task.status === 'pending'">
      <div class="row-head">
        <div v-if="task.params.thumbnail" class="thumb-mini" aria-hidden="true">
          <img :src="task.params.thumbnail" alt="" />
        </div>
        <span class="indicator pending" aria-hidden="true" />
        <span class="title pending-title">{{ task.params.title || task.params.url }}</span>
        <span class="tag">{{ t("home.queued") }}</span>
      </div>
      <div class="row-actions">
        <button class="btn-ghost" @click="emit('cancel', task.id)">
          <Icon name="x" :size="12" />
          <span>{{ t("home.cancel") }}</span>
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.row {
  position: relative;
  background: var(--bg-surface);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-xl);
  padding: 16px 20px;
  display: flex; flex-direction: column; gap: 10px;
  box-shadow: var(--shadow-sm);
  /* Only transform + border animate on the element itself (both cheap /
     GPU-composited). The hover elevation is the ::before pseudo's opacity —
     never box-shadow, which repaints every frame and stutters on a card that's
     already re-rendering from live progress updates. */
  transition: transform var(--dur-base) var(--ease-out),
              border-color var(--dur-fast) var(--ease-default);
}
/* Hover elevation shadow, faded in via opacity (composited, no per-frame repaint). */
.row::before {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: inherit;
  box-shadow: var(--shadow-lg);
  opacity: 0;
  transition: opacity var(--dur-base) var(--ease-out);
  pointer-events: none;
}
.row:hover {
  border-color: var(--accent-border);
  transform: translateY(-2px);
}
.row:hover::before { opacity: 1; }
.row-head {
  display: flex; align-items: center; gap: 12px;
}
.thumb-mini {
  width: 48px; height: 28px;
  border-radius: 4px;
  overflow: hidden; flex-shrink: 0;
  background: var(--bg-elevated);
  box-shadow: var(--shadow-sm);
}
.thumb-mini img { width: 100%; height: 100%; object-fit: cover; display: block; }
.title { flex: 1; font-size: 13px; font-weight: 600; color: var(--text-1); overflow: hidden;
  text-overflow: ellipsis; white-space: nowrap; }
.pending-title { color: var(--text-2); }
.percent {
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 700;
  color: var(--text-1);
  letter-spacing: -0.5px;
  font-variant-numeric: tabular-nums;
}
.tag {
  font-size: 11px;
  color: var(--text-2);
  background: var(--hover-bg);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
}
.indicator {
  width: 7px; height: 7px; border-radius: 50%;
  flex-shrink: 0;
}
.indicator.running { background: var(--brand); animation: pulse 1.6s infinite linear; }
.indicator.pending { background: var(--text-3); }
.indicator.paused { background: var(--warn); }
.bar {
  height: 6px;
  background: var(--rail);
  border-radius: 3px;
  overflow: hidden;
  margin-top: 2px;
  margin-bottom: 2px;
}
.fill {
  height: 100%;
  background: var(--brand);
  border-radius: 3px;
  position: relative;
  overflow: visible;
  /* Backend throttles progress events to ~250ms apart; the bar must keep
     gliding between them, so the transition is deliberately LONGER than that
     interval. A shorter one finishes early and then stalls until the next
     event, which reads as stuttering. */
  transition: width 400ms linear;
}
/* Paused: frozen bar in a muted tone (no brand red, no shimmer). */
.paused-fill { background: var(--label-tertiary); }
.row.running .fill::after {
  content: '';
  position: absolute;
  right: 0; top: 0; bottom: 0; width: 20px;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.6));
  box-shadow: 0 0 8px var(--brand);
  border-radius: 3px;
}
.row-meta {
  display: flex; justify-content: space-between;
  font-family: var(--font-mono);
  font-size: 11px; color: var(--text-2);
  letter-spacing: -0.5px;
  font-variant-numeric: tabular-nums;
}
.row-actions { display: flex; gap: 6px; }
.btn-ghost {
  display: inline-flex; align-items: center; gap: 4px;
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-2);
  font-size: 11px;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background var(--dur-fast) var(--ease-default),
              border-color var(--dur-fast) var(--ease-default),
              color var(--dur-fast) var(--ease-default);
}
.btn-ghost:hover { color: var(--text-1); border-color: var(--border-strong); background: var(--hover-bg); }
.btn-ghost:active { background: var(--bg-elevated); }
.btn-ghost.danger { color: var(--err); }
.btn-ghost.danger:hover { border-color: var(--err); background: var(--err-soft); }
.btn-ghost.danger:active { background: var(--err-softer); }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
</style>
