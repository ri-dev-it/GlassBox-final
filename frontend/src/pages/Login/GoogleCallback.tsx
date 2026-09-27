import { useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { isAxiosError } from 'axios';
import { useAuth } from '../../hooks/useAuth';
import { dashboardPath } from '../../utils/roleAccess';

export default function GoogleCallback() {
  const { completeGoogleLogin } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const token = new URLSearchParams(location.hash.slice(1)).get('token');
    if (!token) {
      navigate('/login?error=Google%20sign-in%20could%20not%20be%20completed.', { replace: true });
      return;
    }
    window.history.replaceState(null, '', location.pathname);
    completeGoogleLogin(token)
      .then((user) => navigate(dashboardPath(user.role), { replace: true }))
      .catch((error) => {
        const message = isAxiosError(error) && !error.response
          ? 'Unable to connect to the server.'
          : 'Unable to authenticate with Google. Please try again.';
        navigate(`/login?${new URLSearchParams({ error: message })}`, { replace: true });
      });
  }, [completeGoogleLogin, navigate, location.hash]);

  return <div className="py-20 text-center text-sm text-slate-600">Completing Google sign-in…</div>;
}
