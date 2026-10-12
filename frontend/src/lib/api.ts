export type JobStatus = {
  job_id: string; status: string; event_name: string; issuer_name: string; issue_date: string;
  certificate_title: string; total_recipients: number; successful_count: number; failed_count: number;
  pending_count: number; processing_count: number; progress_percentage: number; created_at: string;
  started_at?: string | null; completed_at?: string | null; zip_download_url?: string | null;
};
export type JobAccepted = { job_id: string; status: string; total_recipients: number; created_at: string; status_url: string; message?: string };
export type CertificateRecord = {
  id: string; job_id: string; recipient_name: string; recipient_email?: string | null;
  certificate_id?: string | null; status: string; error_code?: string | null; error_message?: string | null;
  created_at: string; completed_at?: string | null; download_url?: string | null;
};
export type Stats = {
  application?: { name?: string; version?: string; environment?: string; uptime_seconds?: number; timestamp?: string };
  resources?: Record<string, number | string>;
  http?: { total_requests?: number; error_requests?: number; error_rate_percentage?: number };
  jobs?: { submitted_total?: number; completed_total?: number; by_status?: Record<string, number>; stale_recoveries_total?: number };
  certificates?: { generated_success?: number; generated_failed?: number; avg_render_latency_ms?: number };
  storage?: { provider?: string; cloud_configured?: boolean; stored_pdf_count?: number; bytes_used?: number; human_readable_size?: string };
};
export type UserProfile = {
  id: string;
  email: string;
  full_name: string;
  avatar_url?: string | null;
  created_at: string;
};
export type AuthConfig = {
  google_client_id?: string | null;
  storage_provider: string;
  cloud_storage_configured: boolean;
  cloud_storage_provider: string;
};
export type AuthResponse = {
  access_token: string;
  token_type: string;
  user: UserProfile;
};

const apiBase = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
const apiKey = import.meta.env.VITE_API_KEY || '';
export const API_ROOT = `${apiBase}/api/v1`;
export const POLL_MS = Math.max(2000, Number(import.meta.env.VITE_POLL_INTERVAL_MS || 4000));

export const TOKEN_STORAGE_KEY = 'certflow.auth_token.v1';
export const USER_STORAGE_KEY = 'certflow.auth_user.v1';

