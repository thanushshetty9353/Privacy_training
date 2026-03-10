'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { apiFetch, getToken, setToken, setUser, getUser, clearToken } from '@/lib/api';
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, PointElement, LineElement,
  BarElement, ArcElement, Title, Tooltip, Legend, Filler
} from 'chart.js';
import { Line, Bar, Doughnut } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale, LinearScale, PointElement, LineElement,
  BarElement, ArcElement, Title, Tooltip, Legend, Filler
);

/* ════════════════════════════════════════════════════════════════
   ICONS (inline SVGs to avoid import issues)
   ════════════════════════════════════════════════════════════════ */
const Icon = ({ d, size = 18 }: { d: string; size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d={d} />
  </svg>
);

const Icons = {
  dashboard: <Icon d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />,
  jobs: <Icon d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />,
  orgs: <><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg></>,
  datasets: <Icon d="M4 7V4h16v3M9 20h6M12 4v16" />,
  models: <><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" /><polyline points="3.27 6.96 12 12.01 20.73 6.96" /><line x1="12" y1="22.08" x2="12" y2="12" /></svg></>,
  audit: <><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg></>,
  privacy: <><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></svg></>,
  logout: <Icon d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" />,
  plus: <Icon d="M12 5v14M5 12h14" />,
  play: <Icon d="M5 3l14 9-14 9V3z" />,
};

/* ════════════════════════════════════════════════════════════════
   TYPES
   ════════════════════════════════════════════════════════════════ */
interface Stats {
  total_organizations: number;
  total_datasets: number;
  total_jobs: number;
  active_jobs: number;
  completed_jobs: number;
  total_models: number;
  total_users: number;
}

interface Job {
  id: string; name: string; model_type: string; privacy_budget: number;
  noise_multiplier: number; max_grad_norm: number; training_rounds: number;
  min_clients: number; fraction_fit: number; status: string; current_round: number;
  final_accuracy: number | null; final_loss: number | null;
  epsilon_spent: number | null; model_path: string | null;
  created_by: string; created_at: string; started_at: string | null;
  completed_at: string | null;
}

interface Org { id: string; name: string; description: string | null; is_active: boolean; registered_at: string; }
interface Dataset { id: string; name: string; org_id: string; description: string | null; num_samples: number | null; sensitivity_level: string; created_at: string; }
interface AuditEntry { id: string; actor: string; actor_role: string | null; action: string; resource_type: string | null; resource_id: string | null; details: any; timestamp: string; }
interface Metric { round_number: number; train_loss: number | null; eval_loss: number | null; eval_accuracy: number | null; epsilon: number | null; num_clients: number | null; round_duration_sec: number | null; }

type Page = 'dashboard' | 'jobs' | 'organizations' | 'datasets' | 'models' | 'audit' | 'privacy';

/* ════════════════════════════════════════════════════════════════
   MAIN APP
   ════════════════════════════════════════════════════════════════ */
export default function Home() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isRegister, setIsRegister] = useState(false);
  const [page, setPage] = useState<Page>('dashboard');
  const [user, setUserState] = useState<any>(null);

  useEffect(() => {
    const t = getToken();
    const u = getUser();
    if (t && u) { setIsLoggedIn(true); setUserState(u); }
  }, []);

  const handleLogin = (token: string, userData: any) => {
    setToken(token);
    setUser(userData);
    setUserState(userData);
    setIsLoggedIn(true);
  };

  const handleLogout = () => {
    clearToken();
    setIsLoggedIn(false);
    setUserState(null);
    setPage('dashboard');
  };

  if (!isLoggedIn) {
    return isRegister
      ? <RegisterPage onLogin={handleLogin} onSwitch={() => setIsRegister(false)} />
      : <LoginPage onLogin={handleLogin} onSwitch={() => setIsRegister(true)} />;
  }

  return (
    <div className="app-layout">
      <Sidebar page={page} setPage={setPage} user={user} onLogout={handleLogout} />
      <main className="main-content">
        {page === 'dashboard' && <DashboardPage />}
        {page === 'jobs' && <JobsPage />}
        {page === 'organizations' && <OrganizationsPage />}
        {page === 'datasets' && <DatasetsPage />}
        {page === 'models' && <ModelsPage />}
        {page === 'audit' && <AuditPage />}
        {page === 'privacy' && <PrivacyPage />}
      </main>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════
   LOGIN / REGISTER
   ════════════════════════════════════════════════════════════════ */
function LoginPage({ onLogin, onSwitch }: { onLogin: (t: string, u: any) => void; onSwitch: () => void }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await apiFetch('/api/auth/login', { method: 'POST', body: { username, password } });
      onLogin(data.access_token, data.user);
    } catch (err: any) {
      setError(err.message || 'Login failed');
    }
    setLoading(false);
  };

  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-card">
          <div className="login-header">
            <div className="logo">🔒</div>
            <h2>PrivacyFL Platform</h2>
            <p>Privacy-Preserving Federated Learning</p>
          </div>
          {error && <div className="error-msg">{error}</div>}
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">Username</label>
              <input className="form-input" value={username} onChange={e => setUsername(e.target.value)} placeholder="Enter username" required />
            </div>
            <div className="form-group">
              <label className="form-label">Password</label>
              <input className="form-input" type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Enter password" required />
            </div>
            <button className="btn btn-primary" style={{ width: '100%' }} disabled={loading}>
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
          <div className="login-footer">
            Don't have an account?{' '}
            <button onClick={onSwitch}>Register</button>
          </div>
        </div>
      </div>
    </div>
  );
}

