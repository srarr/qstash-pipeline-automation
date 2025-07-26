import { jest } from '@jest/globals';

// Mock environment for testing
const mockEnv = {
  URLS: {
    put: jest.fn().mockResolvedValue(undefined)
  }
};

// Import the worker (in a real setup, you'd import from the actual file)
const worker = {
  async fetch(request, env) {
    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 });
    }

    try {
      const { concept } = await request.json();
      
      if (!concept) {
        return new Response('Concept required', { status: 400 });
      }

      const queries = [
        `${concept} trading`,
        `${concept} pinescript`, 
        `${concept} pdf`
      ];

      const urls = [];
      
      for (const query of queries) {
        const mockUrls = [
          `https://example.com/search?q=${encodeURIComponent(query)}&result=1`,
          `https://docs.example.com/${concept.toLowerCase()}/trading-guide`,
          `https://forum.example.com/discussion/${concept.toLowerCase()}`
        ];
        urls.push(...mockUrls);
      }

      await env.URLS.put(concept, JSON.stringify(urls));

      return new Response(JSON.stringify({
        stored: urls.length,
        urls: urls,
        concept: concept
      }), {
        headers: { 'Content-Type': 'application/json' }
      });
    } catch (error) {
      return new Response(`Error: ${error.message}`, { status: 500 });
    }
  }
};

describe('Edge Worker', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('should process concept and store URLs in KV', async () => {
    const request = new Request('http://localhost', {
      method: 'POST',
      body: JSON.stringify({ concept: 'bitcoin' }),
      headers: { 'Content-Type': 'application/json' }
    });

    const response = await worker.fetch(request, mockEnv);
    const result = await response.json();

    expect(response.status).toBe(200);
    expect(result.concept).toBe('bitcoin');
    expect(result.stored).toBe(9); // 3 queries × 3 URLs each
    expect(result.urls).toHaveLength(9);
    expect(mockEnv.URLS.put).toHaveBeenCalledWith('bitcoin', expect.any(String));
  });

  test('should return 400 for missing concept', async () => {
    const request = new Request('http://localhost', {
      method: 'POST',
      body: JSON.stringify({}),
      headers: { 'Content-Type': 'application/json' }
    });

    const response = await worker.fetch(request, mockEnv);
    expect(response.status).toBe(400);
  });

  test('should return 405 for non-POST requests', async () => {
    const request = new Request('http://localhost', {
      method: 'GET'
    });

    const response = await worker.fetch(request, mockEnv);
    expect(response.status).toBe(405);
  });
});