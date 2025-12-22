// Theme Toggle Logic
(function() {
  // Check for saved theme preference or system preference
  const savedTheme = localStorage.getItem('theme');
  const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const theme = savedTheme || (systemPrefersDark ? 'dark' : 'light');

  document.documentElement.setAttribute('data-theme', theme);
})();

function toggleTheme() {
  const html = document.documentElement;
  const current = html.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';

  // Add transition class for smooth theme change
  html.classList.add('theme-transition');
  html.setAttribute('data-theme', next);
  localStorage.setItem('theme', next);

  // Update icon
  updateThemeIcon(next);

  // Remove transition class after animation
  setTimeout(() => html.classList.remove('theme-transition'), 300);
}

function updateThemeIcon(theme) {
  const sunIcon = document.getElementById('sun-icon');
  const moonIcon = document.getElementById('moon-icon');

  if (sunIcon && moonIcon) {
    if (theme === 'dark') {
      sunIcon.classList.remove('hidden');
      moonIcon.classList.add('hidden');
    } else {
      sunIcon.classList.add('hidden');
      moonIcon.classList.remove('hidden');
    }
  }
}

// Initialize icon on load
document.addEventListener('DOMContentLoaded', function() {
  const theme = document.documentElement.getAttribute('data-theme');
  updateThemeIcon(theme);
});
