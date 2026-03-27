import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getAllComments, updateComment, getProjects } from '../api/client';
import type { ReviewComment, Project } from '../types';

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'bg-red-100 text-red-800',
  major: 'bg-orange-100 text-orange-800',
  minor: 'bg-yellow-100 text-yellow-800',
  info: 'bg-blue-100 text-blue-800',
};

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

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">Comment Tracker</h2>

      {/* Stats Bar */}
      <div className="flex gap-4 text-sm">
        <span className="font-medium">{stats.total} comments</span>
        {stats.critical > 0 && <span className="text-red-600">{stats.critical} critical</span>}
        {stats.major > 0 && <span className="text-orange-600">{stats.major} major</span>}
        {stats.minor > 0 && <span className="text-yellow-600">{stats.minor} minor</span>}
      </div>

      {/* Filters */}
      <div className="flex gap-3 bg-white rounded-lg shadow p-3">
        <select
          value={filters.status}
          onChange={(e) => setFilters({ ...filters, status: e.target.value })}
          className="border rounded px-3 py-1.5 text-sm"
        >
          <option value="">All Status</option>
          <option value="open">Open</option>
          <option value="resolved">Resolved</option>
          <option value="deferred">Deferred</option>
        </select>
        <select
          value={filters.severity}
          onChange={(e) => setFilters({ ...filters, severity: e.target.value })}
          className="border rounded px-3 py-1.5 text-sm"
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
          className="border rounded px-3 py-1.5 text-sm"
        >
          <option value="">All Projects</option>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </div>

      {/* Comments */}
      <div className="space-y-2">
        {comments.map((c) => (
          <div
            key={c.id}
            className={`bg-white rounded-lg shadow p-4 border-l-4 ${
              c.status === 'resolved' ? 'border-green-400' :
              c.status === 'deferred' ? 'border-gray-400' :
              c.severity === 'critical' ? 'border-red-500' :
              c.severity === 'major' ? 'border-orange-500' :
              'border-blue-300'
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${SEVERITY_COLORS[c.severity] || ''}`}>
                    {c.severity}
                  </span>
                  <span className={`px-2 py-0.5 rounded text-xs ${
                    c.status === 'open' ? 'bg-red-50 text-red-600' :
                    c.status === 'resolved' ? 'bg-green-50 text-green-600' :
                    'bg-gray-100 text-gray-500'
                  }`}>{c.status}</span>
                  {c.reference_code && <span className="text-xs text-gray-400">{c.reference_code}</span>}
                  <Link to={`/submittal/${c.submittal_id}`} className="text-xs text-blue-500 hover:underline">
                    View Submittal
                  </Link>
                </div>
                <p className="text-sm">{c.comment_text}</p>
                {c.resolution_notes && <p className="text-xs text-green-600 mt-1">Resolution: {c.resolution_notes}</p>}
                <div className="text-xs text-gray-400 mt-1">{new Date(c.created_at).toLocaleDateString()}</div>
              </div>
              <div className="flex gap-1 ml-3">
                {c.status === 'open' && (
                  <>
                    <button onClick={() => handleResolve(c.id)} className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs hover:bg-green-200">Resolve</button>
                    <button onClick={() => handleDefer(c.id)} className="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs hover:bg-gray-200">Defer</button>
                  </>
                )}
                {(c.status === 'resolved' || c.status === 'deferred') && (
                  <button onClick={() => handleReopen(c.id)} className="px-2 py-1 bg-yellow-100 text-yellow-700 rounded text-xs hover:bg-yellow-200">Reopen</button>
                )}
              </div>
            </div>
          </div>
        ))}
        {comments.length === 0 && (
          <div className="text-center py-12 text-gray-400">No comments match your filters.</div>
        )}
      </div>
    </div>
  );
}
