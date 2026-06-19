import { createI18n } from "vue-i18n";
import zhCN from "./locales/zh-CN";
import en from "./locales/en";

// Single i18n instance shared by the Vue app (main.ts) and non-component
// modules (e.g. the download store's system-notification text), so everything
// follows the same selected locale rather than navigator.language.
const i18n = createI18n({
  legacy: false,
  locale: navigator.language.startsWith("zh") ? "zh-CN" : "en",
  fallbackLocale: "en",
  messages: { "zh-CN": zhCN, en },
});

export default i18n;
