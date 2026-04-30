import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
    "./hooks/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        'raksha': {
          50: '#EFF6FF', 100: '#DBEAFE', 200: '#BFDBFE', 300: '#93C5FD',
          400: '#60A5FA', 500: '#3B82F6', 600: '#2563EB', 700: '#1D4ED8',
          800: '#1E40AF', 900: '#1E3A8A', 950: '#172554',
        },
        'accent': {
          50: '#F5F3FF', 100: '#EDE9FE', 200: '#DDD6FE', 300: '#C4B5FD',
          400: '#A78BFA', 500: '#8B5CF6', 600: '#7C3AED', 700: '#6D28D9',
          800: '#5B21B6', 900: '#4C1D95', 950: '#2E1065',
        },
        'danger': {
          50: '#fff1f1', 100: '#ffe0e0', 200: '#ffc7c7', 300: '#ff9e9e',
          400: '#ff6464', 500: '#ff2d2d', 600: '#ed0f0f', 700: '#c80808',
          800: '#a50b0b', 900: '#881111', 950: '#4b0303',
        },
        'warning': {
          50: '#fffbeb', 100: '#fff3c6', 200: '#ffe588', 300: '#ffd14a',
          400: '#ffbd20', 500: '#f99b07', 600: '#dd7302', 700: '#b74f06',
          800: '#943c0c', 900: '#7a330d', 950: '#461902',
        },
        'safe': {
          50: '#edfcf2', 100: '#d3f9e0', 200: '#aaf0c6', 300: '#73e3a5',
          400: '#3bce7f', 500: '#17b363', 600: '#0b9150', 700: '#097441',
          800: '#0b5c36', 900: '#0a4b2e', 950: '#032a19',
        },
        'surface': {
          50: '#F9FAFB', 100: '#F3F4F6', 200: '#E5E7EB', 300: '#D1D5DB',
          400: '#9CA3AF', 500: '#6B7280', 600: '#4B5563', 700: '#374151',
          800: '#1F2937', 900: '#111827', 950: '#0B0F19',
        },
      },
      fontFamily: {
        'sans': ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        'mono': ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'pulse-danger': 'pulse-danger 1s ease-in-out infinite',
        'slide-up': 'slide-up 0.3s ease-out',
        'slide-down': 'slide-down 0.3s ease-out',
        'fade-in': 'fade-in 0.3s ease-out',
        'glow': 'glow 2s ease-in-out infinite',
        'emergency-flash': 'emergency-flash 0.5s ease-in-out infinite',
      },
      keyframes: {
        'pulse-danger': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.5' },
        },
        'slide-up': {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        'slide-down': {
          '0%': { transform: 'translateY(-10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'glow': {
          '0%, 100%': { boxShadow: '0 0 5px rgba(255, 45, 45, 0.3)' },
          '50%': { boxShadow: '0 0 20px rgba(255, 45, 45, 0.6)' },
        },
        'emergency-flash': {
          '0%, 100%': { backgroundColor: 'rgba(255, 45, 45, 0.9)' },
          '50%': { backgroundColor: 'rgba(200, 8, 8, 0.95)' },
        },
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
};

export default config;
