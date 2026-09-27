/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        approved: {
          DEFAULT: 'var(--approved)',
          soft: 'var(--approved-soft)',
          solid: 'var(--approved-button)',
        },
        review: {
          DEFAULT: 'var(--review)',
          soft: 'var(--review-soft)',
          solid: 'var(--review-button)',
        },
        rejected: {
          DEFAULT: 'var(--rejected)',
          soft: 'var(--rejected-soft)',
          solid: 'var(--rejected-button)',
        },
        loan: {
          1: 'var(--loan-1)',
          2: 'var(--loan-2)',
          3: 'var(--loan-3)',
          4: 'var(--loan-4)',
          5: 'var(--loan-5)',
          6: 'var(--loan-6)',
        },
        brand: {
          50: 'var(--brand-50)',
          100: 'var(--brand-100)',
          200: 'var(--brand-200)',
          500: 'var(--brand-500)',
          600: 'var(--brand-600)',
          700: 'var(--brand-700)',
          800: 'var(--brand-800)',
          900: 'var(--brand-900)',
        },
        blue: { 800: 'var(--brand-gradient-mid)' },
        sky: { 600: 'var(--brand-gradient-end)' },
      },
    },
  },
  plugins: [],
};
