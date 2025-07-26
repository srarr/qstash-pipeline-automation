// Cloudflare Worker for concept processing and URL discovery
export default {
  async fetch(request, env) {
    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 });
    }

    try {
      const { concept } = await request.json();
      
      if (!concept) {
        return new Response('Concept required', { status: 400 });
      }

      // Generate Google-style search queries
      const queries = [
        `${concept} trading`,
        `${concept} pinescript`, 
        `${concept} pdf`
      ];

      const urls = [];
      
      // Mock URL extraction for each query (in production, would fetch real results)
      for (const query of queries) {
        // Simulate search results with mock URLs
        const mockUrls = [
          `https://example.com/search?q=${encodeURIComponent(query)}&result=1`,
          `https://docs.example.com/${concept.toLowerCase()}/trading-guide`,
          `https://forum.example.com/discussion/${concept.toLowerCase()}`
        ];
        urls.push(...mockUrls);
      }

      // Store URLs in Cloudflare KV
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