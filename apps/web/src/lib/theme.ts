export const THEME_STORAGE_KEY = "jbn-theme";

export type ThemeChoice = "light" | "dark";

/** Runs before first paint: applies a stored override so the page never flashes the wrong theme. */
export const THEME_INIT_SCRIPT = `(function(){try{var t=localStorage.getItem(${JSON.stringify(
  THEME_STORAGE_KEY,
)});if(t==="light"||t==="dark")document.documentElement.setAttribute("data-theme",t)}catch(e){}})()`;
