import { Outlet } from 'react-router-dom';
import { Bell, Menu, Moon, Sun } from 'lucide-react';
import { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import AppSidebar from '../components/common/AppSidebar';
import AdminSidebar from '../components/common/AdminSidebar';
import { useTheme } from '../hooks/useTheme';

export default function MainLayout() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const { theme, toggleTheme } = useTheme();
  return (
    <div className="min-h-screen bg-page">
      {user?.role === 'admin' ? <AdminSidebar open={open} onClose={() => setOpen(false)} /> : <AppSidebar open={open} onClose={() => setOpen(false)} />}
      <main className={user ? 'lg:pl-72' : ''}>
        {user && <header className="app-header"><button onClick={() => setOpen(true)} className="icon-button lg:hidden" aria-label="Open navigation"><Menu size={20} /></button><div className="hidden sm:block"><p className="eyebrow">GlassBox / decision workspace</p><p className="header-date">{new Intl.DateTimeFormat('en-IN', { dateStyle: 'full' }).format(new Date())}</p></div><div className="header-actions"><button onClick={toggleTheme} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`} className="icon-button">{theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}</button><button aria-label="Notifications" className="icon-button relative"><Bell size={19} /><span className="notification-dot" /></button></div></header>}
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-7 sm:py-8">
        <Outlet />
      </div></main>
    </div>
  );
}
