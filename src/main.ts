import { createApp } from "vue";
import { createPinia } from "pinia";
import {
  create,
  NAlert,
  NConfigProvider,
  NInput,
  NMessageProvider,
  NProgress,
  NRadio,
  NRadioGroup,
  NSelect,
} from "naive-ui";
import App from "./App.vue";
import router from "./router";
import i18n from "./i18n";
import { commands } from "./ipc";

// Per-component registration: lets vite tree-shake the rest of naive-ui.
const naive = create({
  components: [
    NAlert,
    NConfigProvider,
    NInput,
    NMessageProvider,
    NProgress,
    NRadio,
    NRadioGroup,
    NSelect,
  ],
});

const pinia = createPinia();

const app = createApp(App);

// Global error handler for uncaught component errors
app.config.errorHandler = (err, instance, info) => {
  if (import.meta.env.DEV) {
    console.error("[Vue Error]", err);
    console.error("Component:", instance);
    console.error("Error info:", info);
  }

  // Log to backend for production monitoring. Errors from the IPC call are
  // swallowed so the error handler itself can never throw.
  if (import.meta.env.PROD) {
    void commands.writeLog("ERROR", `Vue error: ${err} (${info})`).catch(() => {});
  }
};

// Global warning handler (dev only)
if (import.meta.env.DEV) {
  app.config.warnHandler = (msg, _instance, trace) => {
    console.warn("[Vue Warning]", msg);
    console.warn("Trace:", trace);
  };
}

app.use(naive);
app.use(i18n);
app.use(pinia);
app.use(router);
app.mount("#app");
