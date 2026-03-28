import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getAllComments, updateComment, getProjects } from '../api/client';
import type { ReviewComment, Project } from '../types';

export default function CommentTracker() {
  const [comments, setComments] = useState<ReviewComment[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [filters, setFilters] = useState({ status: 'open', severity: '', project_id: '' });

  useEffect(() => {
    getProjects().then((res) => setProjects(res.data));
  }, []);

  useEffect(() => {
    loadComments();
  }, [filters]);

  const loadComments = async () => {
    try {
      const params: any = {};
      if (filters.status) params.status = filters.status;
      if (filters.severity) params.severity = filters.severity;
      if (filters.project_id) params.project_id = Number(filters.project_id);
      const res = await getAllComments(params);
      setComments(res.data);
    } catch (e) {
      console.error('Failed to load comments', e);
    }
  };

  const handleResolve = async (id: number) => {
    await updateComment(id, { status: 'resolved' });
    loadComments();
  };

  const handleDefer = async (id: number) => {
    await updateComment(id, { status: 'deferred' });
    loadComments();
  };

  const handleReopen = async (id: number) => {
    await updateComment(id, { status: 'open' });
    loadComments();
  };

  const stats = {
    total: comments.length,
    critical: comments.filter((c) => c.severity === 'critical').length,
    major: comments.filter((c) => c.severity === 'major').length,
    minor: comments.filter((c) => c.severity === 'minor').length,
  };

  const severityOrder: Record<string, number> = { critical: 0, major: 1, minor: 2, info: 3 };
  const sorted = [...comments].sort((a, b) => (severityOrder[a.severity] ?? 9) - (severityOrder[b.severity] ?? 9));

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">Comment Tracker</h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">All review comments across projects</p>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: 'Total', value: stats.total, color: 'from-slate-500 to-slate-600' },
          { label: 'Critical', value: stats.critical, color: 'from-red-500 to-red-600' },
          { label: 'Major', value: stats.major, color: 'from-orange-500 to-orange-600' },
          { label: 'Minor', value: stats.minor, color: 'from-amber-400 to-amber-500' },
        ].map((s) => (
          <div key={s.label} className="relative bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 overflow-hidden">
            <div className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${s.color}`} />
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">{s.label}</p>
            <p className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-1">{s.value}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
        <div className="flex items-center gap-4">
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Filters</span>
          <select
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
            className="input text-sm"
          >
            <option value="">All Status</option>
            <option value="open">Open</option>
            <option value="resolved">Resolved</option>
            <option value="deferred">Deferred</option>
          </select>
          <select
            value={filters.severity}
            onChange={(e) => setFilters({ ...filters, severity: e.target.value })}
            className="input text-sm"
          >
            <option value="">All Severity</option>
            <option value="critical">Critical</option>
            <option value="major">Major</option>
            <option value="minor">Minor</option>
            <option value="info">Info</option>
          </select>
          <select
            value={filters.project_id}
            onChange={(e) => setFilters({ ...filters, project_id: e.target.value })}
            className="input text-sm"
          >
            <option value="">All Projects</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          <span className="text-xs text-slate-400 dark:text-slate-500 ml-auto">{comments.length} results</span>
        </div>
      </div>

      {/* Comments */}
      <div className="space-y-2">
        {sorted.map((c) => {
          const severityClass = c.severity === 'critical' ? 'severity-border-critical' :
            c.severity === 'major' ? 'severity-border-major' :
            c.severity === 'minor' ? 'severity-border-minor' : 'severity-border-info';

          const badgeClass = c.severity === 'critical' ? 'badge-critical' :
            c.severity === 'major' ? 'badge-major' :
            c.severity === 'minor' ? 'badge-minor' : 'badge-info';

          const statusColor = c.status === 'open' ? 'bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 ring-1 ring-red-200 dark:ring-red-800' :
            c.status === 'resolved' ? 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 ring-1 ring-emerald-200 dark:ring-emerald-800' :
            'bg-slate-50 dark:bg-slate-700 text-slate-500 dark:text-slate-400 ring-1 ring-slate-200 dark:ring-slate-600';

          return (
            <div
              key={c.id}
              className={`bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 ${severityClass} ${
                c.status !== 'open' ? 'opacity-60' : ''
              } hover:shadow-md transition-shadow`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-2">
                    <span className={`badge ${badgeClass}`}>{c.severity}</span>
                    <span className={`badge ${statusColor}`}>{c.status}</span>
                    {c.reference_code && (
                      <span className="text-xs font-mono text-slate-400 dark:text-slate-500 bg-slate-50 dark:bg-slate-700 px-2 py-0.5 rounded">
                        {c.reference_code}
                      </span>
                    )}
                    {c.page_number && (
                      <span className="text-xs text-slate-400 dark:text-slate-500">pg {c.page_number}</span>
                    )}
                    <Link
                      to={`/submittal/${c.submittal_id}`}
                      className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 font-medium hover:underline"
                    >
                      View Submittal
                    </Link>
                  </div>
                  <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">{c.comment_text}</p>
                  {c.resolution_notes && (
                    <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-2 bg-emerald-50 dark:bg-emerald-900/30 px-3 py-1.5 rounded-lg">
                      Resolution: {c.resolution_notes}
                    </p>
                  )}
                  <p className="text-xs text-slate-400 dark:text-slate-500 mt-2">
                    {new Date(c.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                  </p>
                </div>
                <div className="flex flex-col gap-1.5 shrink-0">
                  {c.status === 'open' && (
                    <>
                      <button onClick={() => handleResolve(c.id)} className="btn-success text-xs px-3 py-1.5">
                        Resolve
                      </button>
                      <button onClick={() => handleDefer(c.id)} className="btn-secondary text-xs px-3 py-1.5">
                        Defer
                      </button>
                    </>
                  )}
                  {(c.status === 'resolved' || c.status === 'deferred') && (
                    <button onClick={() => handleReopen(c.id)} className="btn-secondary text-xs px-3 py-1.5">
                      Reopen
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
        {comments.length === 0 && (
          <div className="text-center py-16">
            <div className="w-16 h-16 mx-auto mb-4 bg-slate-100 dark:bg-slate-700 rounded-2xl flex items-center justify-center">
              <svg className="w-8 h-8 text-slate-400 dark:text-slate-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
              </svg>
            </div>
            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">No comments found</h3>
            <p className="text-sm text-slate-400 dark:text-slate-500 mt-1">Try adjusting your filters</p>
          </div>
        )}
      </div>
    </div>
  );
}
