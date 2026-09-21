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
import ReviewQueue from '../pages/Admin/ReviewQueue';
import ModelOps from '../pages/Admin/ModelOps';
import DocumentVerification from '../pages/Admin/DocumentVerification';

export default function AppRoutes() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route path="/" element={<ProtectedRoute><Landing /></ProtectedRoute>} />
        <Route path="/login" element={<Login />} />
        <Route path="/auth/google/callback" element={<GoogleCallback />} />
        <Route path="/register" element={<Register />} />
        <Route path="/apply" element={<ProtectedRoute allowedRoles={['applicant']}><Application /></ProtectedRoute>} />
        <Route path="/merchant-risk" element={<ProtectedRoute allowedRoles={['admin', 'loan_officer']}><MerchantRisk /></ProtectedRoute>} />
        <Route path="/portfolio" element={<ProtectedRoute allowedRoles={['admin', 'loan_officer']}><Portfolio /></ProtectedRoute>} />
        <Route path="/results/:id" element={<ProtectedRoute><Results /></ProtectedRoute>} />
        <Route path="/history" element={<ProtectedRoute allowedRoles={['applicant']}><History /></ProtectedRoute>} />
        <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
        <Route path="/status" element={<ProtectedRoute allowedRoles={['applicant']}><Status /></ProtectedRoute>} />
        <Route path="/insights" element={<ProtectedRoute allowedRoles={['applicant']}><Insights /></ProtectedRoute>} />
        <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
        <Route path="/about" element={<ProtectedRoute><About /></ProtectedRoute>} />
        <Route path="/analytics" element={<ProtectedRoute allowedRoles={['admin', 'loan_officer']}><CreditAnalytics /></ProtectedRoute>} />
        <Route path="/risk-analysis" element={<ProtectedRoute allowedRoles={['admin', 'loan_officer']}><RiskAnalysis /></ProtectedRoute>} />
        <Route path="/reports" element={<ProtectedRoute allowedRoles={['admin', 'loan_officer']}><Reports /></ProtectedRoute>} />
        <Route
          path="/admin"
          element={
            <ProtectedRoute allowedRoles={['admin']}>
              <Admin />
            </ProtectedRoute>
          }
        />
        <Route path="/admin/review" element={<ProtectedRoute allowedRoles={['admin']}><ReviewQueue /></ProtectedRoute>} />
        <Route path="/admin/model-ops" element={<ProtectedRoute allowedRoles={['admin']}><ModelOps /></ProtectedRoute>} />
        <Route path="/admin/documents" element={<ProtectedRoute allowedRoles={['admin']}><DocumentVerification /></ProtectedRoute>} />
      </Route>
    </Routes>
  );
}
