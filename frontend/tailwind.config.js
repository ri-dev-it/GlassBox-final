/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        approved: '#3D7A5A',
        rejected: '#B34A52',
        brand: {
          50: '#EAF1F8',
          100: '#D7E5F3',
          500: '#3B82C4',
          600: '#2C5F9E',
          700: '#1E4B8C',
          900: '#173A6B',
        },
      },
    },
  },
  plugins: [],
};
