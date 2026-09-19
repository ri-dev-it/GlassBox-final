import { Routes, Route } from 'react-router-dom';
import MainLayout from '../layouts/MainLayout';
import ProtectedRoute from '../components/common/ProtectedRoute';
import Landing from '../pages/Landing/Landing';
import Login from '../pages/Login/Login';
import GoogleCallback from '../pages/Login/GoogleCallback';
import Register from '../pages/Register/Register';
import Application from '../pages/Application/Application';
import Results from '../pages/Results/Results';
import History from '../pages/History/History';
import Profile from '../pages/Profile/Profile';
import Admin from '../pages/Admin/Admin';
import Status from '../pages/Status/Status';
import Insights from '../pages/Insights/Insights';
import Settings from '../pages/Settings/Settings';
import About from '../pages/About/About';
import MerchantRisk from '../pages/MerchantRisk/MerchantRisk';
import Portfolio from '../pages/Portfolio/Portfolio';
import RiskAnalysis from '../pages/RiskAnalysis/RiskAnalysis';
import CreditAnalytics from '../pages/Analytics/CreditAnalytics';
import Reports from '../pages/Reports/Reports';

export default function AppRoutes() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/auth/google/callback" element={<GoogleCallback />} />
        <Route path="/register" element={<Register />} />
        <Route path="/apply" element={<ProtectedRoute><Application /></ProtectedRoute>} />
        <Route path="/merchant-risk" element={<ProtectedRoute><MerchantRisk /></ProtectedRoute>} />
        <Route path="/portfolio" element={<ProtectedRoute allowedRoles={['admin', 'loan_officer']}><Portfolio /></ProtectedRoute>} />
        <Route path="/results/:id" element={<ProtectedRoute><Results /></ProtectedRoute>} />
        <Route path="/history" element={<ProtectedRoute><History /></ProtectedRoute>} />
        <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
        <Route path="/status" element={<ProtectedRoute><Status /></ProtectedRoute>} />
        <Route path="/insights" element={<ProtectedRoute><Insights /></ProtectedRoute>} />
        <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
        <Route path="/about" element={<ProtectedRoute><About /></ProtectedRoute>} />
        <Route path="/analytics" element={<ProtectedRoute><CreditAnalytics /></ProtectedRoute>} />
        <Route path="/risk-analysis" element={<ProtectedRoute><RiskAnalysis /></ProtectedRoute>} />
        <Route path="/reports" element={<ProtectedRoute><Reports /></ProtectedRoute>} />
        <Route
          path="/admin"
          element={
            <ProtectedRoute allowedRoles={['admin']}>
              <Admin />
            </ProtectedRoute>
          }
        />
      </Route>
    </Routes>
  );
}
