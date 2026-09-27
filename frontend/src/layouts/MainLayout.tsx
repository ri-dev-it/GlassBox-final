import { Outlet } from 'react-router-dom';
import { Bell, Menu, Moon, Sun } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import AppSidebar from '../components/common/AppSidebar';
import AdminSidebar from '../components/common/AdminSidebar';
import { useTheme } from '../hooks/useTheme';

export default function MainLayout() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [notificationsMounted, setNotificationsMounted] = useState(false);
  const notificationAnchor = useRef<HTMLDivElement>(null);
  const closeTimer = useRef<number | undefined>(undefined);
  const { theme, toggleTheme } = useTheme();

  const closeNotifications = useCallback(() => {
    setNotificationsOpen(false);
    window.clearTimeout(closeTimer.current);
    closeTimer.current = window.setTimeout(() => setNotificationsMounted(false), 210);
  }, []);

  const toggleNotifications = useCallback(() => {
    if (notificationsOpen) {
      closeNotifications();
      return;
    }
    window.clearTimeout(closeTimer.current);
    setNotificationsMounted(true);
    if (window.requestAnimationFrame) window.requestAnimationFrame(() => setNotificationsOpen(true));
    else window.setTimeout(() => setNotificationsOpen(true), 16);
  }, [notificationsOpen, closeNotifications]);

  useEffect(() => {
    if (!notificationsMounted) return;
    const handlePointerDown = (event: PointerEvent) => {
      if (!notificationAnchor.current?.contains(event.target as Node)) closeNotifications();
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closeNotifications();
    };
    document.addEventListener('pointerdown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [notificationsMounted, closeNotifications]);

  useEffect(() => () => window.clearTimeout(closeTimer.current), []);

  return (
    <div className="min-h-screen bg-page">
      {user?.role === 'admin' ? <AdminSidebar open={open} onClose={() => setOpen(false)} /> : <AppSidebar open={open} onClose={() => setOpen(false)} />}
      <main className={user ? 'lg:pl-72' : ''}>
        {user && <header className="app-header"><button onClick={() => setOpen(true)} className="icon-button lg:hidden" aria-label="Open navigation"><Menu size={20} /></button><div className="hidden sm:block"><p className="eyebrow">GlassBox / decision workspace</p><p className="header-date">{new Intl.DateTimeFormat('en-IN', { dateStyle: 'full' }).format(new Date())}</p></div><div className="header-actions"><button onClick={toggleTheme} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`} className="icon-button">{theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}</button><div className="notification-anchor" ref={notificationAnchor}><button onClick={toggleNotifications} aria-label="Notifications" aria-haspopup="dialog" aria-expanded={notificationsOpen} aria-controls="notification-popover" className="icon-button relative"><Bell size={19} /><span className="notification-dot" /></button>{notificationsMounted && <section id="notification-popover" role="dialog" aria-label="Notifications" aria-live="polite" className={`notification-popover ${notificationsOpen ? 'is-open' : ''}`}><h2 className="notification-title">Notifications</h2><p className="notification-empty">No new notifications.</p></section>}</div></div></header>}
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-7 sm:py-8">
        <Outlet />
      </div></main>
    </div>
  );
}
