export interface Project {
  id: number;
  name: string;
  description?: string;
  client?: string;
  location?: string;
  tier_level?: string;
  created_at: string;
  submittal_count: number;
}

export interface Submittal {
  id: number;
  project_id: number;
  title: string;
  submittal_number?: string;
  equipment_type: string;
  manufacturer?: string;
  model_number?: string;
  spec_section?: string;
  status: string;
  file_path: string;
  annotated_file_path?: string;
  file_size?: number;
  page_count?: number;
  submitted_by?: string;
  contractor?: string;
  created_at: string;
  reviewed_at?: string;
  comment_count: number;
  open_comments: number;
}

export interface ReviewComment {
  id: number;
  submittal_id: number;
  page_number?: number;
  x_position?: number;
  y_position?: number;
  comment_text: string;
  category?: string;
  severity: string;
  status: string;
  assigned_to?: string;
  reference_code?: string;
  resolution_notes?: string;
  created_at: string;
  resolved_at?: string;
}

export interface ReviewResult {
  id: number;
  submittal_id: number;
  check_name: string;
  check_category?: string;
  passed: number;  // 1=pass, 0=fail, -1=needs_review
  details?: string;
  reference_standard?: string;
}

export interface GeneratedEmail {
  id: number;
  submittal_id: number;
  email_type: string;
  subject: string;
  body: string;
  recipients?: string;
  sent: number;
  created_at: string;
}

export interface RFI {
  id: number;
  submittal_id: number;
  rfi_number: string;
  subject: string;
  description?: string;
  status: string;
  severity: string;
  due_date?: string;
  response?: string;
  created_at: string;
  updated_at?: string;
  submittal_title?: string;
  project_name?: string;
}

export interface RegisterItem {
  id: number;
  project_id: number;
  spec_section: string;
  description: string;
  status: string;
  priority: string;
  submittal_id?: number;
  submittal_title?: string;
  due_date?: string;
  notes?: string;
  created_at: string;
  updated_at?: string;
}

export interface DashboardStats {
  total_projects: number;
  total_submittals: number;
  pending_review: number;
  open_comments: number;
  critical_issues: number;
  major_issues?: number;
  reviewed?: number;
  approved?: number;
  resolved_comments?: number;
  total_rfis?: number;
  open_rfis?: number;
  awaiting_response?: number;
  register_total?: number;
  register_not_submitted?: number;
  submittals_by_status: Record<string, number>;
  comments_by_severity?: Record<string, number>;
  submittals_by_equipment_type?: Record<string, number>;
  recent_submittals: Array<{ id: number; title: string; equipment_type: string; status: string }>;
}
