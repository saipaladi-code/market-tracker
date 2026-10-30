import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Outlet, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute, PublicRoute } from './components/ProtectedRoute';
import { Sidebar } from './components/Sidebar';
import { Navbar } from './components/Navbar';
import { LoginPage } from './pages/LoginPage';
import { SignupPage } from './pages/SignupPage';
import { ForgotPasswordPage } from './pages/ForgotPasswordPage';
import { ResetPasswordPage } from './pages/ResetPasswordPage';
import { DashboardPage } from './pages/DashboardPage';
import { LiveAnalysisPage } from './pages/LiveAnalysisPage';
import { NewsExplorerPage } from './pages/NewsExplorerPage';
import { CompanyAnalysisPage } from './pages/CompanyAnalysisPage';
import { ConflictDetectorPage } from './pages/ConflictDetectorPage';
import { SectorHeatmapPage } from './pages/SectorHeatmapPage';
import { AlertsHistoryPage } from './pages/AlertsHistoryPage';
import { DataQualityPage } from './pages/DataQualityPage';
import { AssistantPage } from './pages/AssistantPage';
import { GoldSilverIntelligencePage } from './pages/GoldSilverIntelligencePage';
import { BackendConfigModal } from './components/BackendConfigModal';
import { api } from './services/api';

function AuthenticatedLayout() {
  const [healthData, setHealthData] = useState<any>(null);
  const [lastRefreshed, setLastRefreshed] = useState<string>(new Date().toISOString());
  const [isCollapsed, setIsCollapsed] = useState<boolean>(false);
  const [mobileOpen, setMobileOpen] = useState<boolean>(false);
  const [feedStatus, setFeedStatus] = useState<string>('LIVE FEED');
  const [activeConflictsCount, setActiveConflictsCount] = useState<number>(0);
  const [unreadAlertsCount, setUnreadAlertsCount] = useState<number>(0);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [showBackendModal, setShowBackendModal] = useState<boolean>(false);

  const checkHealthAndStats = async () => {
    try {
      const [health, dashboardStats, unreadAlerts] = await Promise.allSettled([
        api.getHealth(),
        api.getDashboardStats(),
        api.getAlerts(true),
      ]);

      if (health.status === 'fulfilled') {
        setHealthData(health.value);
        if (health.value?.news_api?.feed_status) {
          setFeedStatus(health.value.news_api.feed_status);
        }
      }
      if (dashboardStats.status === 'fulfilled') {
        setActiveConflictsCount(dashboardStats.value.active_conflicts_count || 0);
        if (dashboardStats.value.feed_status) {
          setFeedStatus(dashboardStats.value.feed_status);
        }
      }
      if (unreadAlerts.status === 'fulfilled') {
        setUnreadAlertsCount(unreadAlerts.value.length || 0);
      }
    } catch (err) {
      console.warn('Backend sync check error:', err);
    }
  };

  useEffect(() => {
    checkHealthAndStats();
  }, []);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 3500);
  };

  const handleGlobalRefresh = async () => {
    try {
      const res = await api.refreshNews();
      setLastRefreshed(new Date().toISOString());
      if (res.feed_status) {
        setFeedStatus(res.feed_status);
      }
      await checkHealthAndStats();
      showToast(`Refreshed ${res.articles_count || 0} articles & synchronized sentiment metrics.`);
    } catch (err: any) {
      console.error('Refresh failed:', err);
      showToast('Ingestion refresh failed. Check backend connection.');
    }
  };

  const isDemo =
    feedStatus === 'DEMO DATA' ||
    (Boolean(healthData?.news_api?.status?.includes('Demo')) && !healthData?.news_api?.status?.includes('Connected'));
  const modelStatus = healthData?.model?.status || 'ready';

  return (
    <div className="flex min-h-screen bg-navy-950 text-slate-100 selection:bg-blue-600 selection:text-white antialiased font-sans">
      {/* Navigation Sidebar */}
      <Sidebar
        modelStatus={modelStatus}
        isDemo={isDemo}
        feedStatus={feedStatus}
        isCollapsed={isCollapsed}
        setIsCollapsed={setIsCollapsed}
        mobileOpen={mobileOpen}
        setMobileOpen={setMobileOpen}
        activeConflictsCount={activeConflictsCount}
        unreadAlertsCount={unreadAlertsCount}
        onOpenBackendSettings={() => setShowBackendModal(true)}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <Navbar
          lastUpdated={lastRefreshed}
          isDemo={isDemo}
          feedStatus={feedStatus}
          onRefresh={handleGlobalRefresh}
          onOpenMobileMenu={() => setMobileOpen(true)}
          onOpenBackendSettings={() => setShowBackendModal(true)}
        />

        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto overflow-y-auto">
          <Outlet />
        </main>

        {/* Toast Notification Pill */}
        {toastMessage && (
          <div className="fixed bottom-6 right-6 z-50 bg-navy-800 text-white px-4 py-2.5 rounded-xl border border-navy-750 shadow-2xl flex items-center gap-2 text-xs font-medium animate-in slide-in-from-bottom duration-200">
            <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
            <span>{toastMessage}</span>
          </div>
        )}

        {/* Backend Configuration Modal */}
        <BackendConfigModal
          isOpen={showBackendModal}
          onClose={() => setShowBackendModal(false)}
          onSave={checkHealthAndStats}
        />
      </div>
    </div>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public Authentication Routes */}
          <Route
            path="/login"
            element={
              <PublicRoute>
                <LoginPage />
              </PublicRoute>
            }
          />
          <Route
            path="/signup"
            element={
              <PublicRoute>
                <SignupPage />
              </PublicRoute>
            }
          />
          <Route
            path="/forgot-password"
            element={
              <PublicRoute>
                <ForgotPasswordPage />
              </PublicRoute>
            }
          />
          <Route
            path="/reset-password"
            element={
              <PublicRoute>
                <ResetPasswordPage />
              </PublicRoute>
            }
          />

          {/* Protected Application Routes */}
          <Route
            element={
              <ProtectedRoute>
                <AuthenticatedLayout />
              </ProtectedRoute>
            }
          >
            <Route path="/" element={<DashboardPage />} />
            <Route path="/analyze" element={<LiveAnalysisPage />} />
            <Route path="/metals" element={<GoldSilverIntelligencePage />} />
            <Route path="/news" element={<NewsExplorerPage />} />
            <Route path="/companies" element={<CompanyAnalysisPage />} />
            <Route path="/conflicts" element={<ConflictDetectorPage />} />
            <Route path="/sectors" element={<SectorHeatmapPage />} />
            <Route path="/alerts" element={<AlertsHistoryPage />} />
            <Route path="/data-quality" element={<DataQualityPage />} />
            <Route path="/assistant" element={<AssistantPage />} />
          </Route>

          {/* Catch-all Redirect */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
