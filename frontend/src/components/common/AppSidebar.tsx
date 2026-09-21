import { BarChart3, Brain, CircleHelp, ClipboardCheck, FilePlus2, FileText, History, Home, LogOut, Settings, ShieldAlert, Store, X } from 'lucide-react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import type { Role } from '../../types';

const primaryLinks: Array<{ to: string; label: string; icon: typeof Home; roles: Role[] }> = [
  { to: '/', label: 'Dashboard', icon: Home, roles: ['applicant', 'loan_officer', 'admin'] },
  { to: '/apply', label: 'New Application', icon: FilePlus2, roles: ['applicant', 'client'] },
  { to: '/status', label: 'Application Status', icon: ClipboardCheck, roles: ['applicant', 'client'] },
  { to: '/history', label: 'History', icon: History, roles: ['applicant', 'client'] },
  { to: '/insights', label: 'AI Insights', icon: Brain, roles: ['applicant', 'client'] },
  { to: '/analytics', label: 'Analytics', icon: BarChart3, roles: ['loan_officer', 'admin'] },
];

const roleGroups = [
  { group: 'Applicant / Client', roles: ['applicant', 'client'], links: [{ to: '/apply', label: 'New Application', icon: FilePlus2 }, { to: '/status', label: 'Application Status', icon: ClipboardCheck }, { to: '/history', label: 'Application History', icon: History }] },
  { group: 'Admin / Bank', roles: ['loan_officer', 'admin'], links: [{ to: '/merchant-risk', label: 'Merchant Risk', icon: Store }, { to: '/portfolio', label: 'Portfolio Overview', icon: BarChart3 }, { to: '/risk-analysis', label: 'Risk Analysis', icon: ShieldAlert }, { to: '/reports', label: 'Reports', icon: FileText }] },
  { group: 'Administration', roles: ['admin'], links: [{ to: '/admin', label: 'Admin Review', icon: ShieldAlert }] },
];

export default function AppSidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  if (!user) return null;
  return <>
    <div onClick={onClose} className={`fixed inset-0 z-30 bg-slate-950/40 lg:hidden ${open ? 'block' : 'hidden'}`} />
    <aside className={`app-sidebar fixed inset-y-0 left-0 z-40 flex w-72 -translate-x-full flex-col px-4 py-5 transition-transform lg:translate-x-0 ${open ? 'translate-x-0' : ''}`}>
      <button onClick={onClose} aria-label="Close navigation" className="absolute right-4 top-5 lg:hidden"><X size={20} /></button>
      <NavLink to="/" className="brand-lockup px-3"><p className="text-xl font-bold tracking-tight">GLASS<span>BOX</span></p><p className="mt-1 text-xs">Explainable credit</p></NavLink>
      <nav className="mt-8 flex-1 space-y-6 overflow-y-auto">
        <div className="sidebar-primary-grid">{primaryLinks.filter(({ roles }) => roles.includes(user.role)).map(({ to, label, icon: Icon }) => <NavLink end={to === '/'} onClick={onClose} key={to} to={to} className={({ isActive }) => `sidebar-primary-link ${isActive ? 'is-active' : ''}`}><Icon size={19} /><span>{label}</span></NavLink>)}</div>
        {roleGroups.filter(({ roles }) => roles.includes(user.role)).map(({ group, links }) => <section key={group}><p className="sidebar-group">{group}</p><div className="space-y-1">{links.map(({ to, label, icon: Icon }) => <NavLink end={to === '/'} onClick={onClose} key={to} to={to} className={({ isActive }) => `sidebar-link ${isActive ? 'is-active' : ''}`}><Icon size={17} />{label}</NavLink>)}</div></section>)}
        <section><p className="sidebar-group">Workspace</p><div className="space-y-1"><NavLink onClick={onClose} to="/settings" className={({ isActive }) => `sidebar-link ${isActive ? 'is-active' : ''}`}><Settings size={17} />Settings</NavLink><NavLink onClick={onClose} to="/about" className={({ isActive }) => `sidebar-link ${isActive ? 'is-active' : ''}`}><CircleHelp size={17} />Help & About</NavLink></div></section>
      </nav>
      <div className="sidebar-profile"><NavLink to="/settings" className="flex items-center gap-3 rounded-lg px-2 py-2"><div className="avatar">{user.full_name.charAt(0).toUpperCase()}</div><div className="min-w-0"><p className="truncate text-sm font-medium">{user.full_name}</p><p className="sidebar-role">{user.role.replace('_', ' ')}</p></div></NavLink><button onClick={() => { logout(); navigate('/login'); }} className="sidebar-logout"><LogOut size={17} />Logout</button></div>
    </aside>
  </>;
}
