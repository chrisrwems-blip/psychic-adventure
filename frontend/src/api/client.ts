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
export const getAnnotatedPdfDownloadUrl = (id: number) => `/api/submittals/${id}/annotated-pdf?download=true`;

// --- Reviews ---
export const runReview = (submittalId: number) => api.post(`/reviews/${submittalId}/run`);
export const runBatchReview = (submittalIds: number[]) =>
  api.post('/reviews/batch', { submittal_ids: submittalIds });
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

// --- Reports ---
export const getReportUrl = (submittalId: number) => `/api/reviews/${submittalId}/report`;

// --- Revision Comparison ---
export const compareRevision = (submittalId: number, formData: FormData) =>
  api.post(`/reviews/${submittalId}/compare-revision`, formData, { headers: { 'Content-Type': 'multipart/form-data' } });

// --- Spec Validation ---
export const validateSpec = (submittalId: number, formData: FormData) =>
  api.post(`/reviews/${submittalId}/validate-spec`, formData, { headers: { 'Content-Type': 'multipart/form-data' } });

// --- Multi-Submittal Cross-Reference ---
export const crossReferenceProject = (projectId: number) =>
  api.post(`/reviews/project/${projectId}/cross-reference`);

// --- Feedback ---
export const submitFeedback = (submittalId: number, data: { finding_type: string; action: string; notes?: string }) =>
  api.post(`/feedback/${submittalId}`, data);
export const getFeedbackStats = () => api.get('/feedback/stats');

// --- NEC Commentary ---
export const getNecCommentary = (codeRef: string) => api.get(`/reviews/nec-commentary/${encodeURIComponent(codeRef)}`);

// --- Vision ---
export const startVisionAnalysis = (submittalId: number) => api.post(`/reviews/${submittalId}/vision-analyze`);
export const getVisionStatus = (submittalId: number) => api.get(`/reviews/${submittalId}/vision-status`);
export const checkVisionAvailable = () => api.get('/reviews/vision-available');

// --- Settings ---
export const getEmailSettings = () => api.get('/settings/email');
export const saveEmailSettings = (data: { email: string; password: string; host: string; port: number; display_name?: string }) =>
  api.post('/settings/email/save', data);
export const deleteEmailSettings = () => api.delete('/settings/email');
export const detectSmtpProvider = (email: string) =>
  api.post('/settings/email/detect', { email });
export const testEmailConnection = (data: { email: string; password: string; host: string; port: number }) =>
  api.post('/settings/email/test', data);
export const sendGeneratedEmail = (emailId: number, data: { to: string; cc?: string }) =>
  api.post(`/emails/${emailId}/send`, data);

// --- Dashboard ---
export const getDashboard = () => api.get('/dashboard');

// --- RFIs ---
export const createRFI = (submittalId: number, data?: { email_type?: string }) =>
  api.post(`/rfis/${submittalId}/create`, data || {});
export const getRFIs = (submittalId: number) => api.get(`/rfis/${submittalId}`);
export const getAllRFIs = (params?: { status?: string }) => api.get('/rfis/all', { params });
export const updateRFIStatus = (rfiId: number, data: { status: string }) =>
  api.patch(`/rfis/${rfiId}/status`, data);

// --- Submittal Register ---
export const getRegister = (projectId: number) => api.get(`/register/${projectId}`);
export const addRegisterItem = (projectId: number, data: any) =>
  api.post(`/register/${projectId}`, data);
export const updateRegisterItem = (itemId: number, data: any) =>
  api.patch(`/register/${itemId}`, data);
export const getRegisterSummary = (projectId: number) => api.get(`/register/${projectId}/summary`);
