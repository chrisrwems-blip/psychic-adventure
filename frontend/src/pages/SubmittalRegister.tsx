import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getRegister, addRegisterItem, updateRegisterItem, getProjects } from '../api/client';
import type { RegisterItem, Project } from '../types';

export default function SubmittalRegister() {
  const [items, setItems] = useState<RegisterItem[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newItem, setNewItem] = useState({ spec_section: '', description: '', priority: 'medium' });

  useEffect(() => {
    getProjects().then((res) => {
      setProjects(res.data);
      if (res.data.length > 0) {
        setSelectedProject(res.data[0].id);
      } else {
        setLoading(false);
      }
    });
  }, []);

  useEffect(() => {
    if (selectedProject) loadRegister();
  }, [selectedProject]);

  const loadRegister = async () => {
    if (!selectedProject) return;
    try {
      setLoading(true);
      const res = await getRegister(selectedProject);
      setItems(res.data);
    } catch (e) {
      console.error('Failed to load register', e);
    } finally {
      setLoading(false);
    }
  };

  const handleAddItem = async () => {
    if (!selectedProject || !newItem.spec_section || !newItem.description) return;
    try {
      await addRegisterItem(selectedProject, newItem);
      setNewItem({ spec_section: '', description: '', priority: 'medium' });
      setShowAddForm(false);
      loadRegister();
    } catch (e) {
      console.error('Failed to add register item', e);
    }
  };

  const handleStatusChange = async (itemId: number, status: string) => {
    try {
      await updateRegisterItem(itemId, { status });
      loadRegister();
    } catch (e) {
      console.error('Failed to update register item', e);
    }
  };

  const statusBadge = (status: string) => {
    switch (status) {
      case 'not_submitted': return 'bg-red-100 text-red-700 ring-1 ring-red-200';
      case 'under_review': return 'bg-amber-100 text-amber-700 ring-1 ring-amber-200';
      case 'approved': return 'bg-emerald-100 text-emerald-700 ring-1 ring-emerald-200';
      case 'approved_as_noted': return 'bg-blue-100 text-blue-700 ring-1 ring-blue-200';
      case 'rejected': return 'bg-red-100 text-red-700 ring-1 ring-red-200';
      case 'resubmit': return 'bg-orange-100 text-orange-700 ring-1 ring-orange-200';
      default: return 'bg-slate-100 text-slate-600 ring-1 ring-slate-200';
    }
  };

  const priorityBadge = (priority: string) => {
    switch (priority) {
      case 'high': return 'badge-critical';
      case 'medium': return 'badge-major';
      case 'low': return 'badge-minor';
      default: return 'badge-info';
    }
  };

  const statusLabel = (status: string) => status.replace(/_/g, ' ');

  const stats = {
    total: items.length,
    not_submitted: items.filter((i) => i.status === 'not_submitted').length,
    under_review: items.filter((i) => i.status === 'under_review').length,
    approved: items.filter((i) => i.status === 'approved' || i.status === 'approved_as_noted').length,
    rejected: items.filter((i) => i.status === 'rejected' || i.status === 'resubmit').length,
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Submittal Register</h1>
          <p className="mt-1 text-sm text-slate-500">Track all required submittals for a project</p>
        </div>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="btn-primary"
          disabled={!selectedProject}
        >
          <span className="flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add Item
          </span>
        </button>
      </div>

      {/* Project Selector */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <div className="flex items-center gap-4">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Project</span>
          <select
            value={selectedProject ?? ''}
            onChange={(e) => setSelectedProject(Number(e.target.value))}
            className="input text-sm"
          >
            {projects.length === 0 && <option value="">No projects</option>}
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          <span className="text-xs text-slate-400 ml-auto">{items.length} items</span>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-5 gap-3">
        {[
          { label: 'Total', value: stats.total, color: 'from-slate-500 to-slate-600' },
          { label: 'Not Submitted', value: stats.not_submitted, color: 'from-red-500 to-red-600' },
          { label: 'Under Review', value: stats.under_review, color: 'from-amber-500 to-amber-600' },
          { label: 'Approved', value: stats.approved, color: 'from-emerald-500 to-emerald-600' },
          { label: 'Rejected', value: stats.rejected, color: 'from-red-400 to-red-500' },
        ].map((s) => (
          <div key={s.label} className="relative bg-white rounded-xl border border-slate-200 p-4 overflow-hidden">
            <div className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${s.color}`} />
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">{s.label}</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">{s.value}</p>
          </div>
        ))}
      </div>

      {/* Add Item Form */}
      {showAddForm && (
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h3 className="text-sm font-bold text-slate-800 mb-4">Add Register Item</h3>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1.5">Spec Section</label>
              <input
                type="text"
                value={newItem.spec_section}
                onChange={(e) => setNewItem({ ...newItem, spec_section: e.target.value })}
                placeholder="e.g., 26 24 16"
                className="input w-full"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1.5">Description</label>
              <input
                type="text"
                value={newItem.description}
                onChange={(e) => setNewItem({ ...newItem, description: e.target.value })}
                placeholder="e.g., Panelboards"
                className="input w-full"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1.5">Priority</label>
              <select
                value={newItem.priority}
                onChange={(e) => setNewItem({ ...newItem, priority: e.target.value })}
                className="input w-full"
              >
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
          </div>
          <div className="flex items-center gap-2 mt-4">
            <button onClick={handleAddItem} className="btn-primary text-sm">Add Item</button>
            <button onClick={() => setShowAddForm(false)} className="btn-secondary text-sm">Cancel</button>
          </div>
        </div>
      )}

      {/* Register Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="bg-slate-50/80 border-b border-slate-200">
              <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Spec Section</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Description</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Status</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Priority</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Linked Submittal</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Due Date</th>
              <th className="text-right px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {items.map((item) => (
              <tr key={item.id} className="hover:bg-slate-50/50 transition-colors">
                <td className="px-5 py-3.5">
                  <span className="text-sm font-mono font-medium text-slate-700">{item.spec_section}</span>
                </td>
                <td className="px-5 py-3.5">
                  <span className="text-sm text-slate-700">{item.description}</span>
                  {item.notes && (
                    <p className="text-xs text-slate-400 mt-0.5">{item.notes}</p>
                  )}
                </td>
                <td className="px-5 py-3.5">
                  <span className={`badge ${statusBadge(item.status)}`}>
                    {statusLabel(item.status)}
                  </span>
                </td>
                <td className="px-5 py-3.5">
                  <span className={`badge ${priorityBadge(item.priority)}`}>{item.priority}</span>
                </td>
                <td className="px-5 py-3.5">
                  {item.submittal_id ? (
                    <Link
                      to={`/submittal/${item.submittal_id}`}
                      className="text-xs text-blue-600 hover:text-blue-800 font-medium hover:underline"
                    >
                      {item.submittal_title || `Submittal #${item.submittal_id}`}
                    </Link>
                  ) : (
                    <span className="text-xs text-slate-400">--</span>
                  )}
                </td>
                <td className="px-5 py-3.5">
                  {item.due_date ? (
                    <span className="text-xs text-slate-500">
                      {new Date(item.due_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                    </span>
                  ) : (
                    <span className="text-xs text-slate-400">--</span>
                  )}
                </td>
                <td className="px-5 py-3.5 text-right">
                  <select
                    value={item.status}
                    onChange={(e) => handleStatusChange(item.id, e.target.value)}
                    className="text-xs border border-slate-200 rounded-lg px-2 py-1 bg-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20"
                  >
                    <option value="not_submitted">Not Submitted</option>
                    <option value="under_review">Under Review</option>
                    <option value="approved">Approved</option>
                    <option value="approved_as_noted">Approved as Noted</option>
                    <option value="rejected">Rejected</option>
                    <option value="resubmit">Resubmit</option>
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!loading && items.length === 0 && (
          <div className="text-center py-16">
            <div className="w-16 h-16 mx-auto mb-4 bg-slate-100 rounded-2xl flex items-center justify-center">
              <svg className="w-8 h-8 text-slate-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z" />
              </svg>
            </div>
            <h3 className="text-sm font-semibold text-slate-700">No register items</h3>
            <p className="text-sm text-slate-400 mt-1">Click "Add Item" to start building the submittal register</p>
          </div>
        )}
      </div>
    </div>
  );
}
