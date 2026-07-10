/**
 * Sets up the light/dark theme toggle button.
 * Persists the selected theme in localStorage so it survives page reloads.
 * @author Cristina Vedinas
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
