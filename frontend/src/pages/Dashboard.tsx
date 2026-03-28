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
    { label: 'Projects', value: stats.total_projects, color: 'bg-blue-500' },
    { label: 'Submittals', value: stats.total_submittals, color: 'bg-green-500' },
    { label: 'Pending Review', value: stats.pending_review, color: 'bg-yellow-500' },
    { label: 'Open Comments', value: stats.open_comments, color: 'bg-orange-500' },
    { label: 'Critical Issues', value: stats.critical_issues, color: 'bg-red-500' },
  ] : [];

  return (
    <div className="space-y-6">
      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {statCards.map((s) => (
            <div key={s.label} className="bg-white rounded-lg shadow p-4">
              <div className={`w-2 h-2 rounded-full ${s.color} mb-2`} />
              <div className="text-2xl font-bold">{s.value}</div>
              <div className="text-sm text-gray-500">{s.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Projects */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">Projects</h2>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
        >
          + New Project
        </button>
      </div>

      {showCreate && (
        <form onSubmit={handleCreate} className="bg-white rounded-lg shadow p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <input
              placeholder="Project Name *"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
              className="border rounded px-3 py-2 text-sm"
            />
            <input
              placeholder="Client"
              value={form.client}
              onChange={(e) => setForm({ ...form, client: e.target.value })}
              className="border rounded px-3 py-2 text-sm"
            />
            <input
              placeholder="Location"
              value={form.location}
              onChange={(e) => setForm({ ...form, location: e.target.value })}
              className="border rounded px-3 py-2 text-sm"
            />
            <select
              value={form.tier_level}
              onChange={(e) => setForm({ ...form, tier_level: e.target.value })}
              className="border rounded px-3 py-2 text-sm"
            >
              <option value="I">Tier I</option>
              <option value="II">Tier II</option>
              <option value="III">Tier III</option>
              <option value="IV">Tier IV</option>
            </select>
          </div>
          <input
            placeholder="Description"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="border rounded px-3 py-2 text-sm w-full"
          />
          <div className="flex gap-2">
            <button type="submit" className="px-4 py-2 bg-green-600 text-white rounded text-sm hover:bg-green-700">
              Create Project
            </button>
            <button type="button" onClick={() => setShowCreate(false)} className="px-4 py-2 bg-gray-200 rounded text-sm">
              Cancel
            </button>
          </div>
        </form>
      )}

      <div className="grid gap-4">
        {projects.map((project) => (
          <Link
            key={project.id}
            to={`/project/${project.id}`}
            className="bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow flex items-center justify-between"
          >
            <div>
              <h3 className="font-semibold text-lg">{project.name}</h3>
              <div className="text-sm text-gray-500 flex gap-4 mt-1">
                {project.client && <span>Client: {project.client}</span>}
                {project.location && <span>Location: {project.location}</span>}
                {project.tier_level && <span>Tier {project.tier_level}</span>}
              </div>
              {project.description && <p className="text-sm text-gray-400 mt-1">{project.description}</p>}
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-blue-600">{project.submittal_count}</div>
              <div className="text-xs text-gray-400">submittals</div>
            </div>
          </Link>
        ))}
        {projects.length === 0 && (
          <div className="text-center py-12 text-gray-400">
            No projects yet. Create one to get started.
          </div>
        )}
      </div>
    </div>
  );
}
