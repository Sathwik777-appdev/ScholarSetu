import { lazy, Suspense } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import { AuthProvider } from './auth/AuthContext';
import { useAuth } from './auth/auth';
import WakingBanner from './components/WakingBanner';
import ErrorBoundary from './components/ErrorBoundary';
import { Loading } from './components/States';
import { usePageTitle } from './hooks/usePageTitle';

// Each screen loads on first visit, so the first paint (the sign-in page) stays small.
const Login = lazy(() => import('./pages/Login'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const ReviewQueue = lazy(() => import('./pages/ReviewQueue'));
const Applications = lazy(() => import('./pages/Applications'));
const ApplicationDetail = lazy(() => import('./pages/ApplicationDetail'));
const CoverageMap = lazy(() => import('./pages/CoverageMap'));
const Analytics = lazy(() => import('./pages/Analytics'));
const DBTMonitor = lazy(() => import('./pages/DBTMonitor'));
const DataRequests = lazy(() => import('./pages/DataRequests'));
const DemoSms = lazy(() => import('./pages/DemoSms'));
const ManageOfficers = lazy(() => import('./pages/ManageOfficers'));
const MyWork = lazy(() => import('./pages/MyWork'));
const NotFound = lazy(() => import('./pages/NotFound'));

function Titles() {
  usePageTitle();
  return null;
}

function Home() {
  const { user } = useAuth();
  return <Navigate to={user ? '/my-work' : '/login'} replace />;
}

export default function App() {
  return (
    <ErrorBoundary>
    <AuthProvider>
      <BrowserRouter>
        <Titles />
        <WakingBanner />
        <Suspense fallback={<div className="p-8"><Loading /></div>}>
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
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
        </Suspense>
      </BrowserRouter>
    </AuthProvider>
    </ErrorBoundary>
  );
}
