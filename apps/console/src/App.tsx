import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import { ANALYTICS_ROLES, AuthProvider, useAuth } from './auth/AuthContext';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import ReviewQueue from './pages/ReviewQueue';
import Applications from './pages/Applications';
import ApplicationDetail from './pages/ApplicationDetail';
import CoverageMap from './pages/CoverageMap';
import Analytics from './pages/Analytics';
import DBTMonitor from './pages/DBTMonitor';

function Home() {
  const { user } = useAuth();
  return <Navigate to={user && ANALYTICS_ROLES.includes(user.role) ? '/dashboard' : '/review-queue'} replace />;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<Layout />}>
            <Route index element={<Home />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="review-queue" element={<ReviewQueue />} />
            <Route path="applications" element={<Applications />} />
            <Route path="application/:id" element={<ApplicationDetail />} />
            <Route path="coverage-map" element={<CoverageMap />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="dbt-monitor" element={<DBTMonitor />} />
            <Route path="*" element={<Home />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
