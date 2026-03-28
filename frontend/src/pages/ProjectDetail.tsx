import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getProject, getSubmittals, uploadSubmittal, getEquipmentTypes } from '../api/client';
import type { Project, Submittal } from '../types';

const STATUS_COLORS: Record<string, string> = {
  uploaded: 'bg-gray-200 text-gray-700',
  reviewing: 'bg-yellow-100 text-yellow-800',
  reviewed: 'bg-blue-100 text-blue-800',
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
  revise_resubmit: 'bg-orange-100 text-orange-800',
};

export default function ProjectDetail() {
  const { projectId } = useParams();
  const [project, setProject] = useState<Project | null>(null);
  const [submittals, setSubmittals] = useState<Submittal[]>([]);
  const [equipmentTypes, setEquipmentTypes] = useState<string[]>([]);
  const [showUpload, setShowUpload] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [form, setForm] = useState({
    title: '', equipment_type: 'switchgear', submittal_number: '',
    manufacturer: '', model_number: '', spec_section: '',
    submitted_by: '', contractor: '',
  });
  const [file, setFile] = useState<File | null>(null);

  useEffect(() => {
    if (projectId) loadData();
  }, [projectId]);

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

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('project_id', String(projectId));
    Object.entries(form).forEach(([key, val]) => {
      if (val) formData.append(key, val);
    });

    try {
      await uploadSubmittal(formData);
      setShowUpload(false);
      setFile(null);
      setForm({ title: '', equipment_type: 'switchgear', submittal_number: '', manufacturer: '', model_number: '', spec_section: '', submitted_by: '', contractor: '' });
      loadData();
    } catch (e) {
      console.error('Upload failed', e);
    } finally {
      setUploading(false);
    }
  };

  if (!project) return <div className="text-center py-12 text-gray-400">Loading...</div>;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Link to="/" className="text-sm text-blue-600 hover:underline">&larr; All Projects</Link>
          <h2 className="text-2xl font-bold mt-1">{project.name}</h2>
          <div className="text-sm text-gray-500 flex gap-4">
            {project.client && <span>Client: {project.client}</span>}
            {project.tier_level && <span>Tier {project.tier_level}</span>}
          </div>
        </div>
        <button
          onClick={() => setShowUpload(!showUpload)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
        >
          + Upload Submittal
        </button>
      </div>

      {/* Upload Form */}
      {showUpload && (
        <form onSubmit={handleUpload} className="bg-white rounded-lg shadow p-4 space-y-3">
          <h3 className="font-semibold">Upload New Submittal</h3>
          <div className="grid grid-cols-2 gap-3">
            <input placeholder="Title *" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required className="border rounded px-3 py-2 text-sm" />
            <select value={form.equipment_type} onChange={(e) => setForm({ ...form, equipment_type: e.target.value })} className="border rounded px-3 py-2 text-sm">
              {equipmentTypes.map((t) => (
                <option key={t} value={t}>{t.replace('_', ' ').toUpperCase()}</option>
              ))}
            </select>
            <input placeholder="Submittal Number" value={form.submittal_number} onChange={(e) => setForm({ ...form, submittal_number: e.target.value })} className="border rounded px-3 py-2 text-sm" />
            <input placeholder="Manufacturer" value={form.manufacturer} onChange={(e) => setForm({ ...form, manufacturer: e.target.value })} className="border rounded px-3 py-2 text-sm" />
            <input placeholder="Model Number" value={form.model_number} onChange={(e) => setForm({ ...form, model_number: e.target.value })} className="border rounded px-3 py-2 text-sm" />
            <input placeholder="Spec Section" value={form.spec_section} onChange={(e) => setForm({ ...form, spec_section: e.target.value })} className="border rounded px-3 py-2 text-sm" />
            <input placeholder="Submitted By" value={form.submitted_by} onChange={(e) => setForm({ ...form, submitted_by: e.target.value })} className="border rounded px-3 py-2 text-sm" />
            <input placeholder="Contractor" value={form.contractor} onChange={(e) => setForm({ ...form, contractor: e.target.value })} className="border rounded px-3 py-2 text-sm" />
          </div>
          <div className="border-2 border-dashed rounded-lg p-4 text-center">
            <input type="file" accept=".pdf" onChange={(e) => setFile(e.target.files?.[0] || null)} className="text-sm" />
            <p className="text-xs text-gray-400 mt-1">PDF files only</p>
          </div>
          <div className="flex gap-2">
            <button type="submit" disabled={uploading || !file} className="px-4 py-2 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:opacity-50">
              {uploading ? 'Uploading...' : 'Upload & Create'}
            </button>
            <button type="button" onClick={() => setShowUpload(false)} className="px-4 py-2 bg-gray-200 rounded text-sm">Cancel</button>
          </div>
        </form>
      )}

      {/* Submittals List */}
      <div className="space-y-3">
        {submittals.map((s) => (
          <Link
            key={s.id}
            to={`/submittal/${s.id}`}
            className="bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow flex items-center justify-between block"
          >
            <div className="flex-1">
              <div className="flex items-center gap-3">
                <h3 className="font-semibold">{s.title}</h3>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[s.status] || 'bg-gray-100'}`}>
                  {s.status.replace('_', ' ')}
                </span>
              </div>
              <div className="text-sm text-gray-500 flex gap-4 mt-1">
                <span className="font-medium text-blue-600">{s.equipment_type.replace('_', ' ').toUpperCase()}</span>
                {s.submittal_number && <span>#{s.submittal_number}</span>}
                {s.manufacturer && <span>{s.manufacturer}</span>}
                {s.contractor && <span>Contractor: {s.contractor}</span>}
              </div>
            </div>
            <div className="text-right text-sm">
              {s.open_comments > 0 && (
                <div className="text-orange-600 font-medium">{s.open_comments} open comments</div>
              )}
              {s.page_count && <div className="text-gray-400">{s.page_count} pages</div>}
            </div>
          </Link>
        ))}
        {submittals.length === 0 && (
          <div className="text-center py-12 text-gray-400">No submittals yet. Upload one to begin review.</div>
        )}
      </div>
    </div>
  );
}