export function getStoredToken(): string {
  try { return localStorage.getItem(TOKEN_STORAGE_KEY) || ''; } catch { return ''; }
}
export function setStoredToken(token: string): void {
  try { localStorage.setItem(TOKEN_STORAGE_KEY, token); } catch { /* ignore */ }
}
export function removeStoredToken(): void {
  try { localStorage.removeItem(TOKEN_STORAGE_KEY); } catch { /* ignore */ }
}
export function getStoredUser(): UserProfile | null {
  try { const v = localStorage.getItem(USER_STORAGE_KEY); return v ? JSON.parse(v) : null; } catch { return null; }
}
export function setStoredUser(user: UserProfile | null): void {
  try {
    if (user) localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
    else localStorage.removeItem(USER_STORAGE_KEY);
  } catch { /* ignore */ }
}
export function removeStoredUser(): void {
  try { localStorage.removeItem(USER_STORAGE_KEY); } catch { /* ignore */ }
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status = 0) { super(message); this.name = 'ApiError'; this.status = status; }
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (apiKey) headers.set('X-API-Key', apiKey);
  const token = getStoredToken();
  if (token && !headers.has('Authorization')) headers.set('Authorization', `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');

  let response: Response;
  try { response = await fetch(`${API_ROOT}${path}`, { ...init, headers }); }
  catch { throw new ApiError('Cannot reach the API. Check that your backend is running and the API URL is correct.'); }
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try { const body = await response.json(); message = typeof body.detail === 'string' ? body.detail : body.message || message; }
    catch { /* response body may not be JSON */ }
    throw new ApiError(message, response.status);
  }
  return response.json() as Promise<T>;
}

export const getHealth = () => request<{status:string;db_connected?:boolean;storage_accessible?:boolean;version?:string;environment?:string}>('/health');
export const getStats = () => request<Stats>('/observability/stats');
export const getJob = (id: string) => request<JobStatus>(`/jobs/${encodeURIComponent(id)}`);
export const listServerJobs = (limit = 50) => request<JobStatus[]>(`/jobs?limit=${limit}`);
export const getCertificates = (id: string, status = '', offset = 0, limit = 100) => {
  const q = new URLSearchParams({ offset: String(offset), limit: String(limit) });
  if (status) q.set('status_filter', status);
  return request<CertificateRecord[]>(`/jobs/${encodeURIComponent(id)}/certificates?${q}`);
};

// Auth & Cloud Storage endpoints
export const getAuthConfig = () => request<AuthConfig>('/auth/config');
export const loginWithGoogle = (credential: string) => request<AuthResponse>('/auth/google', { method: 'POST', body: JSON.stringify({ credential }) });
export const loginWithDevGoogle = (name?: string, email?: string) => request<AuthResponse>('/auth/google', { method: 'POST', body: JSON.stringify({ demo: true, name, email }) });
export const getMe = () => request<UserProfile>('/auth/me');
export const logoutUser = () => request<{status:string}>('/auth/logout', { method: 'POST' });

export async function createUploadJob(input: {file: File; event_name: string; issuer_name: string; issue_date: string; certificate_title: string}): Promise<JobAccepted> {
  const body = new FormData(); body.append('file', input.file); body.append('event_name', input.event_name);
  body.append('issuer_name', input.issuer_name); body.append('issue_date', input.issue_date); body.append('certificate_title', input.certificate_title);
  return request<JobAccepted>('/jobs/upload', { method: 'POST', body });
}
export async function downloadFile(path: string, fallbackFilename: string): Promise<void> {
  const headers = new Headers();
  if (apiKey) headers.set('X-API-Key', apiKey);
  const token = getStoredToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const targetUrl = path.startsWith('http') ? path : `${apiBase}${path}`;
  let response: Response;
  try {
    response = await fetch(targetUrl, { headers });
  } catch {
    throw new ApiError('Download failed: the API is unreachable.');
  }

  if (!response.ok) {
    let errorMsg = `Download failed (${response.status})`;
    try {
      const errJson = await response.json();
      errorMsg = errJson.detail || errJson.message || errorMsg;
    } catch {
      // ignore
    }
    throw new ApiError(errorMsg, response.status);
  }

  // 1. Resolve clean filename from Content-Disposition header if available
  let resolvedFilename = fallbackFilename;
  const disposition = response.headers.get('content-disposition');
  if (disposition) {
    const filenameMatch = disposition.match(/filename\*?=(?:UTF-8'')?["']?([^"';\n]+)["']?/i);
    if (filenameMatch && filenameMatch[1]) {
      resolvedFilename = decodeURIComponent(filenameMatch[1].trim());
    }
  }

  // 2. Guarantee correct file extension
  if (path.includes('zip') && !resolvedFilename.toLowerCase().endsWith('.zip')) {
    resolvedFilename = `${resolvedFilename}.zip`;
  } else if ((path.includes('certificate') || path.includes('.pdf')) && !resolvedFilename.toLowerCase().endsWith('.pdf')) {
    resolvedFilename = `${resolvedFilename}.pdf`;
  } else if (path.includes('template') && !resolvedFilename.toLowerCase().endsWith('.xlsx') && !resolvedFilename.toLowerCase().endsWith('.csv')) {
    resolvedFilename = `${resolvedFilename}.xlsx`;
  }

  // 3. Guarantee explicit MIME type so OS file manager associates the file
  const blob = await response.blob();
  const mimeType = resolvedFilename.endsWith('.zip')
    ? 'application/zip'
    : resolvedFilename.endsWith('.pdf')
    ? 'application/pdf'
    : resolvedFilename.endsWith('.xlsx')
    ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    : blob.type || 'application/octet-stream';

  const typedBlob = new Blob([blob], { type: mimeType });
  const objectUrl = URL.createObjectURL(typedBlob);

  // 4. Create anchor and trigger browser download
  const link = document.createElement('a');
  link.style.display = 'none';
  link.href = objectUrl;
  link.download = resolvedFilename;
  link.setAttribute('download', resolvedFilename);
  document.body.appendChild(link);
  link.click();

  // 5. CRITICAL: Do NOT revokeObjectURL synchronously!
  // Chromium requires objectUrl to remain active while the browser file manager saves the file.
  setTimeout(() => {
    try {
      document.body.removeChild(link);
      URL.revokeObjectURL(objectUrl);
    } catch {
      // ignore
    }
  }, 60000);
}

export const downloadTemplate = () => downloadFile(`${API_ROOT}/jobs/upload/template`, 'recipients.xlsx');
export const downloadZip = (jobId: string) => downloadFile(`${API_ROOT}/jobs/${encodeURIComponent(jobId)}/download-zip`, `certificates_${jobId}.zip`);
export const downloadCertificate = (certificateId: string) => downloadFile(`${API_ROOT}/certificates/${encodeURIComponent(certificateId)}/download?as_attachment=true`, `${certificateId}.pdf`);

export type AssetFileInfo = {
  exists: boolean;
  filename?: string | null;
  preview_url?: string | null;
  updated_at?: string | null;
  size_bytes?: number;
};

export type TemplateAssetsStatus = {
  signature: AssetFileInfo;
  background: AssetFileInfo;
  active_template_mode: string;
  sample_preview_url: string;
};

export const getTemplateAssetsStatus = () => request<TemplateAssetsStatus>('/templates/status');

export async function uploadSignatureFile(file: File): Promise<{
  status: string;
  message: string;
  preview_url: string;
  dimensions: { width: number; height: number };
  filename: string;
}> {
  const body = new FormData();
  body.append('file', file);
  return request('/templates/signature', { method: 'POST', body });
}

export const resetSignature = () => request<{ status: string; message: string }>('/templates/signature', { method: 'DELETE' });

export async function uploadBackgroundTemplateFile(file: File): Promise<{
  status: string;
  message: string;
  preview_url: string;
  dimensions: { width: number; height: number };
  filename: string;
}> {
  const body = new FormData();
  body.append('file', file);
  return request('/templates/background', { method: 'POST', body });
}

export const resetBackgroundTemplate = () => request<{ status: string; message: string }>('/templates/background', { method: 'DELETE' });

export type TemplateLayoutConfig = {
  template_mode: 'preprinted' | 'frame' | 'custom';
  render_issuer: boolean;
  render_title: boolean;
  render_title_line: boolean;
  render_subtitle: boolean;
  render_description: boolean;
  render_event: boolean;
  render_remarks: boolean;
  render_seal: boolean;
  render_recipient_underline: boolean;
  render_date: boolean;
  render_signature: boolean;
  render_signatory_line: boolean;
  render_signatory_title: boolean;
  render_verification_code: boolean;
  recipient_name_y: number;
  recipient_name_font_size: number;
  recipient_name_color: string;
  event_y: number;
  event_font_size: number;
  event_color: string;
  date_x: number;
  date_y: number;
  signature_x: number;
  signature_y: number;
  signature_width: number;
  signature_height: number;
  verification_code_y: number;
};

export const getTemplateLayoutConfig = () => request<TemplateLayoutConfig>('/templates/layout');

export const updateTemplateLayoutConfig = (config: TemplateLayoutConfig) =>
  request<TemplateLayoutConfig>('/templates/layout', {
    method: 'POST',
    body: JSON.stringify(config),
  });

export const applyLayoutPreset = (preset: 'preprinted' | 'frame') =>
  request<TemplateLayoutConfig>(`/templates/layout/preset/${preset}`, {
    method: 'POST',
  });

export const aiAnalyzeTemplateLayout = (apiKey?: string) =>
  request<{ status: string; message: string; layout: TemplateLayoutConfig }>('/templates/ai-analyze-layout', {
    method: 'POST',
    body: JSON.stringify({ api_key: apiKey || '' }),
  });

