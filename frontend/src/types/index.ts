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

export interface DashboardStats {
  total_projects: number;
  total_submittals: number;
  pending_review: number;
  open_comments: number;
  critical_issues: number;
  submittals_by_status: Record<string, number>;
  recent_submittals: Array<{ id: number; title: string; equipment_type: string; status: string }>;
}