function RegisterPage({ onLogin, onSwitch }: { onLogin: (t: string, u: any) => void; onSwitch: () => void }) {
  const [form, setForm] = useState({ username: '', email: '', password: '', full_name: '', role: 'researcher' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await apiFetch('/api/auth/register', { method: 'POST', body: form });
      onLogin(data.access_token, data.user);
    } catch (err: any) {
      setError(err.message || 'Registration failed');
    }
    setLoading(false);
  };

  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-card">
          <div className="login-header">
            <div className="logo">🔒</div>
            <h2>Create Account</h2>
            <p>Join the PrivacyFL Platform</p>
          </div>
          {error && <div className="error-msg">{error}</div>}
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">Full Name</label>
              <input className="form-input" value={form.full_name} onChange={e => setForm({ ...form, full_name: e.target.value })} placeholder="John Doe" />
            </div>
            <div className="form-group">
              <label className="form-label">Username</label>
              <input className="form-input" value={form.username} onChange={e => setForm({ ...form, username: e.target.value })} placeholder="johndoe" required />
            </div>
            <div className="form-group">
              <label className="form-label">Email</label>
              <input className="form-input" type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} placeholder="john@hospital.org" required />
            </div>
            <div className="form-group">
              <label className="form-label">Password</label>
              <input className="form-input" type="password" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} placeholder="Min 6 characters" required />
            </div>
            <div className="form-group">
              <label className="form-label">Role</label>
              <select className="form-input" value={form.role} onChange={e => setForm({ ...form, role: e.target.value })}>
                <option value="researcher">Researcher</option>
                <option value="admin">Admin</option>
                <option value="org_node">Organization Node</option>
                <option value="auditor">Auditor</option>
              </select>
            </div>
            <button className="btn btn-primary" style={{ width: '100%' }} disabled={loading}>
              {loading ? 'Creating...' : 'Create Account'}
            </button>
          </form>
          <div className="login-footer">
            Already have an account?{' '}
            <button onClick={onSwitch}>Sign In</button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════
   SIDEBAR
   ════════════════════════════════════════════════════════════════ */
