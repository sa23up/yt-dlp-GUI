<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter, useRoute } from "vue-router";
import { useDownloadStore } from "../stores/download";
import Icon from "./Icon.vue";

const { t } = useI18n();
const router = useRouter();
const route = useRoute();
const download = useDownloadStore();

type Key = "all" | "running";

const counts = computed(() => ({
  all: download.tasks.length,
  running: download.activeCount,
}));

const items: Array<{ key: Key; icon: "grid" | "download"; label: string }> = [
  { key: "all", icon: "grid", label: "nav.all" },
  { key: "running", icon: "download", label: "nav.active" },
];

const activeFilter = computed(() => {
  if (route.name === "settings") return "settings";
  return (route.query.filter as string) || "all";
});

function go(key: Key | "settings") {
  if (key === "settings") router.push({ name: "settings" });
  else router.push({ name: "home", query: { filter: key } });
}
</script>

<template>
  <nav class="sidebar" :aria-label="t('nav.tasksNav')">
    <div class="section-label">{{ t("nav.sectionTasks") }}</div>
    <button
      v-for="item in items" :key="item.key"
      type="button"
      role="link"
      class="nav-item" :class="{ active: activeFilter === item.key }"
      :aria-current="activeFilter === item.key ? 'page' : undefined"
      @click="go(item.key)"
    >
      <Icon :name="item.icon" :size="15" />
      <span>{{ t(item.label) }}</span>
      <span v-if="counts[item.key] > 0" class="count">{{ counts[item.key] }}</span>
    </button>

    <div class="spacer" />
    <div class="divider" />
    <button
      type="button"
      role="link"
      class="nav-item" :class="{ active: activeFilter === 'settings' }"
      :aria-current="activeFilter === 'settings' ? 'page' : undefined"
      @click="go('settings')"
    >
      <Icon name="settings" :size="15" />
      <span>{{ t("nav.settings") }}</span>
    </button>
  </nav>
</template>

<style scoped>
.sidebar {
  width: 200px;
  flex-shrink: 0;
  /* On macOS with a transparent window we'd add backdrop-filter for vibrancy;
     on Win/Linux Tauri webview (non-transparent window) backdrop-filter has
     nothing behind to blur and triggers a WebKitGTK rendering bug at certain
     window sizes that paints a translucent rectangle over wrong coordinates.
     Use the opaque sidebar background everywhere. */
  background: var(--bg-sidebar-opaque);
  border-right: 1px solid var(--separator);
  display: flex;
  flex-direction: column;
  padding: 16px 12px;
  overflow-y: auto;
  transition: width var(--dur-fast) var(--ease-default);
}

/* 响应式：当窗口变窄时，缩小侧边栏 */
@media (max-width: 900px) {
  .sidebar { width: 160px; padding: 16px 8px; }
}
.section-label {
  font-size: 10px; font-weight: 700;
  color: var(--label-secondary);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 8px;
  padding: 0 8px;
}

/* Nav item — selected state uses ACCENT blue (navigation semantic).
   Red is forbidden here per Hybrid C. */
.nav-item {
  position: relative;
  display: flex; align-items: center; gap: 10px;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 400;
  color: var(--label-secondary);
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
  margin-bottom: 2px;
  transition: background var(--dur-fast) var(--ease-default),
              color var(--dur-fast) var(--ease-default);
  animation: slideIn 0.4s var(--spring-snappy) backwards;
}
.nav-item:nth-of-type(1) { animation-delay: 0.05s; }
.nav-item:nth-of-type(2) { animation-delay: 0.1s; }
.nav-item:nth-of-type(3) { animation-delay: 0.15s; }

@keyframes slideIn {
  from { opacity: 0; transform: translateX(-10px); }
  to { opacity: 1; transform: translateX(0); }
}

.nav-item > span:nth-of-type(1) { flex: 1; }
.nav-item:hover { background: var(--hover-bg); color: var(--label); }
.nav-item.active {
  font-weight: 600;
  color: var(--label);
  background: var(--hover-bg);
}
.nav-item.active::before {
  content: "";
  position: absolute;
  left: 0;
  top: 6px;
  bottom: 6px;
  width: 2px;
  background: var(--accent);
  border-radius: 2px;
}
.nav-item.active :deep(svg) { stroke: var(--label); }
.count {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 500;
  letter-spacing: -0.5px;
  color: var(--label-secondary);
  background: var(--bg-elevated);
  padding: 1px 6px;
  border-radius: 8px;
  min-width: 18px;
  text-align: center;
  font-variant-numeric: tabular-nums;
}
.nav-item.active .count {
  color: var(--accent);
  background: var(--accent-soft);
}
.spacer { flex: 1; }
.divider { height: 1px; background: var(--separator); margin-bottom: 8px; }
</style>
