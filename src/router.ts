import { createMemoryHistory, createRouter } from "vue-router";
import HomeView from "./views/HomeView.vue";
import SettingsView from "./views/SettingsView.vue";

const routes = [
  { path: "/", name: "home", component: HomeView },
  { path: "/settings", name: "settings", component: SettingsView },
];

const router = createRouter({ history: createMemoryHistory(), routes });
export default router;
