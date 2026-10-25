/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        'surface-dim': '#0e0e10',
        'surface': '#131315',
        'surface-card': '#18181b',
        'surface-container': '#1f1f23',
        'surface-container-high': '#28282d',
        'surface-container-highest': '#323238',
        'border-subtle': '#26262a',
        'border-muted': '#323238',
        'on-surface': '#f4f4f5',
        'on-surface-variant': '#a1a1aa',
        'outline': '#71717a',
        'accent': '#3b82f6',
        'accent-hover': '#2563eb',
        'accent-subtle': 'rgba(59, 130, 246, 0.12)',
        'success': '#10b981',
        'warning': '#f59e0b',
        'error': '#ef4444',
      },
      fontFamily: {
        sans: ['Geist', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
