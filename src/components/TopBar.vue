<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { useSettingsStore } from "../stores/settings";
import { useDownloadStore } from "../stores/download";
import Icon from "./Icon.vue";

const { t } = useI18n();
const settings = useSettingsStore();
const download = useDownloadStore();
</script>

<template>
  <div class="topbar">
    <span class="brand">{{ t("app.name") }}</span>
    <span v-if="download.activeCount > 0" class="badge">
      {{ t("app.downloads", { count: download.activeCount }, download.activeCount) }}
    </span>
    <button
      class="theme-toggle"
      :aria-label="settings.theme === 'dark' ? t('settings.themeLight') : t('settings.themeDark')"
      @click="settings.toggleTheme()"
    >
      <Icon :name="settings.theme === 'dark' ? 'sun' : 'moon'" :size="16" />
    </button>
  </div>
</template>

<style scoped>
.topbar {
  display: flex; align-items: center; gap: 12px;
  padding: 8px 20px;
  height: 40px;
  box-sizing: border-box;
  /* Same WebKitGTK backdrop-filter bug as Sidebar — use opaque value. */
  background: var(--bg-toolbar-opaque);
  border-bottom: 1px solid var(--separator);
  flex-shrink: 0;
}
.brand {
  font-size: 13px; font-weight: 700;
  color: var(--label);
  letter-spacing: -0.08px;
  display: inline-flex; align-items: center; gap: 6px;
}
.brand::before {
  /* Brand chip — the only place red appears on the toolbar. Download semantic. */
  content: "";
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--brand);
}
.badge {
  /* "{N} downloads in progress" badge — download semantic, brand red. */
  font-size: 11px;
  color: var(--brand);
  background: var(--brand-soft);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-weight: 600;
}
.theme-toggle {
  margin-left: auto;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 6px 8px;
  border-radius: var(--radius-sm);
  color: var(--label-secondary);
  display: inline-flex; align-items: center; justify-content: center;
  transition: background var(--dur-fast) var(--ease-default),
              color var(--dur-fast) var(--ease-default);
}
.theme-toggle:hover { background: var(--hover-bg); color: var(--label); }
.theme-toggle:active { background: var(--border-strong); }
</style>
