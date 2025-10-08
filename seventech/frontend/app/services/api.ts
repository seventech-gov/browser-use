import { API_BASE_URL } from '@/app/utils/config';
import {
  Plan,
  PlanMetadata,
  ExecutionResult,
  MappingSession,
  StartMappingRequest,
  ProvideInputRequest,
  ExecutePlanRequest
} from './types';

class ApiClient {
  private baseURL: string;

  constructor() {
    this.baseURL = API_BASE_URL;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error(`API Request failed: ${endpoint}`, error);
      throw error;
    }
  }

  // Authentication
  async authenticate(): Promise<{ status: string; message: string }> {
    return this.request('/api/v1/auth');
  }

  // Health check
  async getHealth(): Promise<{ service: string; version: string; status: string; features: Record<string, boolean> }> {
    return this.request('/');
  }

  // Interactive Mapping endpoints
  async startMapping(request: StartMappingRequest): Promise<{
    session_id: string;
    status: string;
    message: string;
    sse_url: string;
    status_url: string;
  }> {
    return this.request('/api/v1/mapping/start', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async getMappingSession(sessionId: string): Promise<MappingSession> {
    return this.request(`/api/v1/mapping/sessions/${sessionId}`);
  }

  async provideInput(sessionId: string, request: ProvideInputRequest): Promise<{
    status: string;
    message: string;
  }> {
    return this.request(`/api/v1/mapping/sessions/${sessionId}/input`, {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async cancelMapping(sessionId: string): Promise<{
    status: string;
    session_id: string;
  }> {
    return this.request(`/api/v1/mapping/sessions/${sessionId}/cancel`, {
      method: 'POST',
    });
  }

  async createPlanFromSession(sessionId: string, planName?: string): Promise<Plan> {
    const params = planName ? `?plan_name=${encodeURIComponent(planName)}` : '';
    const url = `/api/v1/mapping/sessions/${sessionId}/create-plan${params}`;
    return this.request(url, {
      method: 'POST',
    });
  }

  // Plan Management endpoints
  async getPlans(tags?: string[]): Promise<Plan[]> {
    const params = tags && tags.length > 0 ? `?tags=${tags.join(',')}` : '';
    return this.request(`/api/v1/plans${params}`);
  }

  async searchPlans(query: string): Promise<Plan[]> {
    return this.request(`/api/v1/plans/search?query=${encodeURIComponent(query)}`);
  }

  async getPlan(planId: string): Promise<Plan> {
    return this.request(`/api/v1/plans/${planId}`);
  }

  async deletePlan(planId: string): Promise<{
    status: string;
    plan_id: string;
  }> {
    return this.request(`/api/v1/plans/${planId}`, {
      method: 'DELETE',
    });
  }

  // Execution endpoints
  async executePlan(planId: string, params: ExecutePlanRequest): Promise<ExecutionResult> {
    return this.request(`/api/v1/execute/${planId}`, {
      method: 'POST',
      body: JSON.stringify(params),
    });
  }

  async getExecutions(planId?: string): Promise<ExecutionResult[]> {
    const params = planId ? `?plan_id=${planId}` : '';
    return this.request(`/api/v1/executions${params}`);
  }

  async getExecution(executionId: string): Promise<ExecutionResult> {
    return this.request(`/api/v1/executions/${executionId}`);
  }
}

export const apiClient = new ApiClient();

// Convenience functions for SevenTech API
export const mappingApi = {
  start: (request: StartMappingRequest) => apiClient.startMapping(request),
  getSession: (sessionId: string) => apiClient.getMappingSession(sessionId),
  provideInput: (sessionId: string, request: ProvideInputRequest) => 
    apiClient.provideInput(sessionId, request),
  cancel: (sessionId: string) => apiClient.cancelMapping(sessionId),
  createPlan: (sessionId: string, planName?: string) => 
    apiClient.createPlanFromSession(sessionId, planName),
};

export const plansApi = {
  getAll: (tags?: string[]) => apiClient.getPlans(tags),
  search: (query: string) => apiClient.searchPlans(query),
  getById: (planId: string) => apiClient.getPlan(planId),
  delete: (planId: string) => apiClient.deletePlan(planId),
};

export const executionApi = {
  execute: (planId: string, params: ExecutePlanRequest) => 
    apiClient.executePlan(planId, params),
  getAll: (planId?: string) => apiClient.getExecutions(planId),
  getById: (executionId: string) => apiClient.getExecution(executionId),
};

export const systemApi = {
  auth: () => apiClient.authenticate(),
  health: () => apiClient.getHealth(),
};