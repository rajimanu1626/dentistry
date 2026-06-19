import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: '#0E7C7B',
          dark: '#075E5D',
          light: '#34D1BF',
          50: '#ecfdfb',
          100: '#cffaf3',
          200: '#a0f2e7',
          300: '#67e4d6',
          400: '#34d1bf',
          500: '#15b3a4',
          600: '#0e7c7b',
          700: '#0f6364',
          800: '#114f51',
          900: '#124143',
          950: '#04282a',
        },
        accent: {
          DEFAULT: '#6366f1',
          light: '#a5b4fc',
          dark: '#4338ca',
        },
        ink: '#0f172a',
      },
      fontFamily: {
        sans: [
          'Inter var',
          'Inter',
          'ui-sans-serif',
          'system-ui',
          'sans-serif',
        ],
      },
      boxShadow: {
        soft: '0 1px 2px 0 rgb(15 23 42 / 0.04), 0 1px 3px 0 rgb(15 23 42 / 0.06)',
        card: '0 1px 3px 0 rgb(15 23 42 / 0.05), 0 8px 24px -12px rgb(15 23 42 / 0.12)',
        lift: '0 10px 30px -10px rgb(15 23 42 / 0.18)',
        glow: '0 8px 24px -8px rgb(14 124 123 / 0.45)',
      },
      borderRadius: {
        xl: '0.875rem',
        '2xl': '1.125rem',
        '3xl': '1.5rem',
      },
      backgroundImage: {
        'brand-gradient': 'linear-gradient(135deg, #0E7C7B 0%, #15b3a4 50%, #34D1BF 100%)',
        'mesh':
          'radial-gradient(60rem 60rem at 110% -10%, rgb(52 209 191 / 0.18), transparent 55%), radial-gradient(50rem 50rem at -10% 0%, rgb(99 102 241 / 0.12), transparent 50%)',
      },
      keyframes: {
        'fade-in-up': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
      animation: {
        'fade-in-up': 'fade-in-up 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
        'fade-in': 'fade-in 0.3s ease-out',
      },
    },
  },
  plugins: [],
} satisfies Config;
