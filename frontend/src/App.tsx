import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { Navbar } from './components/Navbar';
import { DashboardPage } from './pages/DashboardPage';
import { LiveAnalysisPage } from './pages/LiveAnalysisPage';
import { NewsExplorerPage } from './pages/NewsExplorerPage';
import { CompanyAnalysisPage } from './pages/CompanyAnalysisPage';
import { ConflictDetectorPage } from './pages/ConflictDetectorPage';
import { SectorHeatmapPage } from './pages/SectorHeatmapPage';
import { AlertsHistoryPage } from './pages/AlertsHistoryPage';
import { DataQualityPage } from './pages/DataQualityPage';
import { AssistantPage } from './pages/AssistantPage';
import { api } from './services/api';

export function App() {
  const [healthData, setHealthData] = useState<any>(null);
  const [lastRefreshed, setLastRefreshed] = useState<string>(new Date().toISOString());

  const checkHealth = async () => {
    try {
      const data = await api.getHealth();
      setHealthData(data);
    } catch (err) {
      console.warn('Backend health check error:', err);
    }
  };

  useEffect(() => {
    checkHealth();
  }, []);

  const handleGlobalRefresh = async () => {
    try {
      await api.refreshNews();
      setLastRefreshed(new Date().toISOString());
      await checkHealth();
    } catch (err) {
      console.error('Refresh failed:', err);
    }
  };

  const isDemo = healthData?.news_api?.has_key === false || healthData?.news_api?.status?.includes('Demo');
  const modelStatus = healthData?.model?.status || 'ready';

  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-[#0b1120] text-slate-100">
        {/* Navigation Sidebar */}
        <Sidebar modelStatus={modelStatus} isDemo={isDemo} />

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col min-w-0">
          <Navbar
            lastUpdated={lastRefreshed}
            isDemo={isDemo}
            onRefresh={handleGlobalRefresh}
          />

          <main className="flex-1 p-6 lg:p-8 max-w-7xl w-full mx-auto overflow-y-auto">
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/analyze" element={<LiveAnalysisPage />} />
              <Route path="/news" element={<NewsExplorerPage />} />
              <Route path="/companies" element={<CompanyAnalysisPage />} />
              <Route path="/conflicts" element={<ConflictDetectorPage />} />
              <Route path="/sectors" element={<SectorHeatmapPage />} />
              <Route path="/alerts" element={<AlertsHistoryPage />} />
              <Route path="/data-quality" element={<DataQualityPage />} />
              <Route path="/assistant" element={<AssistantPage />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;
