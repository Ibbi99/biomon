// src/ui/components/ThemeToggle.ts
//
// Sets up the light/dark theme toggle button.
// Persists the selected theme in localStorage so it survives page reloads.
//
// Usage:
//   import { setupThemeToggle } from "@ui/components/ThemeToggle";
//   setupThemeToggle(); // call once at page load

/**
 * Initializes the theme toggle button.
 * - Reads the saved theme from localStorage (defaults to "dark")
 * - Applies it immediately to <html data-theme="...">
 * - Listens for button clicks to switch between dark and light
 */
export function setupThemeToggle() {
  const themeToggle = document.getElementById("theme-toggle");
  if (!themeToggle) return;

  // Apply the previously saved theme on page load
  const savedTheme = localStorage.getItem("theme") ?? "dark";
  document.documentElement.setAttribute("data-theme", savedTheme);
  themeToggle.textContent = savedTheme === "dark" ? "🌙" : "☀️";

  // Toggle theme on button click and persist the choice
  themeToggle.addEventListener("click", () => {
    const html = document.documentElement;
    const currentTheme = html.getAttribute("data-theme") ?? "dark";
    const nextTheme = currentTheme === "dark" ? "light" : "dark";
    html.setAttribute("data-theme", nextTheme);
    themeToggle.textContent = nextTheme === "dark" ? "🌙" : "☀️";
    localStorage.setItem("theme", nextTheme);
  });
}
