import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  getSubmittal, runReview, getReviewResults, getComments,
  addComment, updateComment, generateEmail, getEmails,
  getSubmittalPdfUrl, annotateSubmittal, getAnnotatedPdfUrl,
} from '../api/client';
import type { Submittal, ReviewResult, ReviewComment, GeneratedEmail } from '../types';

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'bg-red-100 text-red-800 border-red-300',
  major: 'bg-orange-100 text-orange-800 border-orange-300',
  minor: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  info: 'bg-blue-100 text-blue-800 border-blue-300',
};

const RESULT_ICONS: Record<number, { icon: string; color: string }> = {
  1: { icon: 'PASS', color: 'text-green-600 bg-green-50' },
  0: { icon: 'FAIL', color: 'text-red-600 bg-red-50' },
  [-1]: { icon: 'REVIEW', color: 'text-yellow-600 bg-yellow-50' },
};

export default function SubmittalReview() {
  const { submittalId } = useParams();
  const [submittal, setSubmittal] = useState<Submittal | null>(null);
  const [results, setResults] = useState<ReviewResult[]>([]);
  const [comments, setComments] = useState<ReviewComment[]>([]);
  const [emails, setEmails] = useState<GeneratedEmail[]>([]);
  const [activeTab, setActiveTab] = useState<'review' | 'comments' | 'email' | 'pdf'>('review');
  const [reviewing, setReviewing] = useState(false);
  const [annotating, setAnnotating] = useState(false);
  const [hasAnnotated, setHasAnnotated] = useState(false);
  const [viewingMarkup, setViewingMarkup] = useState(false);
  const [reviewSummary, setReviewSummary] = useState<any>(null);
  const [newComment, setNewComment] = useState({ comment_text: '', severity: 'info', reference_code: '' });
  const [emailForm, setEmailForm] = useState({ email_type: 'clarification', recipients: '', additional_notes: '' });
  const [selectedEmail, setSelectedEmail] = useState<GeneratedEmail | null>(null);

  useEffect(() => {
    if (submittalId) loadData();
  }, [submittalId]);

  const loadData = async () => {
    const id = Number(submittalId);
    try {
      const [subRes, resRes, comRes, emRes] = await Promise.all([
        getSubmittal(id), getReviewResults(id), getComments(id), getEmails(id),
      ]);
      setSubmittal(subRes.data);
      setResults(resRes.data);
      setComments(comRes.data);
      setEmails(emRes.data);
      if (subRes.data.annotated_file_path) setHasAnnotated(true);
    } catch (e) {
      console.error('Failed to load', e);
    }
  };

  const handleRunReview = async () => {
    setReviewing(true);
    try {
      const res = await runReview(Number(submittalId));
      setReviewSummary(res.data);
      loadData();
    } catch (e) {
      console.error('Review failed', e);
    } finally {
      setReviewing(false);
    }
  };

  const handleAnnotate = async () => {
    setAnnotating(true);
    try {
      await annotateSubmittal(Number(submittalId));
      setHasAnnotated(true);
      setViewingMarkup(true);
      setActiveTab('pdf');
      loadData();
    } catch (e) {
      console.error('Annotation failed', e);
    } finally {
      setAnnotating(false);
    }
  };

  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await addComment(Number(submittalId), newComment);
      setNewComment({ comment_text: '', severity: 'info', reference_code: '' });
      loadData();
    } catch (e) {
      console.error('Failed to add comment', e);
    }
  };

  const handleResolve = async (commentId: number) => {
    await updateComment(commentId, { status: 'resolved' });
    loadData();
  };

  const handleDefer = async (commentId: number) => {
    await updateComment(commentId, { status: 'deferred' });
    loadData();
  };

  const handleGenerateEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await generateEmail(Number(submittalId), emailForm);
      setSelectedEmail(res.data);
      loadData();
    } catch (e) {
      console.error('Failed to generate email', e);
    }
  };

  if (!submittal) return <div className="text-center py-12 text-gray-400">Loading...</div>;

  // Group results by category
  const resultsByCategory: Record<string, ReviewResult[]> = {};
  results.forEach((r) => {
    const cat = r.check_category || 'Other';
    if (!resultsByCategory[cat]) resultsByCategory[cat] = [];
    resultsByCategory[cat].push(r);
  });

  const tabs = [
    { id: 'review' as const, label: 'Review Results', count: results.length },
    { id: 'comments' as const, label: 'Comments', count: comments.filter(c => c.status === 'open').length },
    { id: 'email' as const, label: 'Emails', count: emails.length },
    { id: 'pdf' as const, label: 'View PDF' },
  ];

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Link to={`/project/${submittal.project_id}`} className="text-sm text-blue-600 hover:underline">&larr; Back to Project</Link>
          <h2 className="text-2xl font-bold mt-1">{submittal.title}</h2>
          <div className="text-sm text-gray-500 flex gap-4">
            <span className="font-medium text-blue-600">{submittal.equipment_type.replace('_', ' ').toUpperCase()}</span>
            {submittal.manufacturer && <span>{submittal.manufacturer}</span>}
            {submittal.submittal_number && <span>#{submittal.submittal_number}</span>}
            <span className="px-2 py-0.5 rounded-full text-xs bg-gray-200">{submittal.status}</span>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleRunReview}
            disabled={reviewing}
            className="px-6 py-2.5 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 disabled:opacity-50"
          >
            {reviewing ? 'Reviewing...' : 'Run Review'}
          </button>
          <button
            onClick={handleAnnotate}
            disabled={annotating || comments.length === 0}
            className="px-6 py-2.5 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 disabled:opacity-50"
          >
            {annotating ? 'Marking Up...' : 'Mark Up PDF'}
          </button>
        </div>
      </div>

      {/* Review Summary */}
      {reviewSummary && (
        <div className="bg-white rounded-lg shadow p-4 border-l-4 border-blue-500 space-y-3">
          <h3 className="font-bold">Review Summary</h3>

          {/* Stats row */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-sm">
            <div className="bg-gray-50 rounded p-2"><span className="text-gray-500 block text-xs">Total Checks</span><strong className="text-lg">{reviewSummary.total_checks}</strong></div>
            <div className="bg-green-50 rounded p-2"><span className="text-green-600 block text-xs">Passed</span><strong className="text-lg text-green-700">{reviewSummary.passed}</strong></div>
            <div className="bg-red-50 rounded p-2"><span className="text-red-600 block text-xs">Failed</span><strong className="text-lg text-red-700">{reviewSummary.failed}</strong></div>
            <div className="bg-yellow-50 rounded p-2"><span className="text-yellow-600 block text-xs">Needs Review</span><strong className="text-lg text-yellow-700">{reviewSummary.needs_review}</strong></div>
            <div className="bg-red-50 rounded p-2"><span className="text-red-700 block text-xs">Critical</span><strong className="text-lg text-red-800">{reviewSummary.critical_issues}</strong></div>
          </div>

          {/* Full review extras */}
          {reviewSummary.review_type === 'full_package' && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
              <div className="bg-blue-50 rounded p-2"><span className="text-blue-600 block text-xs">Pages Scanned</span><strong className="text-lg">{reviewSummary.total_pages}</strong></div>
              <div className="bg-blue-50 rounded p-2"><span className="text-blue-600 block text-xs">Equipment Found</span><strong className="text-lg">{reviewSummary.equipment_count}</strong></div>
              <div className="bg-purple-50 rounded p-2"><span className="text-purple-600 block text-xs">Cross-Ref Checks</span><strong className="text-lg">{reviewSummary.cross_reference_findings}</strong></div>
              <div className="bg-orange-50 rounded p-2"><span className="text-orange-600 block text-xs">Major Issues</span><strong className="text-lg text-orange-700">{reviewSummary.major_issues}</strong></div>
            </div>
          )}

          {/* Equipment discovered */}
          {reviewSummary.equipment_found && reviewSummary.equipment_found.length > 0 && (
            <details className="text-sm">
              <summary className="cursor-pointer font-medium text-blue-600 hover:underline">
                Equipment Discovered ({reviewSummary.equipment_found.length} items)
              </summary>
              <div className="mt-2 grid grid-cols-1 md:grid-cols-2 gap-1">
                {reviewSummary.equipment_found.map((eq: any, i: number) => (
                  <div key={i} className="flex items-center gap-2 text-xs bg-gray-50 rounded px-2 py-1">
                    <span className="font-mono font-bold text-blue-700">{eq.designation}</span>
                    <span className="text-gray-400">{eq.type}</span>
                    {eq.kva && <span className="text-gray-600">{eq.kva}kVA</span>}
                    {eq.kw && <span className="text-gray-600">{eq.kw}kW</span>}
                    {eq.voltage && <span className="text-gray-600">{eq.voltage}</span>}
                    {eq.amperage && <span className="text-gray-600">{eq.amperage}</span>}
                    <span className="text-gray-300">pg{eq.page}</span>
                  </div>
                ))}
              </div>
            </details>
          )}

          {/* Page breakdown */}
          {reviewSummary.page_breakdown && (
            <details className="text-sm">
              <summary className="cursor-pointer font-medium text-blue-600 hover:underline">
                Page Classification
              </summary>
              <div className="mt-2 flex flex-wrap gap-2">
                {Object.entries(reviewSummary.page_breakdown).map(([type, count]: [string, any]) => (
                  <span key={type} className="bg-gray-100 rounded px-2 py-1 text-xs">
                    {type.replace('_', ' ')}: <strong>{count}</strong>
                  </span>
                ))}
              </div>
            </details>
          )}

          <div className="text-sm font-semibold mt-1 pt-2 border-t">{reviewSummary.recommendation}</div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.id ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.label}
            {tab.count !== undefined && tab.count > 0 && (
              <span className="ml-1.5 px-1.5 py-0.5 bg-gray-200 rounded-full text-xs">{tab.count}</span>
            )}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'review' && (
        <div className="space-y-4">
          {Object.entries(resultsByCategory).map(([category, items]) => (
            <div key={category} className="bg-white rounded-lg shadow">
              <div className="px-4 py-3 border-b bg-gray-50 rounded-t-lg">
                <h3 className="font-semibold text-sm">{category}</h3>
              </div>
              <div className="divide-y">
                {items.map((r) => {
                  const status = RESULT_ICONS[r.passed] || RESULT_ICONS[-1];
                  return (
                    <div key={r.id} className="px-4 py-3 flex items-start gap-3">
                      <span className={`px-2 py-0.5 rounded text-xs font-bold ${status.color}`}>{status.icon}</span>
                      <div className="flex-1">
                        <div className="text-sm font-medium">{r.check_name}</div>
                        {r.details && <div className="text-xs text-gray-500 mt-0.5">{r.details}</div>}
                      </div>
                      {r.reference_standard && (
                        <span className="text-xs text-gray-400 whitespace-nowrap">{r.reference_standard}</span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
          {results.length === 0 && (
            <div className="text-center py-12 text-gray-400">No review results yet. Click "Run Review" to analyze this submittal.</div>
          )}
        </div>
      )}

      {activeTab === 'comments' && (
        <div className="space-y-4">
          {/* Add Comment */}
          <form onSubmit={handleAddComment} className="bg-white rounded-lg shadow p-4 space-y-3">
            <h3 className="font-semibold text-sm">Add Comment</h3>
            <textarea
              placeholder="Enter comment..."
              value={newComment.comment_text}
              onChange={(e) => setNewComment({ ...newComment, comment_text: e.target.value })}
              required
              rows={2}
              className="border rounded px-3 py-2 text-sm w-full"
            />
            <div className="flex gap-3 items-center">
              <select
                value={newComment.severity}
                onChange={(e) => setNewComment({ ...newComment, severity: e.target.value })}
                className="border rounded px-3 py-2 text-sm"
              >
                <option value="critical">Critical</option>
                <option value="major">Major</option>
                <option value="minor">Minor</option>
                <option value="info">Info</option>
              </select>
              <input
                placeholder="Reference (e.g., NEC 110.26)"
                value={newComment.reference_code}
                onChange={(e) => setNewComment({ ...newComment, reference_code: e.target.value })}
                className="border rounded px-3 py-2 text-sm flex-1"
              />
              <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded text-sm">Add</button>
            </div>
          </form>

          {/* Comment List */}
          <div className="space-y-2">
            {comments.map((c) => (
              <div key={c.id} className={`bg-white rounded-lg shadow p-4 border-l-4 ${
                c.status === 'resolved' ? 'border-green-400 opacity-60' :
                c.status === 'deferred' ? 'border-gray-400 opacity-60' :
                c.severity === 'critical' ? 'border-red-500' :
                c.severity === 'major' ? 'border-orange-500' :
                'border-blue-300'
              }`}>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${SEVERITY_COLORS[c.severity] || ''}`}>
                        {c.severity}
                      </span>
                      <span className={`px-2 py-0.5 rounded text-xs ${
                        c.status === 'open' ? 'bg-red-50 text-red-600' :
                        c.status === 'resolved' ? 'bg-green-50 text-green-600' :
                        'bg-gray-50 text-gray-600'
                      }`}>{c.status}</span>
                      {c.reference_code && <span className="text-xs text-gray-400">{c.reference_code}</span>}
                    </div>
                    <p className="text-sm">{c.comment_text}</p>
                    {c.resolution_notes && <p className="text-xs text-green-600 mt-1">Resolution: {c.resolution_notes}</p>}
                  </div>
                  {c.status === 'open' && (
                    <div className="flex gap-1 ml-3">
                      <button onClick={() => handleResolve(c.id)} className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs hover:bg-green-200">Resolve</button>
                      <button onClick={() => handleDefer(c.id)} className="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs hover:bg-gray-200">Defer</button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'email' && (
        <div className="space-y-4">
          {/* Generate Email */}
          <form onSubmit={handleGenerateEmail} className="bg-white rounded-lg shadow p-4 space-y-3">
            <h3 className="font-semibold text-sm">Generate Email</h3>
            <div className="grid grid-cols-2 gap-3">
              <select
                value={emailForm.email_type}
                onChange={(e) => setEmailForm({ ...emailForm, email_type: e.target.value })}
                className="border rounded px-3 py-2 text-sm"
              >
                <option value="rfi">RFI (Request for Information)</option>
                <option value="clarification">Clarification Request</option>
                <option value="rejection">Rejection / Revise & Resubmit</option>
                <option value="approval">Approval</option>
              </select>
              <input
                placeholder="Recipients (email addresses)"
                value={emailForm.recipients}
                onChange={(e) => setEmailForm({ ...emailForm, recipients: e.target.value })}
                className="border rounded px-3 py-2 text-sm"
              />
            </div>
            <textarea
              placeholder="Additional notes (optional)"
              value={emailForm.additional_notes}
              onChange={(e) => setEmailForm({ ...emailForm, additional_notes: e.target.value })}
              rows={2}
              className="border rounded px-3 py-2 text-sm w-full"
            />
            <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded text-sm">Generate Email</button>
          </form>

          {/* Generated Email Preview */}
          {selectedEmail && (
            <div className="bg-white rounded-lg shadow p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold">Generated Email</h3>
                <button
                  onClick={() => navigator.clipboard.writeText(selectedEmail.body)}
                  className="px-3 py-1 bg-gray-100 rounded text-sm hover:bg-gray-200"
                >
                  Copy to Clipboard
                </button>
              </div>
              <div className="text-sm mb-2"><strong>Subject:</strong> {selectedEmail.subject}</div>
              <pre className="text-sm bg-gray-50 rounded p-4 whitespace-pre-wrap font-mono border max-h-96 overflow-y-auto">
                {selectedEmail.body}
              </pre>
            </div>
          )}

          {/* Email History */}
          {emails.length > 0 && (
            <div className="bg-white rounded-lg shadow">
              <div className="px-4 py-3 border-b bg-gray-50 rounded-t-lg">
                <h3 className="font-semibold text-sm">Email History</h3>
              </div>
              <div className="divide-y">
                {emails.map((em) => (
                  <div
                    key={em.id}
                    onClick={() => setSelectedEmail(em)}
                    className="px-4 py-3 cursor-pointer hover:bg-gray-50 flex justify-between items-center"
                  >
                    <div>
                      <div className="text-sm font-medium">{em.subject}</div>
                      <div className="text-xs text-gray-400">{em.email_type} - {new Date(em.created_at).toLocaleDateString()}</div>
                    </div>
                    <span className={`text-xs px-2 py-0.5 rounded ${em.sent ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                      {em.sent ? 'Sent' : 'Draft'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'pdf' && (
        <div className="bg-white rounded-lg shadow">
          {/* PDF toolbar */}
          <div className="flex items-center justify-between px-4 py-2 border-b bg-gray-50 rounded-t-lg">
            <div className="flex gap-2">
              <button
                onClick={() => setViewingMarkup(false)}
                className={`px-3 py-1 rounded text-sm font-medium ${!viewingMarkup ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
              >
                Original PDF
              </button>
              <button
                onClick={() => { if (hasAnnotated) setViewingMarkup(true); }}
                disabled={!hasAnnotated}
                className={`px-3 py-1 rounded text-sm font-medium ${viewingMarkup ? 'bg-purple-600 text-white' : hasAnnotated ? 'bg-gray-200 text-gray-700 hover:bg-gray-300' : 'bg-gray-100 text-gray-400 cursor-not-allowed'}`}
              >
                Marked Up PDF
              </button>
            </div>
            <div className="flex gap-2">
              {viewingMarkup && hasAnnotated && (
                <a
                  href={getAnnotatedPdfUrl(Number(submittalId))}
                  download
                  className="px-3 py-1 bg-green-600 text-white rounded text-sm font-medium hover:bg-green-700"
                >
                  Download Marked Up PDF
                </a>
              )}
              <a
                href={viewingMarkup && hasAnnotated ? getAnnotatedPdfUrl(Number(submittalId)) : getSubmittalPdfUrl(Number(submittalId))}
                target="_blank"
                rel="noopener noreferrer"
                className="px-3 py-1 bg-gray-200 text-gray-700 rounded text-sm hover:bg-gray-300"
              >
                Open in New Tab
              </a>
            </div>
          </div>
          <iframe
            src={viewingMarkup && hasAnnotated ? getAnnotatedPdfUrl(Number(submittalId)) : getSubmittalPdfUrl(Number(submittalId))}
            className="w-full rounded-b-lg"
            style={{ height: '80vh' }}
            title={viewingMarkup ? 'Marked Up PDF' : 'Submittal PDF'}
          />
        </div>
      )}
    </div>
  );
}
