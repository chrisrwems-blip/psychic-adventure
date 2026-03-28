import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getProject, getSubmittals, uploadSubmittal, runBatchReview, getEquipmentTypes } from '../api/client';
import type { Project, Submittal } from '../types';

// --- Helpers ---

function timeAgo(dateStr: string): string {
  const now = new Date();
  const date = new Date(dateStr);
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months}mo ago`;
  return `${Math.floor(months / 12)}y ago`;
}

function formatFileSize(bytes?: number): string {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// --- Equipment type config ---

const EQUIPMENT_CONFIG: Record<string, { icon: string; color: string; bg: string; border: string }> = {
  switchgear:     { icon: '⚡', color: 'text-amber-700 dark:text-amber-400',   bg: 'bg-amber-50 dark:bg-amber-900/30',   border: 'border-amber-200 dark:border-amber-700' },
  transformer:    { icon: '🔌', color: 'text-blue-700 dark:text-blue-400',    bg: 'bg-blue-50 dark:bg-blue-900/30',    border: 'border-blue-200 dark:border-blue-700' },
  panelboard:     { icon: '📋', color: 'text-violet-700 dark:text-violet-400',  bg: 'bg-violet-50 dark:bg-violet-900/30',  border: 'border-violet-200 dark:border-violet-700' },
  ats:            { icon: '🔄', color: 'text-teal-700 dark:text-teal-400',    bg: 'bg-teal-50 dark:bg-teal-900/30',    border: 'border-teal-200 dark:border-teal-700' },
  ups:            { icon: '🔋', color: 'text-green-700 dark:text-green-400',   bg: 'bg-green-50 dark:bg-green-900/30',   border: 'border-green-200 dark:border-green-700' },
  generator:      { icon: '⚙️', color: 'text-slate-700 dark:text-slate-400',   bg: 'bg-slate-50 dark:bg-slate-900/30',   border: 'border-slate-200 dark:border-slate-600' },
  busway:         { icon: '🔗', color: 'text-orange-700 dark:text-orange-400',  bg: 'bg-orange-50 dark:bg-orange-900/30',  border: 'border-orange-200 dark:border-orange-700' },
  cable:          { icon: '🪢', color: 'text-rose-700 dark:text-rose-400',    bg: 'bg-rose-50 dark:bg-rose-900/30',    border: 'border-rose-200 dark:border-rose-700' },
  cooling:        { icon: '❄️', color: 'text-cyan-700 dark:text-cyan-400',    bg: 'bg-cyan-50 dark:bg-cyan-900/30',    border: 'border-cyan-200 dark:border-cyan-700' },
  fire_protection:{ icon: '🔥', color: 'text-red-700 dark:text-red-400',     bg: 'bg-red-50 dark:bg-red-900/30',     border: 'border-red-200 dark:border-red-700' },
  monitoring:     { icon: '📡', color: 'text-indigo-700 dark:text-indigo-400',  bg: 'bg-indigo-50 dark:bg-indigo-900/30',  border: 'border-indigo-200 dark:border-indigo-700' },
  other:          { icon: '📦', color: 'text-gray-700 dark:text-slate-300',    bg: 'bg-gray-50 dark:bg-slate-700',    border: 'border-gray-200 dark:border-slate-700' },
};

function getEquipmentStyle(type: string) {
  return EQUIPMENT_CONFIG[type] || EQUIPMENT_CONFIG.other;
}

// --- Status config ---

const STATUS_STYLES: Record<string, { dot: string; text: string; bg: string; label: string }> = {
  uploaded:         { dot: 'bg-gray-400 dark:bg-slate-500',   text: 'text-gray-700 dark:text-slate-300',   bg: 'bg-gray-50 dark:bg-slate-700',    label: 'Uploaded' },
  reviewing:        { dot: 'bg-yellow-500', text: 'text-yellow-700 dark:text-yellow-400', bg: 'bg-yellow-50 dark:bg-yellow-900/30',  label: 'In Review' },
  reviewed:         { dot: 'bg-blue-500',   text: 'text-blue-700 dark:text-blue-400',   bg: 'bg-blue-50 dark:bg-blue-900/30',    label: 'Reviewed' },
  approved:         { dot: 'bg-emerald-500',text: 'text-emerald-700 dark:text-emerald-400',bg: 'bg-emerald-50 dark:bg-emerald-900/30', label: 'Approved' },
  rejected:         { dot: 'bg-red-500',    text: 'text-red-700 dark:text-red-400',    bg: 'bg-red-50 dark:bg-red-900/30',     label: 'Rejected' },
  revise_resubmit:  { dot: 'bg-orange-500', text: 'text-orange-700 dark:text-orange-400', bg: 'bg-orange-50 dark:bg-orange-900/30',  label: 'Revise & Resubmit' },
};

function StatusBadge({ status }: { status: string }) {
  const s = STATUS_STYLES[status] || STATUS_STYLES.uploaded;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${s.bg} ${s.text} ring-1 ring-inset ring-current/10`}>
      <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
      {s.label}
    </span>
  );
}

