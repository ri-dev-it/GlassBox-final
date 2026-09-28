import { useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import {
  BarChart3, Bell, Brain, ChevronDown, ClipboardCheck,
  ClipboardList, FileCheck2, FilePlus2, FileText, History, Home,
  LayoutDashboard, LogOut, Menu, Moon, Settings, ShieldAlert, Store, Sun, X,
  CircleHelp,
  type LucideIcon,
} from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { useTheme } from '../../hooks/useTheme';
import { notificationApi } from '../../services/api';
import type { Role, UserNotification } from '../../types';

type Leaf = { kind: 'link'; to: string; label: string; icon: LucideIcon };
type Group = { kind: 'group'; label: string; icon: LucideIcon; items: Leaf[] };
type Entry = Leaf | Group;
type MenuItem = Leaf | { kind: 'action'; label: string; icon: LucideIcon; action: () => void };

const leaf = (to: string, label: string, icon: LucideIcon): Leaf => ({ kind: 'link', to, label, icon });

function navigationFor(role: Role): Entry[] {
  if (role === 'admin') return [
    leaf('/admin', 'Admin Overview', LayoutDashboard),
    leaf('/admin/review', 'Review Queue', ClipboardList),
    { kind: 'group', label: 'Risk & Portfolio', icon: ShieldAlert, items: [leaf('/merchant-risk', 'Merchant Risk', Store), leaf('/portfolio', 'Portfolio Overview', BarChart3), leaf('/risk-analysis', 'Risk Analysis', ShieldAlert)] },
    { kind: 'group', label: 'Model Ops', icon: History, items: [leaf('/analytics', 'Credit Analytics', BarChart3), leaf('/admin/model-ops', 'Model Versions & A/B Testing', History)] },
    { kind: 'group', label: 'Reports & Verification', icon: FileCheck2, items: [leaf('/reports', 'Reports', FileText), leaf('/admin/documents', 'Document Verification', FileCheck2)] },
  ];
  if (role === 'loan_officer') return [
    leaf('/', 'Dashboard', Home),
    leaf('/analytics', 'Analytics', BarChart3),
    { kind: 'group', label: 'Risk & Portfolio', icon: ShieldAlert, items: [leaf('/merchant-risk', 'Merchant Risk', Store), leaf('/portfolio', 'Portfolio Overview', BarChart3), leaf('/risk-analysis', 'Risk Analysis', ShieldAlert)] },
    { kind: 'group', label: 'Reports', icon: FileText, items: [leaf('/reports', 'Reports', FileText)] },
  ];
  return [
    leaf('/', 'Dashboard', Home),
    leaf('/apply', 'New Application', FilePlus2),
    leaf('/status', 'Application Status', ClipboardCheck),
    leaf('/history', 'History', History),
    { kind: 'group', label: 'More', icon: ChevronDown, items: [leaf('/insights', 'AI Insights', Brain), leaf('/history', 'Application History', History)] },
  ];
}

function isEntryActive(entry: Entry, pathname: string) {
  const matches = (to: string) => to === '/' ? pathname === '/' : pathname === to || pathname.startsWith(`${to}/`);
  return entry.kind === 'link' ? matches(entry.to) : entry.items.some(item => matches(item.to));
}

function MenuDropdown({ label, icon: Icon, active, items, children, onSelect }: {
  label: string; icon?: LucideIcon; active?: boolean; items: MenuItem[]; children?: ReactNode; onSelect?: () => void;
}) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const itemRefs = useRef<Array<HTMLAnchorElement | HTMLButtonElement | null>>([]);
  const close = useCallback(() => setOpen(false), []);
  const desktopHover = () => window.matchMedia?.('(hover: hover) and (pointer: fine)').matches;
  const focusItem = (index: number) => itemRefs.current[index]?.focus();
  const cycleItems = (event: KeyboardEvent<HTMLAnchorElement | HTMLButtonElement>, index: number) => {
    if (event.key === 'Escape') { event.preventDefault(); close(); trigger.current?.focus(); return; }
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      const step = event.key === 'ArrowDown' ? 1 : -1;
      focusItem((index + step + items.length) % items.length);
    }
  };

  useEffect(() => {
    if (!open) return;
    const outside = (event: PointerEvent) => { if (!root.current?.contains(event.target as Node)) close(); };
    const escape = (event: globalThis.KeyboardEvent) => { if (event.key === 'Escape') { close(); trigger.current?.focus(); } };
    document.addEventListener('pointerdown', outside);
    document.addEventListener('keydown', escape);
    return () => { document.removeEventListener('pointerdown', outside); document.removeEventListener('keydown', escape); };
  }, [open, close]);

  return <div ref={root} className="nav-menu-root" onMouseEnter={() => { if (desktopHover()) setOpen(true); }} onMouseLeave={() => { if (desktopHover()) close(); }} onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) close(); }}>
    <button ref={trigger} type="button" className={`nav-trigger ${active ? 'is-active' : ''}`} aria-haspopup="menu" aria-expanded={open} aria-label={label} onClick={() => setOpen(value => !value)} onKeyDown={event => {
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') { event.preventDefault(); setOpen(true); window.setTimeout(() => focusItem(event.key === 'ArrowDown' ? 0 : items.length - 1), 0); }
      if (event.key === 'Escape') close();
    }}>{children ?? <>{Icon && <Icon size={17} />}<span>{label}</span></>}<ChevronDown size={15} className={`nav-chevron ${open ? 'is-open' : ''}`} /></button>
    <div className={`nav-dropdown ${open ? 'is-open' : ''}`} role="menu" aria-label={label} aria-hidden={!open}>
      {items.map((item, index) => {
        const ItemIcon = item.icon;
        if (item.kind === 'action') return <button key={item.label} ref={node => { itemRefs.current[index] = node; }} type="button" role="menuitem" tabIndex={open ? 0 : -1} className="nav-dropdown-item" onClick={() => { item.action(); close(); onSelect?.(); }} onKeyDown={event => cycleItems(event, index)}><ItemIcon size={17}/><span>{item.label}</span></button>;
        return <NavLink key={`${item.to}-${item.label}`} ref={node => { itemRefs.current[index] = node; }} to={item.to} role="menuitem" tabIndex={open ? 0 : -1} className="nav-dropdown-item" onClick={() => { close(); onSelect?.(); }} onKeyDown={event => cycleItems(event, index)}><ItemIcon size={17}/><span>{item.label}</span></NavLink>;
      })}
    </div>
  </div>;
}

