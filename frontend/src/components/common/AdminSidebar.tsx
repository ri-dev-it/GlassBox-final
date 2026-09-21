import { BarChart3, ClipboardList, FileCheck2, FileText, History, LayoutDashboard, LogOut, Settings, ShieldAlert, Store, X } from 'lucide-react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

const groups = [
  { label: 'Review Queue', links: [{ to: '/admin/review', label: 'Review Queue', icon: ClipboardList }] },
  { label: 'Risk & Portfolio', links: [{ to: '/merchant-risk', label: 'Merchant Risk', icon: Store }, { to: '/portfolio', label: 'Portfolio Overview', icon: BarChart3 }, { to: '/risk-analysis', label: 'Risk Analysis', icon: ShieldAlert }] },
  { label: 'Model Ops', links: [{ to: '/analytics', label: 'Credit Analytics', icon: BarChart3 }, { to: '/admin/model-ops', label: 'Model Versions & A/B Testing', icon: History }] },
  { label: 'Reports & Verification', links: [{ to: '/reports', label: 'Reports', icon: FileText }, { to: '/admin/documents', label: 'Document Verification', icon: FileCheck2 }] },
];

export default function AdminSidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  if (!user || user.role !== 'admin') return null;
  return <>
    <div onClick={onClose} className={`fixed inset-0 z-30 bg-slate-950/40 lg:hidden ${open ? 'block' : 'hidden'}`} />
    <aside className={`app-sidebar fixed inset-y-0 left-0 z-40 flex w-72 -translate-x-full flex-col px-4 py-5 transition-transform lg:translate-x-0 ${open ? 'translate-x-0' : ''}`}>
      <button onClick={onClose} aria-label="Close navigation" className="absolute right-4 top-5 lg:hidden"><X size={20} /></button>
      <NavLink to="/admin" className="brand-lockup px-3"><p className="text-xl font-bold tracking-tight">GLASS<span>BOX</span></p><p className="mt-1 text-xs">Admin decision workspace</p></NavLink>
      <nav className="mt-8 flex-1 space-y-6 overflow-y-auto">
        <NavLink to="/admin" end onClick={onClose} className={({ isActive }) => `sidebar-primary-link ${isActive ? 'is-active' : ''}`}><LayoutDashboard size={19} /><span>Admin Overview</span></NavLink>
        {groups.map(({ label, links }) => <section key={label}><p className="sidebar-group">{label}</p><div className="space-y-1">{links.map(({ to, label: linkLabel, icon: Icon }) => <NavLink key={to} to={to} onClick={onClose} className={({ isActive }) => `sidebar-link ${isActive ? 'is-active' : ''}`}><Icon size={17} />{linkLabel}</NavLink>)}</div></section>)}
        <section><p className="sidebar-group">Workspace</p><NavLink to="/settings" onClick={onClose} className={({ isActive }) => `sidebar-link ${isActive ? 'is-active' : ''}`}><Settings size={17} />Settings</NavLink></section>
      </nav>
      <div className="sidebar-profile"><div className="flex items-center gap-3 px-2 py-2"><div className="avatar">{user.full_name.charAt(0).toUpperCase()}</div><div className="min-w-0"><p className="truncate text-sm font-medium">{user.full_name}</p><p className="sidebar-role">Administrator</p></div></div><button onClick={() => { logout(); navigate('/login'); }} className="sidebar-logout"><LogOut size={17} />Logout</button></div>
    </aside>
  </>;
}
