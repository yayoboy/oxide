/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'gh-canvas': {
          DEFAULT: '#0d1117',
          subtle: '#161b22',
        },
        'gh-border': {
          DEFAULT: '#30363d',
          muted: '#21262d',
        },
        'gh-fg': {
          DEFAULT: '#c9d1d9',
          muted: '#8b949e',
          subtle: '#6e7681',
        },
        'gh-accent': {
          primary: '#58a6ff',
          emphasis: '#1f6feb',
        },
        'gh-success': {
          DEFAULT: '#3fb950',
          emphasis: '#238636',
        },
        'gh-attention': {
          DEFAULT: '#f7b955',
          emphasis: '#9e6a03',
        },
        'gh-danger': {
          DEFAULT: '#f85149',
          emphasis: '#da3633',
        },
      },
      boxShadow: {
        'glow-blue': '0 0 8px rgba(88, 166, 255, 0.3)',
        'glow-green': '0 0 8px rgba(63, 185, 80, 0.3)',
        'glow-red': '0 0 8px rgba(248, 81, 73, 0.3)',
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
