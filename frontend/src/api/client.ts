import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
});

export default api;

// --- Projects ---
export const getProjects = () => api.get('/projects/');
export const createProject = (data: { name: string; description?: string; client?: string; location?: string; tier_level?: string }) =>
  api.post('/projects/', data);
export const getProject = (id: number) => api.get(`/projects/${id}`);
export const deleteProject = (id: number) => api.delete(`/projects/${id}`);

// --- Submittals ---
export const getSubmittals = (projectId?: number) =>
  api.get('/submittals/', { params: projectId ? { project_id: projectId } : {} });
export const getSubmittal = (id: number) => api.get(`/submittals/${id}`);
export const uploadSubmittal = (formData: FormData) =>
  api.post('/submittals/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
export const deleteSubmittal = (id: number) => api.delete(`/submittals/${id}`);
export const getSubmittalPdfUrl = (id: number) => `/api/submittals/${id}/pdf`;
export const annotateSubmittal = (id: number) => api.post(`/submittals/${id}/annotate`);
export const getAnnotatedPdfUrl = (id: number) => `/api/submittals/${id}/annotated-pdf`;

// --- Reviews ---
export const runReview = (submittalId: number) => api.post(`/reviews/${submittalId}/run`);
export const getReviewResults = (submittalId: number) => api.get(`/reviews/${submittalId}/results`);
export const getEquipmentTypes = () => api.get('/reviews/equipment-types');

// --- Comments ---
export const getComments = (submittalId: number, params?: { status?: string; severity?: string }) =>
  api.get(`/comments/submittal/${submittalId}`, { params });
export const getAllComments = (params?: { status?: string; severity?: string; project_id?: number }) =>
  api.get('/comments/all', { params });
export const addComment = (submittalId: number, data: { comment_text: string; severity?: string; page_number?: number; reference_code?: string }) =>
  api.post(`/comments/submittal/${submittalId}`, data);
export const updateComment = (commentId: number, data: { status?: string; resolution_notes?: string; severity?: string }) =>
  api.patch(`/comments/${commentId}`, data);
export const deleteComment = (commentId: number) => api.delete(`/comments/${commentId}`);

// --- Emails ---
export const generateEmail = (submittalId: number, data: { email_type: string; recipients?: string; additional_notes?: string }) =>
  api.post(`/emails/${submittalId}/generate`, data);
export const getEmails = (submittalId: number) => api.get(`/emails/submittal/${submittalId}`);
export const markEmailSent = (emailId: number) => api.patch(`/emails/${emailId}/mark-sent`);

// --- Dashboard ---
export const getDashboard = () => api.get('/dashboard');
