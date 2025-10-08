// SevenTech Plan Types
export interface PlanMetadata {
  plan_id: string;
  name: string;
  description: string;
  url?: string;
  required_params: string[];
  tags: string[];
  expected_output?: string;
  created_at?: string;
  updated_at?: string;
}

export interface PlanStep {
  sequence_id: number;
  action: string;
  params: Record<string, any>;
  description: string;
  original_action?: string;
  original_params?: Record<string, any>;
}

export interface Plan {
  metadata: PlanMetadata;
  steps: PlanStep[];
}

// Execution Types
export interface Artifact {
  artifact_id: string;
  type: 'text' | 'image' | 'pdf' | 'file' | 'json' | 'screenshot';
  name: string;
  content?: string;
  file_path?: string;
  metadata: Record<string, any>;
}

export interface ExecutionResult {
  execution_id: string;
  plan_id: string;
  status: 'success' | 'partial_success' | 'failure' | 'timeout' | 'error';
  artifacts: Artifact[];
  steps_completed: number;
  total_steps: number;
  error_message?: string;
  execution_time_ms?: number;
  metadata: Record<string, any>;
}

// Mapping Types
export interface InputRequest {
  field_name: string;
  field_label: string;
  prompt: string;
  placeholder?: string;
}

export interface CollectedParameter {
  name: string;
  label: string;
  value: string;
}

export interface MappingSession {
  session_id: string;
  objective: string;
  status: 'started' | 'running' | 'waiting_for_input' | 'completed' | 'failed' | 'cancelled';
  steps_completed: number;
  collected_parameters: CollectedParameter[];
  current_input_request?: InputRequest;
}

export interface StartMappingRequest {
  objective: string;
  starting_url?: string;
  tags?: string[];
  plan_name?: string;
}

export interface ProvideInputRequest {
  value: string;
}

export interface ExecutePlanRequest {
  [key: string]: any; // Dynamic parameters based on plan requirements
}