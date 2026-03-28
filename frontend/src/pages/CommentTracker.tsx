import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getAllComments, updateComment, getProjects } from '../api/client';
import type { ReviewComment, Project } from '../types';

const QUICK_TEMPLATES = [
  'Verify NEC compliance — provide code reference',
  'Provide voltage drop / sizing calculation',
  'Clarify coordination with upstream OCPD',
  'Resubmit with revised drawing',
  'Confirm UL listing for US installation',
  'Provide arc flash incident energy label',
];

export default function CommentTracker() {
  const [comments, setComments] = useState<ReviewComment[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [filters, setFilters] = useState({ status: 'open', severity: '', project_id: '' });
  const [replyingTo, setReplyingTo] = useState<number | null>(null);
  const [replyText, setReplyText] = useState('');

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

  const handleResolve = async (id: number, notes?: string) => {
    await updateComment(id, { status: 'resolved', resolution_notes: notes || undefined });
    setReplyingTo(null);
    setReplyText('');
    loadComments();
  };

  const handleReject = async (id: number, notes?: string) => {
    await updateComment(id, { status: 'deferred', resolution_notes: notes || undefined });
    setReplyingTo(null);
    setReplyText('');
    loadComments();
  };

  const handleReopen = async (id: number) => {
    await updateComment(id, { status: 'open' });
    loadComments();
  };

  const handleAddNote = async (id: number) => {
    if (!replyText.trim()) return;
    const comment = comments.find(c => c.id === id);
    const existingNotes = comment?.resolution_notes || '';
    const updatedNotes = existingNotes
      ? `${existingNotes}\n---\n${replyText.trim()}`
      : replyText.trim();
    await updateComment(id, { resolution_notes: updatedNotes });
    setReplyingTo(null);
    setReplyText('');
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

          const isReplying = replyingTo === c.id;

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
                    {c.assigned_to && (
                      <span className="text-xs text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/30 px-2 py-0.5 rounded">
                        {c.assigned_to}
                      </span>
                    )}
                    <Link
                      to={`/submittal/${c.submittal_id}`}
                      className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 font-medium hover:underline"
                    >
                      View Submittal
                    </Link>
                  </div>
                  <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">{c.comment_text}</p>

                  {/* Resolution notes thread */}
                  {c.resolution_notes && (
                    <div className="mt-3 space-y-2">
                      {c.resolution_notes.split('\n---\n').map((note, i) => (
                        <div key={i} className="flex gap-2 items-start">
                          <div className="w-5 h-5 rounded-full bg-blue-100 dark:bg-blue-900/40 flex items-center justify-center shrink-0 mt-0.5">
                            <svg className="w-3 h-3 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
                            </svg>
                          </div>
                          <p className="text-xs text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-700/50 px-3 py-1.5 rounded-lg flex-1">
                            {note}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}

                  <p className="text-xs text-slate-400 dark:text-slate-500 mt-2">
                    {new Date(c.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                  </p>
                </div>

                {/* Action buttons */}
                <div className="flex items-center gap-1.5 shrink-0">
                  {c.status === 'open' && (
                    <>
                      {/* Green checkmark — resolve */}
                      <button
                        onClick={() => handleResolve(c.id)}
                        title="Resolve"
                        className="w-8 h-8 rounded-lg flex items-center justify-center bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-100 dark:hover:bg-emerald-900/50 transition-colors"
                      >
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                        </svg>
                      </button>
                      {/* Red X — reject/defer */}
                      <button
                        onClick={() => handleReject(c.id)}
                        title="Reject / Defer"
                        className="w-8 h-8 rounded-lg flex items-center justify-center bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/50 transition-colors"
                      >
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                        </svg>
                      </button>
                      {/* Reply/note button */}
                      <button
                        onClick={() => { setReplyingTo(isReplying ? null : c.id); setReplyText(''); }}
                        title="Add note"
                        className={`w-8 h-8 rounded-lg flex items-center justify-center transition-colors ${
                          isReplying
                            ? 'bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400'
                            : 'bg-slate-50 dark:bg-slate-700 text-slate-400 dark:text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-600'
                        }`}
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
                        </svg>
                      </button>
                    </>
                  )}
                  {(c.status === 'resolved' || c.status === 'deferred') && (
                    <>
                      <button
                        onClick={() => handleReopen(c.id)}
                        title="Reopen"
                        className="w-8 h-8 rounded-lg flex items-center justify-center bg-slate-50 dark:bg-slate-700 text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-600 transition-colors"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182" />
                        </svg>
                      </button>
                      {/* Reply/note on closed items too */}
                      <button
                        onClick={() => { setReplyingTo(isReplying ? null : c.id); setReplyText(''); }}
                        title="Add note"
                        className={`w-8 h-8 rounded-lg flex items-center justify-center transition-colors ${
                          isReplying
                            ? 'bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400'
                            : 'bg-slate-50 dark:bg-slate-700 text-slate-400 dark:text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-600'
                        }`}
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
                        </svg>
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* Reply input area */}
              {isReplying && (
                <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-700 space-y-2">
                  <textarea
                    value={replyText}
                    onChange={(e) => setReplyText(e.target.value)}
                    placeholder="Add a note or response..."
                    rows={2}
                    className="w-full border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-slate-700 dark:text-slate-200 dark:placeholder-slate-500 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                    autoFocus
                  />
                  {/* Quick templates */}
                  <div className="flex flex-wrap gap-1.5">
                    {QUICK_TEMPLATES.map((t) => (
                      <button
                        key={t}
                        type="button"
                        onClick={() => setReplyText(t)}
                        className="text-xs px-2 py-1 rounded-md bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                      >
                        {t}
                      </button>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleAddNote(c.id)}
                      disabled={!replyText.trim()}
                      className="px-3 py-1.5 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                    >
                      Save Note
                    </button>
                    {c.status === 'open' && (
                      <>
                        <button
                          onClick={() => handleResolve(c.id, replyText.trim() || undefined)}
                          className="px-3 py-1.5 text-xs font-medium text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/30 rounded-lg hover:bg-emerald-100 dark:hover:bg-emerald-900/50 transition-colors"
                        >
                          Resolve with Note
                        </button>
                        <button
                          onClick={() => handleReject(c.id, replyText.trim() || undefined)}
                          className="px-3 py-1.5 text-xs font-medium text-red-700 dark:text-red-400 bg-red-50 dark:bg-red-900/30 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/50 transition-colors"
                        >
                          Reject with Note
                        </button>
                      </>
                    )}
                    <button
                      onClick={() => { setReplyingTo(null); setReplyText(''); }}
                      className="px-3 py-1.5 text-xs font-medium text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300 transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
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
