import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getProjects, createProject, getDashboard } from '../api/client';
import type { Project, DashboardStats } from '../types';

export default function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: '', description: '', client: '', location: '', tier_level: 'III' });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [projRes, dashRes] = await Promise.all([getProjects(), getDashboard()]);
      setProjects(projRes.data);
      setStats(dashRes.data);
    } catch (e) {
      console.error('Failed to load dashboard', e);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createProject(form);
      setForm({ name: '', description: '', client: '', location: '', tier_level: 'III' });
      setShowCreate(false);
      loadData();
    } catch (e) {
      console.error('Failed to create project', e);
    }
  };

  const statCards = stats ? [
    {
      label: 'Total Projects',
      value: stats.total_projects,
      gradient: 'from-blue-500 to-blue-600',
      bgLight: 'bg-blue-50',
      textColor: 'text-blue-700',
      icon: (
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
        </svg>
      ),
    },
    {
      label: 'Submittals',
      value: stats.total_submittals,
      gradient: 'from-emerald-500 to-emerald-600',
      bgLight: 'bg-emerald-50',
      textColor: 'text-emerald-700',
      icon: (
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
        </svg>
      ),
    },
    {
      label: 'Pending Review',
      value: stats.pending_review,
      gradient: 'from-amber-500 to-amber-600',
      bgLight: 'bg-amber-50',
      textColor: 'text-amber-700',
      icon: (
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
    },
    {
      label: 'Open Comments',
      value: stats.open_comments,
      gradient: 'from-orange-500 to-orange-600',
      bgLight: 'bg-orange-50',
      textColor: 'text-orange-700',
      icon: (
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
        </svg>
      ),
    },
    {
      label: 'Critical Issues',
      value: stats.critical_issues,
      gradient: 'from-red-500 to-red-600',
      bgLight: 'bg-red-50',
      textColor: 'text-red-700',
      icon: (
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
        </svg>
      ),
    },
  ] : [];

  const tierColors: Record<string, string> = {
    'I': 'bg-slate-100 text-slate-700',
    'II': 'bg-blue-100 text-blue-700',
    'III': 'bg-violet-100 text-violet-700',
    'IV': 'bg-amber-100 text-amber-700',
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">Overview of your submittal review projects</p>
      </div>

      {/* Stat Cards */}
      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          {statCards.map((s) => (
            <div
              key={s.label}
              className="group relative bg-white rounded-xl border border-gray-200 p-5 hover:shadow-lg hover:border-gray-300 transition-all duration-200 overflow-hidden"
            >
              {/* Gradient accent bar at top */}
              <div className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${s.gradient}`} />

              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-500">{s.label}</p>
                  <p className="mt-2 text-3xl font-bold text-gray-900 tracking-tight">{s.value}</p>
                </div>
                <div className={`${s.bgLight} ${s.textColor} rounded-lg p-2.5 group-hover:scale-110 transition-transform duration-200`}>
                  {s.icon}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Analytics Section */}
      {stats && (stats.submittals_by_status || stats.comments_by_severity) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Submittals by Status */}
          {stats.submittals_by_status && Object.keys(stats.submittals_by_status).length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-semibold text-gray-700 mb-4">Submittals by Status</h3>
              <div className="space-y-3">
                {Object.entries(stats.submittals_by_status).map(([status, count]: [string, any]) => {
                  const total = Object.values(stats.submittals_by_status).reduce((a: any, b: any) => a + b, 0) as number;
                  const pct = total > 0 ? (count / total) * 100 : 0;
                  const colors: Record<string, string> = {
                    uploaded: 'bg-slate-400', reviewing: 'bg-amber-400',
                    reviewed: 'bg-blue-400', approved: 'bg-emerald-400',
                    rejected: 'bg-red-400', revise_resubmit: 'bg-orange-400',
                  };
                  return (
                    <div key={status}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-gray-600 capitalize">{status.replace('_', ' ')}</span>
                        <span className="font-semibold">{count}</span>
                      </div>
                      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                        <div className={`h-full rounded-full ${colors[status] || 'bg-gray-400'}`} style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Comments by Severity */}
          {stats.comments_by_severity && Object.keys(stats.comments_by_severity).length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-semibold text-gray-700 mb-4">Open Comments by Severity</h3>
              <div className="space-y-3">
                {Object.entries(stats.comments_by_severity).map(([severity, count]: [string, any]) => {
                  const total = Object.values(stats.comments_by_severity).reduce((a: any, b: any) => a + b, 0) as number;
                  const pct = total > 0 ? (count / total) * 100 : 0;
                  const colors: Record<string, string> = {
                    critical: 'bg-red-500', major: 'bg-orange-500',
                    minor: 'bg-amber-400', info: 'bg-blue-400',
                  };
                  return (
                    <div key={severity}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-gray-600 capitalize">{severity}</span>
                        <span className="font-semibold">{count}</span>
                      </div>
                      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                        <div className={`h-full rounded-full ${colors[severity] || 'bg-gray-400'}`} style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Projects Section */}
      <div>
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Projects</h2>
            <p className="text-sm text-gray-500 mt-0.5">
              {projects.length > 0
                ? `${projects.length} project${projects.length !== 1 ? 's' : ''}`
                : 'No projects yet'}
            </p>
          </div>
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-blue-600 to-blue-700 text-white text-sm font-medium rounded-lg hover:from-blue-700 hover:to-blue-800 shadow-sm hover:shadow-md transition-all duration-200 active:scale-[0.98]"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            New Project
          </button>
        </div>

        {/* Create Project Modal Overlay */}
        {showCreate && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            {/* Backdrop */}
            <div
              className="absolute inset-0 bg-gray-900/50 backdrop-blur-sm"
              onClick={() => setShowCreate(false)}
            />

            {/* Modal */}
            <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg border border-gray-200 overflow-hidden">
              {/* Modal Header */}
              <div className="px-6 py-5 border-b border-gray-100 bg-gray-50/80">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">Create New Project</h3>
                    <p className="text-sm text-gray-500 mt-0.5">Set up a new submittal review project</p>
                  </div>
                  <button
                    onClick={() => setShowCreate(false)}
                    className="text-gray-400 hover:text-gray-600 rounded-lg p-1.5 hover:bg-gray-100 transition-colors"
                  >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>

              {/* Modal Body */}
              <form onSubmit={handleCreate} className="p-6 space-y-5">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    Project Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    placeholder="e.g., Armada Leviathan MDC"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    required
                    className="w-full border border-gray-300 rounded-lg px-3.5 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-shadow"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">Client</label>
                    <input
                      placeholder="e.g., ABB"
                      value={form.client}
                      onChange={(e) => setForm({ ...form, client: e.target.value })}
                      className="w-full border border-gray-300 rounded-lg px-3.5 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-shadow"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">Location</label>
                    <input
                      placeholder="e.g., Dallas, TX"
                      value={form.location}
                      onChange={(e) => setForm({ ...form, location: e.target.value })}
                      className="w-full border border-gray-300 rounded-lg px-3.5 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-shadow"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">Redundancy Tier</label>
                  <select
                    value={form.tier_level}
                    onChange={(e) => setForm({ ...form, tier_level: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3.5 py-2.5 text-sm text-gray-900 bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-shadow appearance-none cursor-pointer"
                  >
                    <option value="I">Tier I &mdash; Basic</option>
                    <option value="II">Tier II &mdash; Redundant Components</option>
                    <option value="III">Tier III &mdash; Concurrently Maintainable</option>
                    <option value="IV">Tier IV &mdash; Fault Tolerant</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">Description</label>
                  <input
                    placeholder="Brief project description..."
                    value={form.description}
                    onChange={(e) => setForm({ ...form, description: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3.5 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-shadow"
                  />
                </div>

                {/* Modal Footer */}
                <div className="flex items-center justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowCreate(false)}
                    className="px-4 py-2.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-5 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-blue-600 to-blue-700 rounded-lg hover:from-blue-700 hover:to-blue-800 shadow-sm hover:shadow-md transition-all duration-200"
                  >
                    Create Project
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Project Cards */}
        <div className="grid gap-4">
          {projects.map((project) => (
            <Link
              key={project.id}
              to={`/project/${project.id}`}
              className="group bg-white rounded-xl border border-gray-200 p-5 hover:shadow-lg hover:border-gray-300 transition-all duration-200"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3">
                    <h3 className="text-base font-semibold text-gray-900 group-hover:text-blue-600 transition-colors truncate">
                      {project.name}
                    </h3>
                    {project.tier_level && (
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${tierColors[project.tier_level] || 'bg-gray-100 text-gray-700'}`}>
                        Tier {project.tier_level}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
                    {project.client && (
                      <span className="inline-flex items-center gap-1.5">
                        <svg className="w-3.5 h-3.5 text-gray-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 21h16.5M4.5 3h15M5.25 3v18m13.5-18v18M9 6.75h1.5m-1.5 3h1.5m-1.5 3h1.5m3-6H15m-1.5 3H15m-1.5 3H15M9 21v-3.375c0-.621.504-1.125 1.125-1.125h3.75c.621 0 1.125.504 1.125 1.125V21" />
                        </svg>
                        {project.client}
                      </span>
                    )}
                    {project.location && (
                      <span className="inline-flex items-center gap-1.5">
                        <svg className="w-3.5 h-3.5 text-gray-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
                        </svg>
                        {project.location}
                      </span>
                    )}
                    {project.created_at && (
                      <span className="inline-flex items-center gap-1.5 text-gray-400">
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
                        </svg>
                        {formatDate(project.created_at)}
                      </span>
                    )}
                  </div>

                  {project.description && (
                    <p className="text-sm text-gray-400 mt-2 line-clamp-1">{project.description}</p>
                  )}
                </div>

                <div className="flex items-center gap-4 flex-shrink-0">
                  <div className="text-center px-4 py-2 bg-blue-50 rounded-lg">
                    <div className="text-2xl font-bold text-blue-600">{project.submittal_count}</div>
                    <div className="text-xs font-medium text-blue-500 mt-0.5">
                      {project.submittal_count === 1 ? 'submittal' : 'submittals'}
                    </div>
                  </div>
                  <svg className="w-5 h-5 text-gray-300 group-hover:text-blue-500 transition-colors" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                  </svg>
                </div>
              </div>
            </Link>
          ))}

          {/* Empty State */}
          {projects.length === 0 && (
            <div className="text-center py-20 bg-white rounded-xl border border-dashed border-gray-300">
              <div className="mx-auto w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
                <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
                </svg>
              </div>
              <h3 className="text-base font-semibold text-gray-900">No projects yet</h3>
              <p className="mt-1.5 text-sm text-gray-500 max-w-sm mx-auto">
                Create your first project to start reviewing submittals for your data center builds.
              </p>
              <button
                onClick={() => setShowCreate(true)}
                className="mt-5 inline-flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-blue-600 to-blue-700 text-white text-sm font-medium rounded-lg hover:from-blue-700 hover:to-blue-800 shadow-sm hover:shadow-md transition-all duration-200"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                </svg>
                Create Your First Project
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
