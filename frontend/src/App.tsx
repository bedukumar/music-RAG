import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import { Home, ListMusic, Activity, Database, Search, Settings as SettingsIcon, MessageSquare, BookOpen } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import Chat from './pages/Chat';
import MediaCatalog from './pages/MediaCatalog';
import MediaDetails from './pages/MediaDetails';
import JobsMonitor from './pages/JobsMonitor';
import Collections from './pages/Collections';
import Settings from './pages/Settings';
import SearchPage from './pages/Search';
import SearchHistory from './pages/SearchHistory';
import SearchAnalytics from './pages/SearchAnalytics';
import SearchSettings from './pages/SearchSettings';
import ThemeToggle from './components/ThemeToggle';
import ApiDocs from './pages/ApiDocs';
import BulkUpload from './pages/BulkUpload';
import { UploadCloud } from 'lucide-react';

function MainLayout() {
  return (
    <div className="app-layout">

      <aside className="sidebar">
        {/* Logo */}
        <div className="sidebar-logo">
          <ListMusic size={16} color="var(--accent)" strokeWidth={2.5} />
          <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-1)', letterSpacing: '-0.01em' }}>
            RagPipe
          </span>
        </div>

        {/* Primary navigation */}
        <nav className="sidebar-nav">
          <NavLink
            to="/"
            end
            className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
          >
            <Home size={14} strokeWidth={2} />
            Dashboard
          </NavLink>
          <NavLink
            to="/search"
            className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
          >
            <Search size={14} strokeWidth={2} />
            Search
          </NavLink>
          <NavLink
            to="/chat"
            className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
          >
            <MessageSquare size={14} strokeWidth={2} />
            Chat
          </NavLink>
          <NavLink
            to="/media"
            className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
          >
            <ListMusic size={14} strokeWidth={2} />
            Media Catalog
          </NavLink>
          <NavLink
            to="/bulk-upload"
            className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
          >
            <UploadCloud size={14} strokeWidth={2} />
            Bulk Upload
          </NavLink>
          <NavLink
            to="/jobs"
            className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
          >
            <Activity size={14} strokeWidth={2} />
            Jobs Monitor
          </NavLink>
          <NavLink
            to="/collections"
            className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
          >
            <Database size={14} strokeWidth={2} />
            Collections
          </NavLink>
          <NavLink
            to="/api-docs"
            className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
          >
            <BookOpen size={14} strokeWidth={2} />
            API Docs
          </NavLink>
        </nav>

        {/* Footer navigation */}
        <div className="sidebar-footer">
          <ThemeToggle />
          <NavLink
            to="/settings"
            className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
          >
            <SettingsIcon size={14} strokeWidth={2} />
            Settings
          </NavLink>
        </div>
      </aside>

      <main className="main-content">
        <Routes>
          <Route path="/"                   element={<Dashboard />} />
          <Route path="/chat"               element={<Chat />} />
          <Route path="/search"             element={<SearchPage />} />
          <Route path="/search/history"     element={<SearchHistory />} />
          <Route path="/search/analytics"   element={<SearchAnalytics />} />
          <Route path="/search/settings"    element={<SearchSettings />} />
          <Route path="/media"              element={<MediaCatalog />} />
          <Route path="/media/:id"          element={<MediaDetails />} />
          <Route path="/bulk-upload"        element={<BulkUpload />} />
          <Route path="/jobs"               element={<JobsMonitor />} />
          <Route path="/collections"        element={<Collections />} />
          <Route path="/settings"           element={<Settings />} />
        </Routes>
      </main>

    </div>
  );
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/api-docs" element={<ApiDocs />} />
        <Route path="/*" element={<MainLayout />} />
      </Routes>
    </Router>
  );
}

export default App;
