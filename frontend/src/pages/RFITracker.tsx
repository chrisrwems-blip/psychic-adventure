import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getAllRFIs, updateRFIStatus } from '../api/client';
import type { RFI } from '../types';

export default function RFITracker() {
  const [rfis, setRfis] = useState<RFI[]>([]);
  const [filter, setFilter] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadRFIs();
  }, [filter]);

  const loadRFIs = async () => {
    try {
      setLoading(true);
      const params: any = {};
      if (filter) params.status = filter;
      const res = await getAllRFIs(params);
      setRfis(res.data);
    } catch (e) {
      console.error('Failed to load RFIs', e);
    } finally {
      setLoading(false);
    }
  };

  const handleStatusChange = async (rfiId: number, status: string) => {
    try {
      await updateRFIStatus(rfiId, { status });
      loadRFIs();
    } catch (e) {
      console.error('Failed to update RFI status', e);
    }
  };

  const stats = {
    total: rfis.length,
    draft: rfis.filter((r) => r.status === 'draft').length,
    sent: rfis.filter((r) => r.status === 'sent').length,
    responded: rfis.filter((r) => r.status === 'responded').length,
    closed: rfis.filter((r) => r.status === 'closed').length,
  };

  const severityOrder: Record<string, number> = { critical: 0, major: 1, minor: 2, info: 3 };
  const sorted = [...rfis].sort((a, b) => (severityOrder[a.severity] ?? 9) - (severityOrder[b.severity] ?? 9));

  const statusBadge = (status: string) => {
    switch (status) {
      case 'draft': return 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 ring-1 ring-slate-200 dark:ring-slate-600';
      case 'sent': return 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 ring-1 ring-blue-200 dark:ring-blue-800';
      case 'responded': return 'bg-amber-50 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 ring-1 ring-amber-200 dark:ring-amber-800';
      case 'closed': return 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 ring-1 ring-emerald-200 dark:ring-emerald-800';
      default: return 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 ring-1 ring-slate-200 dark:ring-slate-600';
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">RFI Tracker</h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Track Requests for Information across all submittals</p>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-5 gap-3">
        {[
          { label: 'Total', value: stats.total, color: 'from-slate-500 to-slate-600' },
          { label: 'Draft', value: stats.draft, color: 'from-slate-400 to-slate-500' },
          { label: 'Sent', value: stats.sent, color: 'from-blue-500 to-blue-600' },
          { label: 'Responded', value: stats.responded, color: 'from-amber-500 to-amber-600' },
          { label: 'Closed', value: stats.closed, color: 'from-emerald-500 to-emerald-600' },
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
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="input text-sm"
          >
            <option value="">All Status</option>
            <option value="draft">Draft</option>
            <option value="sent">Sent</option>
            <option value="responded">Responded</option>
            <option value="closed">Closed</option>
          </select>
          <span className="text-xs text-slate-400 dark:text-slate-500 ml-auto">{rfis.length} results</span>
        </div>
      </div>

      {/* RFI List */}
      <div className="space-y-2">
        {sorted.map((rfi) => {
          const severityClass = rfi.severity === 'critical' ? 'severity-border-critical' :
            rfi.severity === 'major' ? 'severity-border-major' :
            rfi.severity === 'minor' ? 'severity-border-minor' : 'severity-border-info';

          const badgeClass = rfi.severity === 'critical' ? 'badge-critical' :
            rfi.severity === 'major' ? 'badge-major' :
            rfi.severity === 'minor' ? 'badge-minor' : 'badge-info';

          return (
            <div
              key={rfi.id}
              className={`bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 ${severityClass} ${
                rfi.status === 'closed' ? 'opacity-60' : ''
              } hover:shadow-md transition-shadow`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-2">
                    <span className="text-sm font-bold text-slate-900 dark:text-slate-100">{rfi.rfi_number}</span>
                    <span className={`badge ${badgeClass}`}>{rfi.severity}</span>
                    <span className={`badge ${statusBadge(rfi.status)}`}>{rfi.status}</span>
                    {rfi.due_date && (
                      <span className="text-xs text-slate-400 dark:text-slate-500">
                        Due: {new Date(rfi.due_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                      </span>
                    )}
                    <Link
                      to={`/submittal/${rfi.submittal_id}`}
                      className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 font-medium hover:underline"
                    >
                      View Submittal
                    </Link>
                  </div>
                  <p className="text-sm font-semibold text-slate-800 dark:text-slate-200 mb-1">{rfi.subject}</p>
                  {rfi.description && (
                    <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">{rfi.description}</p>
                  )}
                  {rfi.response && (
                    <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-2 bg-emerald-50 dark:bg-emerald-900/30 px-3 py-1.5 rounded-lg">
                      Response: {rfi.response}
                    </p>
                  )}
                  <div className="flex items-center gap-3 mt-2">
                    {rfi.project_name && (
                      <span className="text-xs text-slate-400 dark:text-slate-500">{rfi.project_name}</span>
                    )}
                    {rfi.submittal_title && (
                      <span className="text-xs text-slate-400 dark:text-slate-500">{rfi.submittal_title}</span>
                    )}
                    <span className="text-xs text-slate-400 dark:text-slate-500">
                      {new Date(rfi.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                    </span>
                  </div>
                </div>
                <div className="flex flex-col gap-1.5 shrink-0">
                  {rfi.status === 'draft' && (
                    <button
                      onClick={() => handleStatusChange(rfi.id, 'sent')}
                      className="btn-primary text-xs px-3 py-1.5"
                    >
                      Mark as Sent
                    </button>
                  )}
                  {rfi.status === 'sent' && (
                    <button
                      onClick={() => handleStatusChange(rfi.id, 'responded')}
                      className="btn-success text-xs px-3 py-1.5"
                    >
                      Log Response
                    </button>
                  )}
                  {(rfi.status === 'responded' || rfi.status === 'sent') && (
                    <button
                      onClick={() => handleStatusChange(rfi.id, 'closed')}
                      className="btn-secondary text-xs px-3 py-1.5"
                    >
                      Close
                    </button>
                  )}
                  {rfi.status === 'closed' && (
                    <button
                      onClick={() => handleStatusChange(rfi.id, 'draft')}
                      className="btn-secondary text-xs px-3 py-1.5"
                    >
                      Reopen
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
        {!loading && rfis.length === 0 && (
          <div className="text-center py-16">
            <div className="w-16 h-16 mx-auto mb-4 bg-slate-100 dark:bg-slate-700 rounded-2xl flex items-center justify-center">
              <svg className="w-8 h-8 text-slate-400 dark:text-slate-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15a2.25 2.25 0 012.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z" />
              </svg>
            </div>
            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">No RFIs found</h3>
            <p className="text-sm text-slate-400 dark:text-slate-500 mt-1">RFIs will appear here when generated from submittal reviews</p>
          </div>
        )}
      </div>
    </div>
  );
}
