import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import ReviewQueue from './pages/ReviewQueue';
import ApplicationDetail from './pages/ApplicationDetail';
import CoverageMap from './pages/CoverageMap';
import Analytics from './pages/Analytics';
import DBTMonitor from './pages/DBTMonitor';
import StudentLookup from './pages/StudentLookup';
import StudentPortal from './pages/StudentPortal';

import { LanguageProvider } from './context/LanguageContext';

function App() {
  return (
    <LanguageProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="student" element={<StudentPortal />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="review-queue" element={<ReviewQueue />} />
            <Route path="application/:id" element={<ApplicationDetail />} />
            <Route path="coverage-map" element={<CoverageMap />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="dbt-monitor" element={<DBTMonitor />} />
            <Route path="student-lookup" element={<StudentLookup />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </LanguageProvider>
  );
}

export default App;
