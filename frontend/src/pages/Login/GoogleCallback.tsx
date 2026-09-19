import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { dashboardPath } from '../../utils/roleAccess';

export default function GoogleCallback() {
  const { completeGoogleLogin } = useAuth();
  const [params] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    const token = params.get('token');
    if (!token) {
      navigate('/login?error=Google%20sign-in%20could%20not%20be%20completed.', { replace: true });
      return;
    }
    completeGoogleLogin(token)
      .then((user) => navigate(dashboardPath(user.role), { replace: true }))
      .catch(() => navigate('/login?error=Google%20sign-in%20could%20not%20be%20completed.', { replace: true }));
  }, [completeGoogleLogin, navigate, params]);

  return <div className="py-20 text-center text-sm text-slate-600">Completing Google sign-in…</div>;
}
