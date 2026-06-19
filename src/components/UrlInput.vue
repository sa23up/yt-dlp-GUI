<script setup lang="ts">
import { ref, computed, nextTick } from "vue";
import { useI18n } from "vue-i18n";
import Icon from "./Icon.vue";

const { t } = useI18n();

const props = defineProps<{ loading: boolean }>();
const emit = defineEmits<{ (e: "submit", value: string): void }>();

const text = ref("");
const ta = ref<HTMLTextAreaElement | null>(null);

const lineCount = computed(() => text.value.split("\n").map(s => s.trim()).filter(Boolean).length);

/** Grow the textarea to fit pasted multi-URL / playlist input (capped by the
 *  CSS max-height, past which it scrolls). Without this a 10-URL paste stays a
 *  one-row box. min-height in CSS is the floor. */
function autoGrow() {
  const el = ta.value;
  if (!el) return;
  el.style.height = "auto";
  el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
}

function submit() {
  const v = text.value.trim();
  if (!v || props.loading) return;
  emit("submit", v);
  // Parent clears via clear() on successful submit; keep text on error.
}

defineExpose({
  clear() { text.value = ""; void nextTick(autoGrow); },
  focus() { ta.value?.focus(); },
});

function onKeydown(e: KeyboardEvent) {
  // Enter without Shift submits; Shift+Enter inserts newline.
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
    e.preventDefault();
    submit();
  }
}
</script>

<template>
  <div class="input-bar">
    <textarea
      ref="ta"
      v-model="text"
      class="url"
      :placeholder="t('home.inputPlaceholder')"
      :disabled="loading"
      :aria-label="t('home.inputPlaceholder')"
      rows="1"
      @input="autoGrow"
      @keydown="onKeydown"
    />
    <div class="actions">
      <span v-if="lineCount > 1" class="counter" :aria-label="t('home.urlCount', lineCount)">{{ lineCount }}</span>
      <button class="btn-primary" :disabled="loading" @click="submit" :aria-label="t('home.parse')">
        <Icon v-if="loading" name="loader" :size="16" class="spinner" />
        <Icon v-else name="download" :size="16" />
        <span>{{ loading ? t("home.fetching") : t("home.parse") }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.input-bar {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  background: var(--bg-surface);
  border: 1px solid var(--border-strong);
  border-radius: 20px;
  padding: 16px;
  margin-top: 16px;
  margin-bottom: 40px;
  box-shadow: var(--shadow-lg);
  transform: translateY(0);
  transition: transform var(--dur-base) var(--spring-snappy),
              box-shadow var(--dur-base) var(--ease-out),
              border-color var(--dur-fast) var(--ease-default);
}
.input-bar:focus-within {
  transform: translateY(-4px);
  border-color: var(--accent);
  box-shadow: var(--shadow-xl), 0 0 0 3px var(--accent-soft);
}
.url {
  flex: 1;
  min-height: 48px;
  max-height: 160px;
  padding: 12px 16px;
  border-radius: var(--radius);
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-1);
  font-size: 16px;
  font-weight: 500;
  font-family: inherit;
  resize: vertical;
  outline: none;
  line-height: 1.6;
  transition: background var(--dur-fast) var(--ease-default);
}
.url:focus { border-color: transparent; box-shadow: none; }
.url::placeholder { color: var(--text-3); }
.actions {
  display: flex; align-items: center; gap: 8px;
  flex-shrink: 0;
}
.counter {
  font-size: 11px;
  color: var(--text-2);
  background: var(--hover-bg);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  font-variant-numeric: tabular-nums;
}
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--brand);
  color: var(--brand-on);
  border: none;
  font-weight: 700;
  height: 48px;
  padding: 0 24px;
  border-radius: 12px;
  cursor: pointer;
  white-space: nowrap;
  font-size: 14px;
  box-shadow: 0 4px 12px var(--brand-soft);
  transition: background var(--dur-fast) var(--ease-default),
              transform var(--dur-fast) var(--spring-snappy),
              box-shadow var(--dur-fast) var(--ease-default);
}
.btn-primary:hover:not(:disabled) { 
  background: var(--brand-hover); 
  transform: translateY(-1px);
  box-shadow: 0 6px 16px var(--brand-soft);
}
.btn-primary:active:not(:disabled) { 
  background: var(--brand-pressed); 
  transform: translateY(1px);
  box-shadow: 0 2px 8px var(--brand-softer);
}
.btn-primary:disabled { opacity: 0.35; cursor: not-allowed; }

.spinner { animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