function Sidebar({ page, setPage, user, onLogout }: { page: Page; setPage: (p: Page) => void; user: any; onLogout: () => void }) {
  const navItems: { id: Page; label: string; icon: React.ReactNode }[] = [
    { id: 'dashboard', label: 'Dashboard', icon: Icons.dashboard },
    { id: 'jobs', label: 'Training Jobs', icon: Icons.jobs },
    { id: 'organizations', label: 'Organizations', icon: Icons.orgs },
    { id: 'datasets', label: 'Datasets', icon: Icons.datasets },
    { id: 'models', label: 'Models', icon: Icons.models },
    { id: 'privacy', label: 'Privacy Budget', icon: Icons.privacy },
    { id: 'audit', label: 'Audit Logs', icon: Icons.audit },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="logo-icon">🔒</div>
        <div>
          <h1>PrivacyFL</h1>
          <span>Federated Learning Platform</span>
        </div>
      </div>

      <nav>
        <div className="nav-section">
          <div className="nav-section-title">Main Menu</div>
          {navItems.map(item => (
            <button
              key={item.id}
              className={`nav-link ${page === item.id ? 'active' : ''}`}
              onClick={() => setPage(item.id)}
            >
              {item.icon}
              {item.label}
            </button>
          ))}
        </div>
      </nav>

      <div style={{ marginTop: 'auto' }}>
        <div style={{ padding: '12px', borderTop: '1px solid var(--border-color)', marginTop: '16px' }}>
          <div style={{ fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
            {user?.full_name || user?.username}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '12px' }}>
            {user?.role?.toUpperCase()} • {user?.email}
          </div>
          <button className="nav-link" onClick={onLogout} style={{ color: 'var(--accent-rose)' }}>
            {Icons.logout}
            Sign Out
          </button>
        </div>
      </div>
    </aside>
  );
}

/* ════════════════════════════════════════════════════════════════
   DASHBOARD PAGE
   ════════════════════════════════════════════════════════════════ */
