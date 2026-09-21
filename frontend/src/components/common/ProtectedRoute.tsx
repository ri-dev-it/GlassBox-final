import { Navigate } from 'react-router-dom';
import type { Role } from '../../types';
import { useAuth } from '../../hooks/useAuth';

interface Props {
  children: React.ReactNode;
  allowedRoles?: Role[];
}

export default function ProtectedRoute({ children, allowedRoles }: Props) {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="p-8 text-center text-slate-500">Loading…</div>;
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  const effectiveRole = user.role === 'client' ? 'applicant' : user.role;
  if (allowedRoles && !allowedRoles.includes(effectiveRole)) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}
