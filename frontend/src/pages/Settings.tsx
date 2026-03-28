import { useState, useEffect } from 'react';
import { getEmailSettings, saveEmailSettings, deleteEmailSettings, detectSmtpProvider, testEmailConnection, getProfile, saveProfile } from '../api/client';

export default function Settings() {
  const [form, setForm] = useState({ email: '', password: '', host: '', port: 587, display_name: '' });
  const [configured, setConfigured] = useState(false);
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const [profile, setProfile] = useState({
    reviewer_name: '', reviewer_title: '',
    company_name: '', company_address: '', company_phone: '',
    default_jurisdiction: 'auto', review_sla_days: 5, report_min_severity: 'minor',
  });
  const [profileSaved, setProfileSaved] = useState(false);
  const [savingProfile, setSavingProfile] = useState(false);

  useEffect(() => {
    loadSettings();
    loadProfile();
  }, []);

  const loadSettings = async () => {
    try {
      const res = await getEmailSettings();
      if (res.data.configured) {
        setConfigured(true);
        setForm(f => ({ ...f, email: res.data.email, host: res.data.host, port: res.data.port, display_name: res.data.display_name || '' }));
      }
    } catch (e) {
      console.error('Failed to load settings', e);
    }
  };

  const handleEmailBlur = async () => {
    if (!form.email.includes('@')) return;
    try {
      const res = await detectSmtpProvider(form.email);
      setForm(f => ({ ...f, host: res.data.host, port: res.data.port }));
      if (!res.data.detected) setShowAdvanced(true);
    } catch (e) {
      console.error('Detection failed', e);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await testEmailConnection({ email: form.email, password: form.password, host: form.host, port: form.port });
      setTestResult(res.data);
    } catch (e) {
      setTestResult({ success: false, message: 'Connection test failed' });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await saveEmailSettings(form);
      setConfigured(true);
      setTestResult({ success: true, message: 'Settings saved successfully' });
    } catch (e) {
      console.error('Save failed', e);
    } finally {
      setSaving(false);
    }
  };

  const handleDisconnect = async () => {
    await deleteEmailSettings();
    setConfigured(false);
    setForm({ email: '', password: '', host: '', port: 587, display_name: '' });
    setTestResult(null);
  };

  const loadProfile = async () => {
    try {
      const res = await getProfile();
      setProfile(res.data);
    } catch (e) {
      console.error('Failed to load profile', e);
    }
  };

  const handleSaveProfile = async () => {
    setSavingProfile(true);
    setProfileSaved(false);
    try {
      await saveProfile(profile);
      setProfileSaved(true);
      setTimeout(() => setProfileSaved(false), 3000);
    } catch (e) {
      console.error('Failed to save profile', e);
    } finally {
      setSavingProfile(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100 tracking-tight">Settings</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-slate-400">Configure ArcLight to work with your tools</p>
      </div>

      {/* Email Configuration */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 dark:border-slate-700 bg-gray-50/80 dark:bg-slate-800/80">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center">
                <svg className="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75" />
                </svg>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-gray-900 dark:text-slate-100">Email</h3>
                <p className="text-xs text-gray-500 dark:text-slate-400">Send RFIs and review emails directly from ArcLight</p>
              </div>
            </div>
            {configured && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 ring-1 ring-emerald-200 dark:ring-emerald-800">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                Connected
              </span>
            )}
          </div>
        </div>

        <div className="p-6 space-y-5">
          {/* Email Address */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1.5">
              Email Address
            </label>
            <input
              type="email"
              placeholder="you@company.com"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              onBlur={handleEmailBlur}
              className="w-full border border-gray-300 dark:border-slate-600 rounded-lg px-3.5 py-2.5 text-sm text-gray-900 dark:text-slate-200 bg-white dark:bg-slate-700 placeholder:text-gray-400 dark:placeholder:text-slate-500 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            />
          </div>

          {/* Password */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1.5">
              Password
            </label>
            <input
              type="password"
              placeholder={configured ? '••••••••••' : 'Your email password or app password'}
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              className="w-full border border-gray-300 dark:border-slate-600 rounded-lg px-3.5 py-2.5 text-sm text-gray-900 dark:text-slate-200 bg-white dark:bg-slate-700 placeholder:text-gray-400 dark:placeholder:text-slate-500 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            />
            <p className="mt-1.5 text-xs text-gray-400 dark:text-slate-500">
              If you use two-factor authentication, you'll need an app-specific password.
              {form.host?.includes('gmail') && ' Google: Account → Security → App Passwords.'}
              {form.host?.includes('office365') && ' Microsoft: account.microsoft.com → Security → App Passwords.'}
            </p>
          </div>

          {/* Display Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1.5">
              Display Name
            </label>
            <input
              type="text"
              placeholder="Chris Williams"
              value={form.display_name}
              onChange={(e) => setForm({ ...form, display_name: e.target.value })}
              className="w-full border border-gray-300 dark:border-slate-600 rounded-lg px-3.5 py-2.5 text-sm text-gray-900 dark:text-slate-200 bg-white dark:bg-slate-700 placeholder:text-gray-400 dark:placeholder:text-slate-500 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            />
          </div>

          {/* Advanced Settings (collapsible) */}
          <div>
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="text-xs font-medium text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-300 flex items-center gap-1"
            >
              <svg className={`w-3 h-3 transition-transform ${showAdvanced ? 'rotate-90' : ''}`} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
              </svg>
              Advanced Settings
            </button>
            {showAdvanced && (
              <div className="mt-3 grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">Outgoing Mail Server</label>
                  <input
                    type="text"
                    value={form.host}
                    onChange={(e) => setForm({ ...form, host: e.target.value })}
                    className="w-full border border-gray-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-slate-200 bg-white dark:bg-slate-700 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">Port</label>
                  <input
                    type="number"
                    value={form.port}
                    onChange={(e) => setForm({ ...form, port: parseInt(e.target.value) || 587 })}
                    className="w-full border border-gray-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-slate-200 bg-white dark:bg-slate-700 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Test Result */}
          {testResult && (
            <div className={`rounded-lg px-4 py-3 text-sm flex items-center gap-2 ${
              testResult.success
                ? 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400'
                : 'bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-400'
            }`}>
              {testResult.success ? (
                <svg className="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                </svg>
              ) : (
                <svg className="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
                </svg>
              )}
              {testResult.message}
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center gap-3 pt-2 border-t border-gray-100 dark:border-slate-700">
            <button
              onClick={handleTest}
              disabled={!form.email || !form.password || testing}
              className="px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-slate-300 bg-white dark:bg-slate-700 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 transition-colors disabled:opacity-50"
            >
              {testing ? 'Testing...' : 'Test Connection'}
            </button>
            <button
              onClick={handleSave}
              disabled={!form.email || !form.password || saving}
              className="px-5 py-2.5 text-sm font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 shadow-sm transition-colors disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save Settings'}
            </button>
            {configured && (
              <button
                onClick={handleDisconnect}
                className="px-4 py-2.5 text-sm font-medium text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 ml-auto transition-colors"
              >
                Disconnect
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Reviewer & Company Profile */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 dark:border-slate-700 bg-gray-50/80 dark:bg-slate-800/80">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-50 dark:bg-emerald-900/30 flex items-center justify-center">
              <svg className="w-5 h-5 text-emerald-600 dark:text-emerald-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
              </svg>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-900 dark:text-slate-100">Reviewer & Company</h3>
              <p className="text-xs text-gray-500 dark:text-slate-400">Pre-fills approval stamps, emails, and report headers</p>
            </div>
          </div>
        </div>
        <div className="p-6 space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1.5">Reviewer Name</label>
              <input
                type="text"
                placeholder="Chris Williams, PE"
                value={profile.reviewer_name}
                onChange={(e) => setProfile({ ...profile, reviewer_name: e.target.value })}
                className="w-full border border-gray-300 dark:border-slate-600 rounded-lg px-3.5 py-2.5 text-sm text-gray-900 dark:text-slate-200 bg-white dark:bg-slate-700 placeholder:text-gray-400 dark:placeholder:text-slate-500 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1.5">Title</label>
              <input
                type="text"
                placeholder="Senior Electrical Engineer"
                value={profile.reviewer_title}
                onChange={(e) => setProfile({ ...profile, reviewer_title: e.target.value })}
                className="w-full border border-gray-300 dark:border-slate-600 rounded-lg px-3.5 py-2.5 text-sm text-gray-900 dark:text-slate-200 bg-white dark:bg-slate-700 placeholder:text-gray-400 dark:placeholder:text-slate-500 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1.5">Company Name</label>
            <input
              type="text"
              placeholder="POSITRON"
              value={profile.company_name}
              onChange={(e) => setProfile({ ...profile, company_name: e.target.value })}
              className="w-full border border-gray-300 dark:border-slate-600 rounded-lg px-3.5 py-2.5 text-sm text-gray-900 dark:text-slate-200 bg-white dark:bg-slate-700 placeholder:text-gray-400 dark:placeholder:text-slate-500 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1.5">Company Address</label>
              <input
                type="text"
                placeholder="123 Main St, Dallas, TX 75201"
                value={profile.company_address}
                onChange={(e) => setProfile({ ...profile, company_address: e.target.value })}
                className="w-full border border-gray-300 dark:border-slate-600 rounded-lg px-3.5 py-2.5 text-sm text-gray-900 dark:text-slate-200 bg-white dark:bg-slate-700 placeholder:text-gray-400 dark:placeholder:text-slate-500 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1.5">Phone</label>
              <input
                type="text"
                placeholder="(214) 555-0100"
                value={profile.company_phone}
                onChange={(e) => setProfile({ ...profile, company_phone: e.target.value })}
                className="w-full border border-gray-300 dark:border-slate-600 rounded-lg px-3.5 py-2.5 text-sm text-gray-900 dark:text-slate-200 bg-white dark:bg-slate-700 placeholder:text-gray-400 dark:placeholder:text-slate-500 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Review Preferences */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 dark:border-slate-700 bg-gray-50/80 dark:bg-slate-800/80">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-amber-50 dark:bg-amber-900/30 flex items-center justify-center">
              <svg className="w-5 h-5 text-amber-600 dark:text-amber-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 6h9.75M10.5 6a1.5 1.5 0 1 1-3 0m3 0a1.5 1.5 0 1 0-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m-9.75 0h9.75" />
              </svg>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-900 dark:text-slate-100">Review Preferences</h3>
              <p className="text-xs text-gray-500 dark:text-slate-400">Default settings for new reviews</p>
            </div>
          </div>
        </div>
        <div className="p-6 space-y-5">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1.5">Default Jurisdiction</label>
              <select
                value={profile.default_jurisdiction}
                onChange={(e) => setProfile({ ...profile, default_jurisdiction: e.target.value })}
                className="w-full border border-gray-300 dark:border-slate-600 rounded-lg px-3.5 py-2.5 text-sm text-gray-900 dark:text-slate-200 bg-white dark:bg-slate-700 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              >
                <option value="auto">Auto-Detect</option>
                <option value="NEC">NEC (US)</option>
                <option value="IEC">IEC (International)</option>
                <option value="AS/NZS">AS/NZS (Australia/NZ)</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1.5">Review SLA (days)</label>
              <select
                value={profile.review_sla_days}
                onChange={(e) => setProfile({ ...profile, review_sla_days: parseInt(e.target.value) })}
                className="w-full border border-gray-300 dark:border-slate-600 rounded-lg px-3.5 py-2.5 text-sm text-gray-900 dark:text-slate-200 bg-white dark:bg-slate-700 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              >
                <option value={3}>3 days</option>
                <option value={5}>5 days</option>
                <option value={7}>7 days</option>
                <option value={10}>10 days</option>
                <option value={14}>14 days</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1.5">Report Min Severity</label>
              <select
                value={profile.report_min_severity}
                onChange={(e) => setProfile({ ...profile, report_min_severity: e.target.value })}
                className="w-full border border-gray-300 dark:border-slate-600 rounded-lg px-3.5 py-2.5 text-sm text-gray-900 dark:text-slate-200 bg-white dark:bg-slate-700 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              >
                <option value="critical">Critical only</option>
                <option value="major">Critical + Major</option>
                <option value="minor">Critical + Major + Minor</option>
                <option value="info">All (including Info)</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Save Profile Button */}
      <div className="flex items-center gap-3">
        <button
          onClick={handleSaveProfile}
          disabled={savingProfile}
          className="px-5 py-2.5 text-sm font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 shadow-sm transition-colors disabled:opacity-50"
        >
          {savingProfile ? 'Saving...' : 'Save Profile & Preferences'}
        </button>
        {profileSaved && (
          <span className="text-sm text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
            </svg>
            Saved
          </span>
        )}
      </div>

      {/* Vision AI Status */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 dark:border-slate-700 bg-gray-50/80 dark:bg-slate-800/80">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-purple-50 dark:bg-purple-900/30 flex items-center justify-center">
              <svg className="w-5 h-5 text-purple-600 dark:text-purple-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178Z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
              </svg>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-900 dark:text-slate-100">Vision AI (Ollama)</h3>
              <p className="text-xs text-gray-500 dark:text-slate-400">Analyzes scanned drawings and nameplates using local AI</p>
            </div>
          </div>
        </div>
        <div className="p-6">
          <p className="text-sm text-gray-600 dark:text-slate-400">
            Vision analysis uses Ollama with the LLaVA model running locally on your machine. No cloud services or API keys needed.
          </p>
          <div className="mt-3 text-xs text-gray-500 dark:text-slate-500 space-y-1">
            <p>1. Install Ollama from ollama.com</p>
            <p>2. Run: <code className="bg-gray-100 dark:bg-slate-700 px-1.5 py-0.5 rounded font-mono">ollama pull llava</code></p>
            <p>3. ArcLight detects it automatically when running</p>
          </div>
        </div>
      </div>
    </div>
  );
}
