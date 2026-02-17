/**
 * API client for Queryus backend
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface ApiError {
  detail: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface User {
  id: string;
  email: string;
  full_name?: string;
  avatar_url?: string;
  role: string;
  created_at: string;
}

export interface Connection {
  id: string;
  name: string;
  type: string;
  is_read_only: boolean;
  created_at: string;
  last_used?: string;
}

export interface CreateConnectionRequest {
  name: string;
  type: string;
  credentials: Record<string, any>;
  is_read_only: boolean;
}

export interface ChatMessageRequest {
  conversation_id: string;
  message: {
    id: string;
    role: string;
    content: string;
    timestamp: string;
  };
  connection_id: string;
  mode: string;
  execute_sql: boolean;
  stream: boolean;
}

class ApiClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
    // Load token from localStorage
    this.token = localStorage.getItem('access_token');
  }

  setToken(token: string) {
    this.token = token;
    localStorage.setItem('access_token', token);
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem('access_token');
  }

  private getHeaders(includeAuth: boolean = true): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (includeAuth && this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    return headers;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        ...this.getHeaders(),
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        detail: `HTTP ${response.status}: ${response.statusText}`,
      }));
      throw new Error(error.detail || 'An error occurred');
    }

    return response.json();
  }

  // Auth endpoints
  async register(data: RegisterRequest): Promise<User> {
    return this.request<User>('/api/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async login(data: LoginRequest): Promise<TokenResponse> {
    const response = await this.request<TokenResponse>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    this.setToken(response.access_token);
    return response;
  }

  async getCurrentUser(): Promise<User> {
    return this.request<User>('/api/v1/auth/me');
  }

  // Connection endpoints
  async getConnections(): Promise<Connection[]> {
    return this.request<Connection[]>('/api/v1/connections');
  }

  async createConnection(data: CreateConnectionRequest): Promise<Connection> {
    return this.request<Connection>('/api/v1/connections', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteConnection(id: string): Promise<void> {
    return this.request<void>(`/api/v1/connections/${id}`, {
      method: 'DELETE',
    });
  }

  // Chat endpoints
  async sendMessage(data: ChatMessageRequest): Promise<any> {
    return this.request<any>('/api/v1/chat/message', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  createStreamingConnection(data: ChatMessageRequest): EventSource {
    const url = `${this.baseUrl}/api/v1/chat/message/stream`;
    
    // EventSource doesn't support custom headers or POST, so we use fetch with SSE
    // This is a workaround - in production, consider using a library like eventsource-parser
    
    return new EventSource(url, {
      // Note: EventSource doesn't support auth headers directly
      // For production, you may need to use query params or a different approach
    });
  }

  // Conversations
  async getConversations(): Promise<any[]> {
    return this.request<any[]>('/api/v1/chat/conversations');
  }

  async getConversation(id: string): Promise<any> {
    return this.request<any>(`/api/v1/chat/conversations/${id}`);
  }

  // Schema endpoints
  async getSchemaTree(connectionId: string): Promise<any> {
    return this.request<any>(`/api/v1/schema/${connectionId}/tree`);
  }

  async refreshSchema(connectionId: string): Promise<void> {
    return this.request<void>(`/api/v1/schema/${connectionId}/refresh`, {
      method: 'POST',
    });
  }

  async getSampleData(
    connectionId: string,
    params: { table: string; schema_name?: string; limit?: number }
  ): Promise<{ columns: { name: string; type: string }[]; rows: unknown[][]; total_rows: number }> {
    return this.request<{ columns: { name: string; type: string }[]; rows: unknown[][]; total_rows: number }>(
      `/api/v1/schema/${connectionId}/sample`,
      {
        method: 'POST',
        body: JSON.stringify({
          table: params.table,
          schema_name: params.schema_name ?? null,
          limit: params.limit ?? 10,
        }),
      }
    );
  }
}

export const apiClient = new ApiClient(API_BASE_URL);
