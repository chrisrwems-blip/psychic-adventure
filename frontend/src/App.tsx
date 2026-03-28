import { Routes, Route, Link, useLocation } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import ProjectDetail from './pages/ProjectDetail';
import SubmittalReview from './pages/SubmittalReview';
import CommentTracker from './pages/CommentTracker';

const navItems = [
  { path: '/', label: 'Dashboard' },
  { path: '/comments', label: 'Comment Tracker' },
];

export default function App() {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-slate-900 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-500 rounded flex items-center justify-center font-bold text-sm">DC</div>
            <div>
              <h1 className="text-lg font-bold leading-tight">Submittal Review Platform</h1>
              <p className="text-xs text-slate-400">Modular Data Center Electrical</p>
            </div>
          </Link>
          <nav className="flex gap-1">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`px-3 py-1.5 rounded text-sm transition-colors ${
                  location.pathname === item.path
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-300 hover:bg-slate-800'
                }`}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/project/:projectId" element={<ProjectDetail />} />
          <Route path="/submittal/:submittalId" element={<SubmittalReview />} />
          <Route path="/comments" element={<CommentTracker />} />
        </Routes>
      </main>
    </div>
  );
}