export default function TopNavbar() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [mobileGroups, setMobileGroups] = useState<string[]>([]);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [notificationsMounted, setNotificationsMounted] = useState(false);
  const [notifications, setNotifications] = useState<UserNotification[]>([]);
  const [notificationError, setNotificationError] = useState<string | null>(null);
  const notificationAnchor = useRef<HTMLDivElement>(null);
  const navbar = useRef<HTMLElement>(null);
  const mobilePanel = useRef<HTMLDivElement>(null);
  const mobileToggle = useRef<HTMLButtonElement>(null);
  const closeTimer = useRef<number | undefined>(undefined);
  const entries = useMemo(() => user ? navigationFor(user.role) : [], [user?.role]);

  useEffect(() => { setMobileOpen(false); setMobileGroups([]); }, [location.pathname]);
  useEffect(() => {
    if (!mobileOpen) return;
    const outside = (event: PointerEvent) => {
      const target = event.target as Node;
      if (!mobilePanel.current?.contains(target) && !mobileToggle.current?.contains(target)) setMobileOpen(false);
    };
    const escape = (event: globalThis.KeyboardEvent) => { if (event.key === 'Escape') { setMobileOpen(false); setMobileGroups([]); } };
    document.addEventListener('pointerdown', outside); document.addEventListener('keydown', escape);
    return () => { document.removeEventListener('pointerdown', outside); document.removeEventListener('keydown', escape); };
  }, [mobileOpen]);
  useEffect(() => {
    if (!user) { setNotifications([]); return; }
    let active = true;
    notificationApi.list().then(items => { if (active) setNotifications(items); }).catch(() => { if (active) setNotificationError('Could not load notifications.'); });
    return () => { active = false; };
  }, [user?.id]);

  const closeNotifications = useCallback(() => {
    setNotificationsOpen(false);
    window.clearTimeout(closeTimer.current);
    closeTimer.current = window.setTimeout(() => setNotificationsMounted(false), 210);
  }, []);
  const toggleNotifications = useCallback(() => {
    if (notificationsOpen) { closeNotifications(); return; }
    window.clearTimeout(closeTimer.current);
    setNotificationsMounted(true);
    notificationApi.list().then(setNotifications).catch(() => setNotificationError('Could not load notifications.'));
    if (window.requestAnimationFrame) window.requestAnimationFrame(() => setNotificationsOpen(true));
    else window.setTimeout(() => setNotificationsOpen(true), 16);
  }, [notificationsOpen, closeNotifications]);
  const markNotificationRead = async (notification: UserNotification) => {
    if (notification.is_read) return;
    try { const updated = await notificationApi.markRead(notification.id); setNotifications(current => current.map(item => item.id === updated.id ? updated : item)); }
    catch { setNotificationError('Could not update this notification.'); }
  };
  useEffect(() => {
    if (!notificationsMounted) return;
    const outside = (event: PointerEvent) => { if (!notificationAnchor.current?.contains(event.target as Node)) closeNotifications(); };
    const escape = (event: globalThis.KeyboardEvent) => { if (event.key === 'Escape') closeNotifications(); };
    document.addEventListener('pointerdown', outside); document.addEventListener('keydown', escape);
    return () => { document.removeEventListener('pointerdown', outside); document.removeEventListener('keydown', escape); };
  }, [notificationsMounted, closeNotifications]);
  useEffect(() => () => window.clearTimeout(closeTimer.current), []);

  const signOut = () => { logout(); navigate('/login'); };
  const profileItems: MenuItem[] = [
    leaf('/settings', 'Settings', Settings),
    ...(user?.role === 'admin' ? [] : [leaf('/about', 'Help & About', CircleHelp)]),
    { kind: 'action', label: 'Logout', icon: LogOut, action: signOut },
  ];

  const renderDesktopEntry = (entry: Entry) => {
    if (entry.kind === 'group') return <MenuDropdown key={entry.label} label={entry.label} icon={entry.icon} active={isEntryActive(entry, location.pathname)} items={entry.items}/>;
    const Icon = entry.icon;
    return <NavLink key={`${entry.to}-${entry.label}`} to={entry.to} end={entry.to === '/'} className={({ isActive }) => `nav-link ${isActive ? 'is-active' : ''}`}><Icon className="nav-link-icon" size={16}/><span>{entry.label}</span></NavLink>;
  };

  return <header ref={navbar} className="top-navbar">
    <div className="top-navbar-inner">
      <NavLink to={user?.role === 'admin' ? '/admin' : '/'} className="nav-logo" aria-label="GlassBox home"><span className="nav-logo-title">GLASS<span>BOX</span></span><span className="nav-logo-tagline">Explainable credit</span></NavLink>
      {user && <nav aria-label="Main navigation" className="nav-desktop">{entries.map(renderDesktopEntry)}</nav>}
      <div className="nav-actions">
        {user && <button type="button" onClick={toggleTheme} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`} className="icon-button nav-motion">{theme === 'dark' ? <Sun size={18}/> : <Moon size={18}/>}</button>}
        {user && <div className="notification-anchor" ref={notificationAnchor}><button onClick={toggleNotifications} aria-label="Notifications" aria-haspopup="dialog" aria-expanded={notificationsOpen} aria-controls="notification-popover" className="icon-button relative nav-motion"><Bell size={19}/>{notifications.filter(item => !item.is_read).length > 0 && <span className="notification-badge">{notifications.filter(item => !item.is_read).length}</span>}</button>{notificationsMounted && <section id="notification-popover" role="dialog" aria-label="Notifications" aria-live="polite" className={`notification-popover ${notificationsOpen ? 'is-open' : ''}`}><h2 className="notification-title">Notifications</h2>{notificationError && <p role="alert" className="mt-2 text-xs text-red-600">{notificationError}</p>}{notifications.length === 0 ? <p className="notification-empty">No new notifications.</p> : <ul className="mt-3 max-h-80 space-y-2 overflow-y-auto">{notifications.map(notification => { const tone = notification.decision_type === 'rejected' ? 'border-red-400 bg-red-50' : notification.decision_type === 'approved' ? 'border-green-400 bg-green-50' : 'border-slate-200 bg-slate-50'; return <li key={notification.id}><button type="button" onClick={() => markNotificationRead(notification)} className={`w-full rounded-r-lg border-l-4 p-3 text-left text-sm ${tone} ${notification.is_read ? 'opacity-75' : ''}`}><span className="block text-slate-800">{notification.message}</span><span className="mt-1 block text-xs text-slate-500">{notification.created_at ? new Date(notification.created_at).toLocaleString() : ''}{!notification.is_read && <span className="ml-2 font-semibold text-sky-700">Unread</span>}</span></button></li>; })}</ul>}</section>}</div>}
        {user && <MenuDropdown label="Profile menu" active={location.pathname === '/settings' || (user.role !== 'admin' && location.pathname === '/about')} items={profileItems} onSelect={() => setMobileOpen(false)}><span className="nav-profile-content"><span className="nav-avatar">{user.full_name.charAt(0).toUpperCase()}</span><span className="nav-profile-text"><strong>{user.full_name}</strong><small>{user.role === 'admin' ? 'Administrator' : user.role.replace('_', ' ')}</small></span></span></MenuDropdown>}
        {user && <button ref={mobileToggle} type="button" className={`icon-button nav-mobile-trigger nav-motion ${mobileOpen ? 'is-open' : ''}`} aria-label={mobileOpen ? 'Close navigation menu' : 'Open navigation menu'} aria-expanded={mobileOpen} aria-controls="mobile-navigation" onClick={() => setMobileOpen(value => !value)}>{mobileOpen ? <X size={20}/> : <Menu size={20}/>}</button>}
      </div>
    </div>
    {user && <div ref={mobilePanel} id="mobile-navigation" className={`nav-mobile-panel ${mobileOpen ? 'is-open' : ''}`} aria-hidden={!mobileOpen}>
      <nav aria-label="Mobile main navigation" className="nav-mobile-list">{entries.map(entry => entry.kind === 'link' ? <NavLink key={`${entry.to}-${entry.label}`} to={entry.to} end={entry.to === '/'} tabIndex={mobileOpen ? 0 : -1} className={({ isActive }) => `nav-mobile-link ${isActive ? 'is-active' : ''}`} onClick={() => setMobileOpen(false)}><entry.icon size={18}/><span>{entry.label}</span></NavLink> : <section key={entry.label} className="nav-mobile-group"><button type="button" tabIndex={mobileOpen ? 0 : -1} aria-expanded={mobileGroups.includes(entry.label)} className={`nav-mobile-group-trigger ${isEntryActive(entry, location.pathname) ? 'is-active' : ''}`} onClick={() => setMobileGroups(groups => groups.includes(entry.label) ? groups.filter(label => label !== entry.label) : [...groups, entry.label])}><entry.icon size={18}/><span>{entry.label}</span><ChevronDown size={16} className={`nav-chevron ${mobileGroups.includes(entry.label) ? 'is-open' : ''}`}/></button><div className={`nav-mobile-submenu ${mobileGroups.includes(entry.label) ? 'is-open' : ''}`}>{entry.items.map(item => <NavLink key={`${item.to}-${item.label}`} to={item.to} tabIndex={mobileOpen && mobileGroups.includes(entry.label) ? 0 : -1} className={({ isActive }) => `nav-mobile-link nav-mobile-subitem ${isActive ? 'is-active' : ''}`} onClick={() => setMobileOpen(false)}><item.icon size={17}/><span>{item.label}</span></NavLink>)}</div></section>)}</nav>
    </div>}
  </header>;
}