function EquipmentBadge({ type }: { type: string }) {
  const cfg = getEquipmentStyle(type);
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-semibold border ${cfg.bg} ${cfg.color} ${cfg.border}`}>
      <span className="text-sm leading-none">{cfg.icon}</span>
      {type.replace(/_/g, ' ').toUpperCase()}
    </span>
  );
}

// --- Main Component ---

export default function ProjectDetail() {
  const { projectId } = useParams();
  const [project, setProject] = useState<Project | null>(null);
  const [submittals, setSubmittals] = useState<Submittal[]>([]);
  const [equipmentTypes, setEquipmentTypes] = useState<string[]>([]);
  const [showUpload, setShowUpload] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [form, setForm] = useState({
    title: '', equipment_type: 'auto', submittal_number: '',
    manufacturer: '', model_number: '', spec_section: '',
    submitted_by: '', contractor: '',
  });
  const [files, setFiles] = useState<File[]>([]);
  const [batchIds, setBatchIds] = useState<number[]>([]);
  const [batchActive, setBatchActive] = useState(false);

  useEffect(() => {
    if (projectId) loadData();
  }, [projectId]);

  // Poll for batch review progress
  useEffect(() => {
    if (!batchActive || batchIds.length === 0) return;
    const interval = setInterval(async () => {
      const res = await getSubmittals(Number(projectId));
      setSubmittals(res.data);
      const batchSubmittals = res.data.filter((s: Submittal) => batchIds.includes(s.id));
      const allDone = batchSubmittals.every((s: Submittal) => s.status !== 'reviewing');
      if (allDone) {
        setBatchActive(false);
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [batchActive, batchIds, projectId]);

  // Close modal on Escape key
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && showUpload) setShowUpload(false);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [showUpload]);

  const loadData = async () => {
    try {
      const [projRes, subRes, eqRes] = await Promise.all([
        getProject(Number(projectId)),
        getSubmittals(Number(projectId)),
        getEquipmentTypes(),
      ]);
      setProject(projRes.data);
      setSubmittals(subRes.data);
      setEquipmentTypes(eqRes.data.equipment_types);
    } catch (e) {
      console.error('Failed to load project', e);
    }
  };

  const resetForm = () => {
    setFiles([]);
    setForm({ title: '', equipment_type: 'auto', submittal_number: '', manufacturer: '', model_number: '', spec_section: '', submitted_by: '', contractor: '' });
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (files.length === 0) return;

    setUploading(true);
    const uploadedIds: number[] = [];

    try {
      for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('project_id', String(projectId));
        // Use filename as title if no explicit title set, or append filename for batch
        const title = files.length === 1 && form.title
          ? form.title
          : file.name.replace(/\.pdf$/i, '');
        formData.append('title', title);
        Object.entries(form).forEach(([key, val]) => {
          if (val && key !== 'title') formData.append(key, val);
        });

        const res = await uploadSubmittal(formData);
        uploadedIds.push(res.data.id);
      }

      setShowUpload(false);
      resetForm();
      loadData();

      // Auto-trigger batch review if multiple files
      if (uploadedIds.length > 1) {
        await runBatchReview(uploadedIds);
        setBatchIds(uploadedIds);
        setBatchActive(true);
      }
    } catch (e) {
      console.error('Upload failed', e);
    } finally {
      setUploading(false);
    }
  };

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const dropped = Array.from(e.dataTransfer.files).filter(f => f.type === 'application/pdf');
    if (dropped.length > 0) {
      setFiles(prev => [...prev, ...dropped]);
    }
  }, []);

  // --- Stats ---
  const totalComments = submittals.reduce((sum, s) => sum + s.open_comments, 0);
  const reviewedCount = submittals.filter(s => ['reviewed', 'approved', 'rejected', 'revise_resubmit'].includes(s.status)).length;

  // --- Loading state ---
  if (!project) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-gray-300 dark:border-slate-600 border-t-blue-600" />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400">
        <Link to="/" className="hover:text-gray-900 dark:hover:text-slate-100 transition-colors flex items-center gap-1">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="m2.25 12 8.954-8.955a1.126 1.126 0 0 1 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" /></svg>
          Projects
        </Link>
        <svg className="w-3.5 h-3.5 text-gray-300 dark:text-slate-600" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" /></svg>
        <span className="text-gray-900 dark:text-slate-100 font-medium truncate max-w-xs">{project.name}</span>
      </nav>

      {/* Header Card */}
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100 tracking-tight">{project.name}</h1>
            {project.description && (
              <p className="mt-1 text-sm text-gray-500 dark:text-slate-400">{project.description}</p>
            )}
            <div className="mt-3 flex flex-wrap items-center gap-3">
              {project.client && (
                <span className="inline-flex items-center gap-1.5 text-sm text-gray-600 dark:text-slate-400">
                  <svg className="w-4 h-4 text-gray-400 dark:text-slate-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M2.25 21h19.5M3.75 3v18h16.5V3H3.75Zm3 3.75h3v3h-3v-3Zm6.75 0h3v3h-3v-3Zm-6.75 6h3v3h-3v-3Zm6.75 0h3v3h-3v-3Z" /></svg>
                  {project.client}
                </span>
              )}
              {project.location && (
                <span className="inline-flex items-center gap-1.5 text-sm text-gray-600 dark:text-slate-400">
                  <svg className="w-4 h-4 text-gray-400 dark:text-slate-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" /><path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1 1 15 0Z" /></svg>
                  {project.location}
                </span>
              )}
              {project.tier_level && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-xs font-semibold bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-700">
                  Tier {project.tier_level}
                </span>
              )}
            </div>
          </div>
          <button
            onClick={() => setShowUpload(true)}
            className="shrink-0 inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-semibold shadow-sm hover:bg-blue-700 active:bg-blue-800 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
            Upload Submittal
          </button>
        </div>

        {/* Stats Row */}
        {submittals.length > 0 && (
          <div className="mt-6 pt-5 border-t border-gray-100 dark:border-slate-700 grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900 dark:text-slate-100">{submittals.length}</div>
              <div className="text-xs text-gray-500 dark:text-slate-400 font-medium mt-0.5">Submittals</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900 dark:text-slate-100">{reviewedCount}</div>
              <div className="text-xs text-gray-500 dark:text-slate-400 font-medium mt-0.5">Reviewed</div>
            </div>
            <div className="text-center">
              <div className={`text-2xl font-bold ${totalComments > 0 ? 'text-orange-600' : 'text-gray-900 dark:text-slate-100'}`}>{totalComments}</div>
              <div className="text-xs text-gray-500 dark:text-slate-400 font-medium mt-0.5">Open Comments</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900 dark:text-slate-100">
                {submittals.reduce((sum, s) => sum + (s.page_count || 0), 0).toLocaleString()}
              </div>
              <div className="text-xs text-gray-500 dark:text-slate-400 font-medium mt-0.5">Total Pages</div>
            </div>
          </div>
        )}
      </div>

      {/* Upload Modal Overlay */}
      {showUpload && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="fixed inset-0 bg-gray-900/60 backdrop-blur-sm transition-opacity" onClick={() => !uploading && setShowUpload(false)} />
          <div className="flex min-h-full items-center justify-center p-4">
            <div className="relative w-full max-w-2xl bg-white dark:bg-slate-800 rounded-2xl shadow-2xl ring-1 ring-gray-200 dark:ring-slate-700">
              {/* Modal Header */}
              <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-slate-700">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-slate-100">Upload New Submittal</h3>
                  <p className="text-sm text-gray-500 dark:text-slate-400 mt-0.5">Add a submittal document for automated review</p>
                </div>
                <button
                  onClick={() => !uploading && setShowUpload(false)}
                  className="rounded-lg p-1.5 text-gray-400 dark:text-slate-500 hover:text-gray-600 dark:hover:text-slate-300 hover:bg-gray-100 dark:hover:bg-slate-600 transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
                </button>
              </div>

              {/* Modal Body */}
              <form onSubmit={handleUpload} className="p-6 space-y-5">
                {/* Drag & Drop Area */}
                <div
                  onDragEnter={handleDrag}
                  onDragLeave={handleDrag}
                  onDragOver={handleDrag}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={`relative cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition-all
                    ${dragActive
                      ? 'border-blue-400 bg-blue-50 dark:bg-blue-900/30 ring-4 ring-blue-100 dark:ring-blue-900/50'
                      : files.length > 0
                        ? 'border-emerald-300 dark:border-emerald-700 bg-emerald-50 dark:bg-emerald-900/30'
                        : 'border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-700 hover:border-gray-300 dark:hover:border-slate-600 hover:bg-gray-100 dark:hover:bg-slate-600'
                    }`}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf"
                    multiple
                    onChange={(e) => {
                      const selected = Array.from(e.target.files || []).filter(f => f.type === 'application/pdf');
                      if (selected.length > 0) setFiles(prev => [...prev, ...selected]);
                    }}
                    className="hidden"
                  />
                  {files.length > 0 ? (
                    <div className="space-y-3">
                      <div className="mx-auto w-12 h-12 rounded-xl bg-emerald-100 dark:bg-emerald-900/50 flex items-center justify-center">
                        <svg className="w-6 h-6 text-emerald-600 dark:text-emerald-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>
                      </div>
                      <div className="space-y-1">
                        {files.map((f, i) => (
                          <div key={i} className="flex items-center justify-center gap-2 text-sm">
                            <span className="font-medium text-gray-900 dark:text-slate-100">{f.name}</span>
                            <span className="text-gray-400 dark:text-slate-500 text-xs">{formatFileSize(f.size)}</span>
                            <button
                              type="button"
                              onClick={(e) => { e.stopPropagation(); setFiles(files.filter((_, j) => j !== i)); }}
                              className="text-red-400 hover:text-red-600 dark:hover:text-red-400 text-xs"
                            >
                              remove
                            </button>
                          </div>
                        ))}
                      </div>
                      <p className="text-xs text-gray-500 dark:text-slate-400">Click or drag to add more files</p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <div className="mx-auto w-12 h-12 rounded-xl bg-gray-100 dark:bg-slate-700 flex items-center justify-center">
                        <svg className="w-6 h-6 text-gray-400 dark:text-slate-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5" /></svg>
                      </div>
                      <p className="text-sm font-semibold text-gray-700 dark:text-slate-300">Drop your PDFs here, or click to browse</p>
                      <p className="text-xs text-gray-400 dark:text-slate-500">PDF files — select multiple for batch review</p>
                    </div>
                  )}
                </div>

                {/* Form Fields */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="col-span-2 sm:col-span-1">
                    <label className="block text-xs font-semibold text-gray-600 dark:text-slate-400 mb-1.5">Title {files.length <= 1 && <span className="text-red-400">*</span>}</label>
                    <input
                      placeholder={files.length > 1 ? "Auto-derived from filenames" : "e.g. Main Switchgear MSB-1"}
                      value={form.title}
                      onChange={(e) => setForm({ ...form, title: e.target.value })}
                      required={files.length <= 1}
                      className="w-full border border-gray-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm bg-white dark:bg-slate-800 placeholder:text-gray-400 dark:placeholder:text-slate-500 text-gray-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-shadow"
                    />
                  </div>
                  <div className="col-span-2 sm:col-span-1">
                    <label className="block text-xs font-semibold text-gray-600 dark:text-slate-400 mb-1.5">Equipment Type</label>
                    <select
                      value={form.equipment_type}
                      onChange={(e) => setForm({ ...form, equipment_type: e.target.value })}
                      className="w-full border border-gray-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm bg-white dark:bg-slate-800 text-gray-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-shadow"
                    >
                      <option value="auto">Auto-Detect (Recommended)</option>
                      {equipmentTypes.map((t) => (
                        <option key={t} value={t}>{t.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-gray-600 dark:text-slate-400 mb-1.5">Submittal Number</label>
                    <input
                      placeholder="e.g. E-001"
                      value={form.submittal_number}
                      onChange={(e) => setForm({ ...form, submittal_number: e.target.value })}
                      className="w-full border border-gray-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm bg-white dark:bg-slate-800 placeholder:text-gray-400 dark:placeholder:text-slate-500 text-gray-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-shadow"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-gray-600 dark:text-slate-400 mb-1.5">Manufacturer</label>
                    <input
                      placeholder="e.g. ABB"
                      value={form.manufacturer}
                      onChange={(e) => setForm({ ...form, manufacturer: e.target.value })}
                      className="w-full border border-gray-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm bg-white dark:bg-slate-800 placeholder:text-gray-400 dark:placeholder:text-slate-500 text-gray-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-shadow"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-gray-600 dark:text-slate-400 mb-1.5">Model Number</label>
                    <input
                      placeholder="e.g. Emax 2"
                      value={form.model_number}
                      onChange={(e) => setForm({ ...form, model_number: e.target.value })}
                      className="w-full border border-gray-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm bg-white dark:bg-slate-800 placeholder:text-gray-400 dark:placeholder:text-slate-500 text-gray-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-shadow"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-gray-600 dark:text-slate-400 mb-1.5">Spec Section</label>
                    <input
                      placeholder="e.g. 26 24 16"
                      value={form.spec_section}
                      onChange={(e) => setForm({ ...form, spec_section: e.target.value })}
                      className="w-full border border-gray-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm bg-white dark:bg-slate-800 placeholder:text-gray-400 dark:placeholder:text-slate-500 text-gray-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-shadow"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-gray-600 dark:text-slate-400 mb-1.5">Submitted By</label>
                    <input
                      placeholder="Name"
                      value={form.submitted_by}
                      onChange={(e) => setForm({ ...form, submitted_by: e.target.value })}
                      className="w-full border border-gray-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm bg-white dark:bg-slate-800 placeholder:text-gray-400 dark:placeholder:text-slate-500 text-gray-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-shadow"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-gray-600 dark:text-slate-400 mb-1.5">Contractor</label>
                    <input
                      placeholder="Company name"
                      value={form.contractor}
                      onChange={(e) => setForm({ ...form, contractor: e.target.value })}
                      className="w-full border border-gray-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm bg-white dark:bg-slate-800 placeholder:text-gray-400 dark:placeholder:text-slate-500 text-gray-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-shadow"
                    />
                  </div>
                </div>

                {/* Modal Footer */}
                <div className="flex items-center justify-end gap-3 pt-3 border-t border-gray-100 dark:border-slate-700">
                  <button
                    type="button"
                    onClick={() => { setShowUpload(false); resetForm(); }}
                    disabled={uploading}
                    className="px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-slate-300 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={uploading || files.length === 0 || (files.length === 1 && !form.title)}
                    className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-semibold text-white bg-blue-600 rounded-lg shadow-sm hover:bg-blue-700 active:bg-blue-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                  >
                    {uploading ? (
                      <>
                        <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
                        Uploading...
                      </>
                    ) : (
                      <>
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5" /></svg>
                        {files.length > 1 ? `Upload & Review (${files.length} files)` : 'Upload & Create'}
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Batch Review Progress */}
      {batchActive && batchIds.length > 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-blue-200 dark:border-blue-800 shadow-sm p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-blue-700 dark:text-blue-400 flex items-center gap-2">
              <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
              Batch Review in Progress
            </h3>
            <span className="text-xs text-gray-500 dark:text-slate-400">
              {submittals.filter(s => batchIds.includes(s.id) && s.status !== 'reviewing').length} of {batchIds.length} complete
            </span>
          </div>
          <div className="w-full bg-gray-200 dark:bg-slate-700 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-500"
              style={{ width: `${(submittals.filter(s => batchIds.includes(s.id) && s.status !== 'reviewing').length / batchIds.length) * 100}%` }}
            />
          </div>
          <div className="grid gap-2">
            {submittals.filter(s => batchIds.includes(s.id)).map(s => (
              <div key={s.id} className="flex items-center gap-3 text-sm">
                {s.status === 'reviewing' ? (
                  <svg className="animate-spin w-4 h-4 text-blue-500" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
                ) : (
                  <svg className="w-4 h-4 text-emerald-500" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>
                )}
                <span className="text-gray-700 dark:text-slate-300">{s.title}</span>
                {s.status !== 'reviewing' && (
                  <Link to={`/submittal/${s.id}`} className="text-xs text-blue-600 dark:text-blue-400 hover:underline ml-auto">
                    View Report
                  </Link>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Submittals Section */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-slate-100">
            Submittals
            {submittals.length > 0 && (
              <span className="ml-2 text-sm font-normal text-gray-400 dark:text-slate-500">({submittals.length})</span>
            )}
          </h2>
        </div>

        {submittals.length === 0 ? (
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm py-16 text-center">
            <div className="mx-auto w-16 h-16 rounded-2xl bg-gray-100 dark:bg-slate-700 flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-gray-400 dark:text-slate-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" /></svg>
            </div>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-slate-100">No submittals yet</h3>
            <p className="text-sm text-gray-500 dark:text-slate-400 mt-1 mb-4">Upload a submittal PDF to begin automated review.</p>
            <button
              onClick={() => setShowUpload(true)}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
              Upload your first submittal
            </button>
          </div>
        ) : (
          <div className="grid gap-3">
            {submittals.map((s) => (
              <Link
                key={s.id}
                to={`/submittal/${s.id}`}
                className="group bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm hover:shadow-md hover:border-gray-300 dark:hover:border-slate-600 transition-all p-5 flex items-center gap-5"
              >
                {/* Equipment Icon */}
                <div className={`shrink-0 w-11 h-11 rounded-xl flex items-center justify-center text-lg ${getEquipmentStyle(s.equipment_type).bg} ${getEquipmentStyle(s.equipment_type).border} border`}>
                  {getEquipmentStyle(s.equipment_type).icon}
                </div>

                {/* Main Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2.5 flex-wrap">
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors truncate">
                      {s.title}
                    </h3>
                    <StatusBadge status={s.status} />
                  </div>
                  <div className="flex items-center gap-3 mt-1.5 flex-wrap">
                    <EquipmentBadge type={s.equipment_type} />
                    {s.submittal_number && (
                      <span className="text-xs text-gray-500 dark:text-slate-400 font-mono bg-gray-100 dark:bg-slate-700 px-1.5 py-0.5 rounded">#{s.submittal_number}</span>
                    )}
                    {s.manufacturer && (
                      <span className="text-xs text-gray-500 dark:text-slate-400">{s.manufacturer}</span>
                    )}
                    {s.contractor && (
                      <span className="text-xs text-gray-400 dark:text-slate-500">via {s.contractor}</span>
                    )}
                  </div>
                </div>

                {/* Right Side Stats */}
                <div className="shrink-0 flex items-center gap-5 text-right">
                  {s.open_comments > 0 && (
                    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-orange-50 dark:bg-orange-900/30 border border-orange-200 dark:border-orange-700">
                      <svg className="w-3.5 h-3.5 text-orange-500" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" /></svg>
                      <span className="text-xs font-semibold text-orange-700 dark:text-orange-400">{s.open_comments}</span>
                    </div>
                  )}
                  <div className="text-right">
                    {s.page_count && (
                      <div className="text-xs text-gray-500 dark:text-slate-400 font-medium">{s.page_count.toLocaleString()} pg</div>
                    )}
                    {s.file_size && (
                      <div className="text-xs text-gray-400 dark:text-slate-500">{formatFileSize(s.file_size)}</div>
                    )}
                  </div>
                  <div className="text-xs text-gray-400 dark:text-slate-500 whitespace-nowrap">{timeAgo(s.created_at)}</div>
                  <svg className="w-4 h-4 text-gray-300 dark:text-slate-600 group-hover:text-blue-500 dark:group-hover:text-blue-400 transition-colors shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" /></svg>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
