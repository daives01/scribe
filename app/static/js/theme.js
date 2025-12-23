// Theme system preference listener
(function() {
  const savedTheme = localStorage.getItem('theme');

  // Listen for system theme changes when no preference is saved
  if (!savedTheme) {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
      document.documentElement.classList.toggle('dark', e.matches);
    });
  }
})();