function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [s, j] = await Promise.all([
        apiFetch('/api/dashboard/stats'),
        apiFetch('/api/jobs/'),
      ]);
      setStats(s);
      setJobs(j);

      // Load metrics for the most recent completed or running job
      const activeJob = j.find((job: Job) => job.status === 'running' || job.status === 'completed');
      if (activeJob) {
        const m = await apiFetch(`/api/jobs/${activeJob.id}/metrics`);
        setMetrics(m);
      }
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  if (loading) return <div className="loading">Loading dashboard...</div>;

  const statCards = [
    { label: 'Organizations', value: stats?.total_organizations || 0, color: 'indigo', icon: '🏥' },
    { label: 'Datasets', value: stats?.total_datasets || 0, color: 'cyan', icon: '📊' },
    { label: 'Total Jobs', value: stats?.total_jobs || 0, color: 'emerald', icon: '⚙️' },
    { label: 'Active Jobs', value: stats?.active_jobs || 0, color: 'amber', icon: '🔄' },
    { label: 'Completed', value: stats?.completed_jobs || 0, color: 'rose', icon: '✅' },
    { label: 'Users', value: stats?.total_users || 0, color: 'indigo', icon: '👤' },
  ];

  const lossData = {
    labels: metrics.map(m => `Round ${m.round_number}`),
    datasets: [
      {
        label: 'Train Loss',
        data: metrics.map(m => m.train_loss),
        borderColor: '#6366f1',
        backgroundColor: 'rgba(99,102,241,0.1)',
        fill: true, tension: 0.4,
      },
      {
        label: 'Eval Loss',
        data: metrics.map(m => m.eval_loss),
        borderColor: '#06b6d4',
        backgroundColor: 'rgba(6,182,212,0.1)',
        fill: true, tension: 0.4,
      },
    ],
  };

  const accData = {
    labels: metrics.map(m => `Round ${m.round_number}`),
    datasets: [{
      label: 'Accuracy',
      data: metrics.map(m => m.eval_accuracy ? m.eval_accuracy * 100 : null),
      borderColor: '#10b981',
      backgroundColor: 'rgba(16,185,129,0.1)',
      fill: true, tension: 0.4,
    }],
  };

  const chartOpts: any = {
    responsive: true,
    plugins: {
      legend: { labels: { color: '#9ca3af', font: { size: 12 } } },
    },
    scales: {
      x: { ticks: { color: '#6b7280' }, grid: { color: 'rgba(255,255,255,0.05)' } },
      y: { ticks: { color: '#6b7280' }, grid: { color: 'rgba(255,255,255,0.05)' } },
    },
  };

  return (
    <>
      <div className="page-header">
        <h2>Dashboard</h2>
        <p>Privacy-Preserving Federated Learning Platform Overview</p>
      </div>

      <div className="stats-grid">
        {statCards.map((s, i) => (
          <div key={i} className={`stat-card ${s.color}`}>
            <div className={`stat-icon ${s.color}`}>{s.icon}</div>
            <div className="stat-value">{s.value}</div>
            <div className="stat-label">{s.label}</div>
          </div>
        ))}
      </div>

      {metrics.length > 0 && (
        <div className="charts-grid">
          <div className="card">
            <div className="card-header">
              <span className="card-title">Training & Evaluation Loss</span>
            </div>
            <div className="chart-container">
              <Line data={lossData} options={chartOpts} />
            </div>
          </div>
          <div className="card">
            <div className="card-header">
              <span className="card-title">Model Accuracy (%)</span>
            </div>
            <div className="chart-container">
              <Line data={accData} options={chartOpts} />
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <span className="card-title">Recent Training Jobs</span>
        </div>
        {jobs.length === 0 ? (
          <div className="empty-state">
            <h3>No jobs yet</h3>
            <p>Create your first federated learning training job</p>
          </div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Model</th>
                  <th>Rounds</th>
                  <th>Status</th>
                  <th>Accuracy</th>
                  <th>Privacy (ε)</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {jobs.slice(0, 10).map(j => (
                  <tr key={j.id}>
                    <td style={{ fontWeight: 600 }}>{j.name}</td>
                    <td>{j.model_type}</td>
                    <td>{j.current_round}/{j.training_rounds}</td>
                    <td><span className={`badge ${j.status}`}>{j.status}</span></td>
                    <td>{j.final_accuracy ? `${(j.final_accuracy * 100).toFixed(1)}%` : '—'}</td>
                    <td>{j.epsilon_spent?.toFixed(4) ?? '—'}</td>
                    <td>{new Date(j.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}

/* ════════════════════════════════════════════════════════════════
   JOBS PAGE
   ════════════════════════════════════════════════════════════════ */
function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [jobMetrics, setJobMetrics] = useState<Metric[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadJobs(); }, []);

  const loadJobs = async () => {
    try {
      const data = await apiFetch('/api/jobs/');
      setJobs(data);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const startJob = async (jobId: string) => {
    try {
      await apiFetch(`/api/jobs/${jobId}/start`, { method: 'POST' });
      loadJobs();
    } catch (e: any) { alert(e.message); }
  };

  const viewMetrics = async (job: Job) => {
    setSelectedJob(job);
    try {
      const m = await apiFetch(`/api/jobs/${job.id}/metrics`);
      setJobMetrics(m);
    } catch (e) { setJobMetrics([]); }
  };

  const chartOpts: any = {
    responsive: true,
    plugins: { legend: { labels: { color: '#9ca3af' } } },
    scales: {
      x: { ticks: { color: '#6b7280' }, grid: { color: 'rgba(255,255,255,0.05)' } },
      y: { ticks: { color: '#6b7280' }, grid: { color: 'rgba(255,255,255,0.05)' } },
    },
  };

  if (loading) return <div className="loading">Loading jobs...</div>;

  return (
    <>
      <div className="page-header">
        <h2>Training Jobs</h2>
        <p>Create and monitor federated learning training jobs</p>
      </div>

      <div style={{ marginBottom: '24px' }}>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
          {Icons.plus} Create Training Job
        </button>
      </div>

      {showCreate && <CreateJobModal onClose={() => setShowCreate(false)} onCreated={() => { loadJobs(); setShowCreate(false); }} />}

      {selectedJob && (
        <div className="modal-overlay" onClick={() => setSelectedJob(null)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: '700px' }}>
            <h3>Job: {selectedJob.name}</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '20px', fontSize: '14px' }}>
              <div><strong>Model:</strong> {selectedJob.model_type}</div>
              <div><strong>Status:</strong> <span className={`badge ${selectedJob.status}`}>{selectedJob.status}</span></div>
              <div><strong>Rounds:</strong> {selectedJob.current_round}/{selectedJob.training_rounds}</div>
              <div><strong>Clients:</strong> {selectedJob.min_clients}</div>
              <div><strong>Privacy Budget:</strong> ε = {selectedJob.privacy_budget}</div>
              <div><strong>Epsilon Spent:</strong> {selectedJob.epsilon_spent?.toFixed(4) ?? '—'}</div>
              <div><strong>Noise:</strong> σ = {selectedJob.noise_multiplier}</div>
              <div><strong>Accuracy:</strong> {selectedJob.final_accuracy ? `${(selectedJob.final_accuracy * 100).toFixed(2)}%` : '—'}</div>
            </div>
            {jobMetrics.length > 0 && (
              <div className="chart-container">
                <Line data={{
                  labels: jobMetrics.map(m => `R${m.round_number}`),
                  datasets: [
                    { label: 'Train Loss', data: jobMetrics.map(m => m.train_loss), borderColor: '#6366f1', tension: 0.4 },
                    { label: 'Accuracy %', data: jobMetrics.map(m => m.eval_accuracy ? m.eval_accuracy * 100 : null), borderColor: '#10b981', tension: 0.4 },
                  ],
                }} options={chartOpts} />
              </div>
            )}
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setSelectedJob(null)}>Close</button>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Model</th>
                <th>Rounds</th>
                <th>Clients</th>
                <th>Status</th>
                <th>Accuracy</th>
                <th>ε Spent</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map(j => (
                <tr key={j.id}>
                  <td style={{ fontWeight: 600, cursor: 'pointer', color: 'var(--accent-indigo)' }} onClick={() => viewMetrics(j)}>{j.name}</td>
                  <td>{j.model_type}</td>
                  <td>{j.current_round}/{j.training_rounds}</td>
                  <td>{j.min_clients}</td>
                  <td><span className={`badge ${j.status}`}>{j.status}</span></td>
                  <td>{j.final_accuracy ? `${(j.final_accuracy * 100).toFixed(1)}%` : '—'}</td>
                  <td>{j.epsilon_spent?.toFixed(4) ?? '—'}</td>
                  <td>
                    {j.status === 'pending' && (
                      <button className="btn btn-primary btn-sm" onClick={() => startJob(j.id)}>
                        {Icons.play} Start
                      </button>
                    )}
                    <button className="btn btn-secondary btn-sm" style={{ marginLeft: '8px' }} onClick={() => viewMetrics(j)}>
                      View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

/* ── Create Job Modal ──────────────────────────────────── */
function CreateJobModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [form, setForm] = useState({
    name: '', model_type: 'cnn_cifar10', privacy_budget: 10,
    noise_multiplier: 1.1, max_grad_norm: 1.0,
    training_rounds: 5, min_clients: 3, fraction_fit: 1.0,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await apiFetch('/api/jobs/create', { method: 'POST', body: form });
      onCreated();
    } catch (err: any) {
      setError(err.message);
    }
    setLoading(false);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <h3>Create Training Job</h3>
        {error && <div className="error-msg">{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Job Name</label>
            <input className="form-input" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="e.g. Cancer Prediction Model v1" required />
          </div>
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Model Type</label>
              <select className="form-input" value={form.model_type} onChange={e => setForm({ ...form, model_type: e.target.value })}>
                <option value="cnn_cifar10">CNN (CIFAR-10)</option>
                <option value="resnet18">ResNet-18</option>
                <option value="custom">Custom</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Training Rounds</label>
              <input className="form-input" type="number" min="1" max="100" value={form.training_rounds} onChange={e => setForm({ ...form, training_rounds: +e.target.value })} />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Min Clients</label>
              <input className="form-input" type="number" min="1" value={form.min_clients} onChange={e => setForm({ ...form, min_clients: +e.target.value })} />
            </div>
            <div className="form-group">
              <label className="form-label">Fraction Fit</label>
              <input className="form-input" type="number" step="0.1" min="0.1" max="1" value={form.fraction_fit} onChange={e => setForm({ ...form, fraction_fit: +e.target.value })} />
            </div>
          </div>
          <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '16px', marginTop: '8px' }}>
            <div className="nav-section-title" style={{ marginBottom: '12px' }}>PRIVACY SETTINGS</div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Privacy Budget (ε)</label>
              <input className="form-input" type="number" step="0.5" min="0.1" value={form.privacy_budget} onChange={e => setForm({ ...form, privacy_budget: +e.target.value })} />
            </div>
            <div className="form-group">
              <label className="form-label">Noise Multiplier (σ)</label>
              <input className="form-input" type="number" step="0.1" min="0.1" value={form.noise_multiplier} onChange={e => setForm({ ...form, noise_multiplier: +e.target.value })} />
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">Max Gradient Norm</label>
            <input className="form-input" type="number" step="0.1" min="0.1" value={form.max_grad_norm} onChange={e => setForm({ ...form, max_grad_norm: +e.target.value })} />
          </div>
          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Creating...' : 'Create Job'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════
   ORGANIZATIONS PAGE
   ════════════════════════════════════════════════════════════════ */
function OrganizationsPage() {
  const [orgs, setOrgs] = useState<Org[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: '', description: '' });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => { loadOrgs(); }, []);

  const loadOrgs = async () => {
    try {
      const data = await apiFetch('/api/organizations/');
      setOrgs(data);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await apiFetch('/api/organizations/register', { method: 'POST', body: form });
      setShowCreate(false);
      setForm({ name: '', description: '' });
      loadOrgs();
    } catch (err: any) { setError(err.message); }
  };

  if (loading) return <div className="loading">Loading organizations...</div>;

  return (
    <>
      <div className="page-header">
        <h2>Organizations</h2>
        <p>Manage participating hospital nodes and data providers</p>
      </div>

      <div style={{ marginBottom: '24px' }}>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
          {Icons.plus} Register Organization
        </button>
      </div>

      {showCreate && (
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>Register Organization</h3>
            {error && <div className="error-msg">{error}</div>}
            <form onSubmit={handleCreate}>
              <div className="form-group">
                <label className="form-label">Organization Name</label>
                <input className="form-input" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="e.g. City General Hospital" required />
              </div>
              <div className="form-group">
                <label className="form-label">Description</label>
                <input className="form-input" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} placeholder="Brief description" />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Register</button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="card">
        {orgs.length === 0 ? (
          <div className="empty-state">
            <h3>No organizations</h3>
            <p>Register your first hospital node or organization</p>
          </div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead><tr><th>Name</th><th>Description</th><th>Status</th><th>Registered</th></tr></thead>
              <tbody>
                {orgs.map(o => (
                  <tr key={o.id}>
                    <td style={{ fontWeight: 600 }}>{o.name}</td>
                    <td style={{ color: 'var(--text-secondary)' }}>{o.description || '—'}</td>
                    <td><span className={`badge ${o.is_active ? 'completed' : 'failed'}`}>{o.is_active ? 'Active' : 'Inactive'}</span></td>
                    <td>{new Date(o.registered_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}

/* ════════════════════════════════════════════════════════════════
   DATASETS PAGE
   ════════════════════════════════════════════════════════════════ */
function DatasetsPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [orgs, setOrgs] = useState<Org[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: '', org_id: '', description: '', num_samples: 0, sensitivity_level: 'high' });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const [d, o] = await Promise.all([apiFetch('/api/datasets/'), apiFetch('/api/organizations/')]);
      setDatasets(d);
      setOrgs(o);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await apiFetch('/api/datasets/register', { method: 'POST', body: { ...form, num_samples: +form.num_samples } });
      setShowCreate(false);
      loadData();
    } catch (err: any) { setError(err.message); }
  };

  if (loading) return <div className="loading">Loading datasets...</div>;

  return (
    <>
      <div className="page-header">
        <h2>Datasets</h2>
        <p>Register dataset metadata from participating organizations</p>
      </div>

      <div style={{ marginBottom: '24px' }}>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
          {Icons.plus} Register Dataset
        </button>
      </div>

      {showCreate && (
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>Register Dataset</h3>
            {error && <div className="error-msg">{error}</div>}
            <form onSubmit={handleCreate}>
              <div className="form-group">
                <label className="form-label">Dataset Name</label>
                <input className="form-input" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="e.g. Chest X-Ray Images" required />
              </div>
              <div className="form-group">
                <label className="form-label">Organization</label>
                <select className="form-input" value={form.org_id} onChange={e => setForm({ ...form, org_id: e.target.value })} required>
                  <option value="">Select organization</option>
                  {orgs.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}
                </select>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Number of Samples</label>
                  <input className="form-input" type="number" value={form.num_samples} onChange={e => setForm({ ...form, num_samples: +e.target.value })} />
                </div>
                <div className="form-group">
                  <label className="form-label">Sensitivity Level</label>
                  <select className="form-input" value={form.sensitivity_level} onChange={e => setForm({ ...form, sensitivity_level: e.target.value })}>
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">Description</label>
                <input className="form-input" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} placeholder="Brief description" />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Register Dataset</button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="card">
        {datasets.length === 0 ? (
          <div className="empty-state"><h3>No datasets</h3><p>Register dataset metadata from organizations</p></div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead><tr><th>Name</th><th>Samples</th><th>Sensitivity</th><th>Created</th></tr></thead>
              <tbody>
                {datasets.map(d => (
                  <tr key={d.id}>
                    <td style={{ fontWeight: 600 }}>{d.name}</td>
                    <td>{d.num_samples?.toLocaleString() ?? '—'}</td>
                    <td><span className={`badge ${d.sensitivity_level}`}>{d.sensitivity_level}</span></td>
                    <td>{new Date(d.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}

/* ════════════════════════════════════════════════════════════════
   MODELS PAGE
   ════════════════════════════════════════════════════════════════ */
function ModelsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch('/api/jobs/?status=completed').then(setJobs).catch(console.error).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Loading models...</div>;

  return (
    <>
      <div className="page-header">
        <h2>Trained Models</h2>
        <p>View and download completed federated learning models</p>
      </div>

      <div className="card">
        {jobs.length === 0 ? (
          <div className="empty-state"><h3>No models yet</h3><p>Complete a training job to see models here</p></div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead><tr><th>Model Name</th><th>Type</th><th>Rounds</th><th>Accuracy</th><th>Loss</th><th>Privacy (ε)</th><th>Completed</th></tr></thead>
              <tbody>
                {jobs.map(j => (
                  <tr key={j.id}>
                    <td style={{ fontWeight: 600 }}>{j.name}</td>
                    <td>{j.model_type}</td>
                    <td>{j.training_rounds}</td>
                    <td style={{ color: 'var(--accent-emerald)', fontWeight: 600 }}>{j.final_accuracy ? `${(j.final_accuracy * 100).toFixed(2)}%` : '—'}</td>
                    <td>{j.final_loss?.toFixed(4) ?? '—'}</td>
                    <td>{j.epsilon_spent?.toFixed(4) ?? '—'}</td>
                    <td>{j.completed_at ? new Date(j.completed_at).toLocaleDateString() : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}

/* ════════════════════════════════════════════════════════════════
   PRIVACY PAGE
   ════════════════════════════════════════════════════════════════ */
function PrivacyPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch('/api/jobs/').then(setJobs).catch(console.error).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Loading privacy data...</div>;

  const completedJobs = jobs.filter(j => j.status === 'completed' || j.status === 'running');

  const epsilonChart = {
    labels: completedJobs.map(j => j.name.substring(0, 20)),
    datasets: [{
      label: 'Epsilon Spent',
      data: completedJobs.map(j => j.epsilon_spent || 0),
      backgroundColor: completedJobs.map(j => {
        const ratio = (j.epsilon_spent || 0) / j.privacy_budget;
        if (ratio < 0.5) return 'rgba(16, 185, 129, 0.8)';
        if (ratio < 0.8) return 'rgba(245, 158, 11, 0.8)';
        return 'rgba(244, 63, 94, 0.8)';
      }),
      borderRadius: 8,
    }],
  };

  return (
    <>
      <div className="page-header">
        <h2>Privacy Budget Tracking</h2>
        <p>Monitor differential privacy epsilon consumption across training jobs</p>
      </div>

      <div className="stats-grid">
        {completedJobs.map(j => {
          const ratio = (j.epsilon_spent || 0) / j.privacy_budget;
          const level = ratio < 0.5 ? 'safe' : ratio < 0.8 ? 'warning' : 'danger';
          return (
            <div key={j.id} className="card">
              <div style={{ fontWeight: 600, fontSize: '15px', marginBottom: '12px' }}>{j.name}</div>
              <div className="privacy-meter">
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                  <span>ε spent: <strong>{j.epsilon_spent?.toFixed(4) ?? '0'}</strong></span>
                  <span>Budget: <strong>{j.privacy_budget}</strong></span>
                </div>
                <div className="privacy-bar">
                  <div className={`privacy-bar-fill ${level}`} style={{ width: `${Math.min(ratio * 100, 100)}%` }} />
                </div>
                <div className="privacy-labels">
                  <span>0</span>
                  <span>{(ratio * 100).toFixed(1)}% used</span>
                  <span>{j.privacy_budget}</span>
                </div>
              </div>
              <div style={{ marginTop: '12px', fontSize: '12px', color: 'var(--text-muted)' }}>
                Noise σ = {j.noise_multiplier} • Grad norm = {j.max_grad_norm}
              </div>
            </div>
          );
        })}
      </div>

      {completedJobs.length > 0 && (
        <div className="card">
          <div className="card-header"><span className="card-title">Epsilon Consumption by Job</span></div>
          <div className="chart-container">
            <Bar data={epsilonChart} options={{
              responsive: true,
              plugins: { legend: { display: false } },
              scales: {
                x: { ticks: { color: '#6b7280' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { ticks: { color: '#6b7280' }, grid: { color: 'rgba(255,255,255,0.05)' }, title: { display: true, text: 'Epsilon (ε)', color: '#9ca3af' } },
              },
            }} />
          </div>
        </div>
      )}

      <div className="card" style={{ marginTop: '24px' }}>
        <div className="card-header"><span className="card-title">About Differential Privacy</span></div>
        <div style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.8 }}>
          <p><strong>Epsilon (ε)</strong> measures the privacy loss. Lower ε means stronger privacy but may reduce model accuracy.</p>
          <p style={{ marginTop: '12px' }}><strong>Noise Multiplier (σ)</strong> controls the amount of Gaussian noise added to gradients during training.</p>
          <p style={{ marginTop: '12px' }}><strong>Formula:</strong> Noisy Gradient = Gradient + 𝒩(0, σ²·C²), where C is the max gradient norm.</p>
          <p style={{ marginTop: '12px' }}>This protects against <strong>membership inference</strong> and <strong>model inversion</strong> attacks.</p>
        </div>
      </div>
    </>
  );
}

/* ════════════════════════════════════════════════════════════════
   AUDIT PAGE
   ════════════════════════════════════════════════════════════════ */
function AuditPage() {
  const [logs, setLogs] = useState<AuditEntry[]>([]);
  const [filter, setFilter] = useState({ action: '', actor: '' });
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadLogs(); }, []);

  const loadLogs = async () => {
    try {
      let url = '/api/audit-logs/?limit=200';
      if (filter.action) url += `&action=${filter.action}`;
      if (filter.actor) url += `&actor=${filter.actor}`;
      const data = await apiFetch(url);
      setLogs(data);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  if (loading) return <div className="loading">Loading audit logs...</div>;

  return (
    <>
      <div className="page-header">
        <h2>Audit Logs</h2>
        <p>Complete activity trail for compliance and security monitoring</p>
      </div>

      <div style={{ display: 'flex', gap: '12px', marginBottom: '24px' }}>
        <input className="form-input" style={{ maxWidth: '200px' }} placeholder="Filter by actor" value={filter.actor} onChange={e => setFilter({ ...filter, actor: e.target.value })} />
        <select className="form-input" style={{ maxWidth: '200px' }} value={filter.action} onChange={e => setFilter({ ...filter, action: e.target.value })}>
          <option value="">All Actions</option>
          <option value="user_registered">User Registered</option>
          <option value="user_login">User Login</option>
          <option value="organization_registered">Org Registered</option>
          <option value="dataset_registered">Dataset Registered</option>
          <option value="training_job_created">Job Created</option>
          <option value="training_job_started">Job Started</option>
        </select>
        <button className="btn btn-primary btn-sm" onClick={loadLogs}>Apply</button>
      </div>

      <div className="card">
        {logs.length === 0 ? (
          <div className="empty-state"><h3>No audit logs</h3><p>Activity will appear here as actions are performed</p></div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead><tr><th>Timestamp</th><th>Actor</th><th>Role</th><th>Action</th><th>Resource</th><th>Details</th></tr></thead>
              <tbody>
                {logs.map(l => (
                  <tr key={l.id}>
                    <td style={{ fontSize: '12px', whiteSpace: 'nowrap' }}>{new Date(l.timestamp).toLocaleString()}</td>
                    <td style={{ fontWeight: 600 }}>{l.actor}</td>
                    <td><span className="badge pending" style={{ fontSize: '10px' }}>{l.actor_role || '—'}</span></td>
                    <td>{l.action.replace(/_/g, ' ')}</td>
                    <td style={{ color: 'var(--text-muted)', fontSize: '12px' }}>{l.resource_type || '—'}</td>
                    <td style={{ color: 'var(--text-muted)', fontSize: '12px', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {l.details ? JSON.stringify(l.details) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
