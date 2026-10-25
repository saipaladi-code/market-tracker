/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      colors: {
        navy: {
          950: '#070b14', // deepest backdrop
          900: '#0b1120', // main layout background
          850: '#0f172a', // primary card background
          800: '#142038', // elevated card / input background
          750: '#1c2b4a', // card borders & dividing lines
          700: '#253861', // hover borders & controls
          600: '#385189', // subdued text & subtle icons
        },
        bullish: {
          DEFAULT: '#10b981',
          light: '#34d399',
          dark: '#065f46',
          bg: 'rgba(16, 185, 129, 0.1)',
          border: 'rgba(16, 185, 129, 0.25)',
        },
        bearish: {
          DEFAULT: '#f43f5e',
          light: '#fb7185',
          dark: '#881337',
          bg: 'rgba(244, 63, 94, 0.1)',
          border: 'rgba(244, 63, 94, 0.25)',
        },
        neutralScore: {
          DEFAULT: '#f59e0b',
          light: '#fbbf24',
          dark: '#78350f',
          bg: 'rgba(245, 158, 11, 0.1)',
          border: 'rgba(245, 158, 11, 0.25)',
        },
        accent: {
          blue: '#3b82f6',
          cyan: '#06b6d4',
          indigo: '#6366f1',
        }
      },
      boxShadow: {
        'glow-sm': '0 0 15px -3px rgba(59, 130, 246, 0.2)',
        'glow-md': '0 0 25px -5px rgba(59, 130, 246, 0.25)',
        'card': '0 4px 20px -2px rgba(0, 0, 0, 0.5)',
      }
    },
  },
  plugins: [],
}
