import { Outlet } from 'react-router-dom';
import { Bell, Menu, Moon, Sun } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import AppSidebar from '../components/common/AppSidebar';
import AdminSidebar from '../components/common/AdminSidebar';
import { useTheme } from '../hooks/useTheme';
import { notificationApi } from '../services/api';
import type { UserNotification } from '../types';

export default function MainLayout() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [notificationsMounted, setNotificationsMounted] = useState(false);
  const [notifications, setNotifications] = useState<UserNotification[]>([]);
  const [notificationError, setNotificationError] = useState<string | null>(null);
  const notificationAnchor = useRef<HTMLDivElement>(null);
  const closeTimer = useRef<number | undefined>(undefined);
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    if (!user) { setNotifications([]); return; }
    let active = true;
    notificationApi.list().then(items => { if (active) setNotifications(items); }).catch(() => {
      if (active) setNotificationError('Could not load notifications.');
    });
    return () => { active = false; };
  }, [user?.id]);

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
    notificationApi.list().then(setNotifications).catch(() => setNotificationError('Could not load notifications.'));
    if (window.requestAnimationFrame) window.requestAnimationFrame(() => setNotificationsOpen(true));
    else window.setTimeout(() => setNotificationsOpen(true), 16);
  }, [notificationsOpen, closeNotifications]);

  const markNotificationRead = async (notification: UserNotification) => {
    if (notification.is_read) return;
    try {
      const updated = await notificationApi.markRead(notification.id);
      setNotifications(current => current.map(item => item.id === updated.id ? updated : item));
    } catch {
      setNotificationError('Could not update this notification.');
    }
  };

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
        {user && <header className="app-header"><button onClick={() => setOpen(true)} className="icon-button lg:hidden" aria-label="Open navigation"><Menu size={20} /></button><div className="hidden sm:block"><p className="eyebrow">GlassBox / decision workspace</p><p className="header-date">{new Intl.DateTimeFormat('en-IN', { dateStyle: 'full' }).format(new Date())}</p></div><div className="header-actions"><button onClick={toggleTheme} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`} className="icon-button">{theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}</button><div className="notification-anchor" ref={notificationAnchor}><button onClick={toggleNotifications} aria-label="Notifications" aria-haspopup="dialog" aria-expanded={notificationsOpen} aria-controls="notification-popover" className="icon-button relative"><Bell size={19} />{notifications.filter(item => !item.is_read).length > 0 && <span className="notification-badge">{notifications.filter(item => !item.is_read).length}</span>}</button>{notificationsMounted && <section id="notification-popover" role="dialog" aria-label="Notifications" aria-live="polite" className={`notification-popover ${notificationsOpen ? 'is-open' : ''}`}><h2 className="notification-title">Notifications</h2>{notificationError && <p role="alert" className="mt-2 text-xs text-red-600">{notificationError}</p>}{notifications.length === 0 ? <p className="notification-empty">No new notifications.</p> : <ul className="mt-3 max-h-80 space-y-2 overflow-y-auto">{notifications.map(notification => { const tone = notification.decision_type === 'rejected' ? 'border-red-400 bg-red-50' : notification.decision_type === 'approved' ? 'border-green-400 bg-green-50' : 'border-slate-200 bg-slate-50'; return <li key={notification.id}><button type="button" onClick={() => markNotificationRead(notification)} className={`w-full rounded-r-lg border-l-4 p-3 text-left text-sm ${tone} ${notification.is_read ? 'opacity-75' : ''}`}><span className="block text-slate-800">{notification.message}</span><span className="mt-1 block text-xs text-slate-500">{notification.created_at ? new Date(notification.created_at).toLocaleString() : ''}{!notification.is_read && <span className="ml-2 font-semibold text-sky-700">Unread</span>}</span></button></li>; })}</ul>}</section>}</div></div></header>}
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-7 sm:py-8">
        <Outlet />
      </div></main>
    </div>
  );
}
