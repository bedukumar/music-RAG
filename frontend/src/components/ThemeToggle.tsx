import { Sun, Moon } from 'lucide-react';
import { useTheme } from '../hooks/useTheme';

export default function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const isDark = theme === 'dark';

  return (
    <button
      onClick={toggle}
      title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        width: '100%',
        height: 30,
        padding: '0 8px',
        borderRadius: 'var(--r-2)',
        background: 'transparent',
        border: 'none',
        cursor: 'pointer',
        color: 'var(--text-2)',
        fontFamily: 'var(--font)',
        fontSize: 13,
        fontWeight: 450,
        letterSpacing: '-0.01em',
        transition: 'color var(--t-fast), background var(--t-fast)',
        flexShrink: 0,
        textAlign: 'left',
      }}
      onMouseEnter={e => {
        (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-2)';
        (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-1)';
      }}
      onMouseLeave={e => {
        (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
        (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-2)';
      }}
    >
      {isDark
        ? <Sun  size={14} strokeWidth={2} />
        : <Moon size={14} strokeWidth={2} />
      }
      {isDark ? 'Light mode' : 'Dark mode'}
    </button>
  );
}
