import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import { AuthProvider } from './auth/AuthContext';
import { useAuth } from './auth/auth';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import ReviewQueue from './pages/ReviewQueue';
import Applications from './pages/Applications';
import ApplicationDetail from './pages/ApplicationDetail';
import CoverageMap from './pages/CoverageMap';
import Analytics from './pages/Analytics';
import DBTMonitor from './pages/DBTMonitor';
import DataRequests from './pages/DataRequests';
import DemoSms from './pages/DemoSms';
import ManageOfficers from './pages/ManageOfficers';
import MyWork from './pages/MyWork';
import WakingBanner from './components/WakingBanner';

function Home() {
  const { user } = useAuth();
  return <Navigate to={user ? '/my-work' : '/login'} replace />;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <WakingBanner />
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<Layout />}>
            <Route index element={<Home />} />
            <Route path="my-work" element={<MyWork />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="review-queue" element={<ReviewQueue />} />
            <Route path="applications" element={<Applications />} />
            <Route path="application/:id" element={<ApplicationDetail />} />
            <Route path="coverage-map" element={<CoverageMap />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="dbt-monitor" element={<DBTMonitor />} />
            <Route path="data-requests" element={<DataRequests />} />
            <Route path="demo-sms" element={<DemoSms />} />
            <Route path="manage-officers" element={<ManageOfficers />} />
            <Route path="*" element={<Home />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
