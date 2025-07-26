// index.js
var index_default = {
  async fetch(request, env) {
    if (request.method !== "POST") {
      return new Response("Method not allowed", { status: 405 });
    }
    try {
      const { concept } = await request.json();
      if (!concept) {
        return new Response("Concept required", { status: 400 });
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
        urls,
        concept
      }), {
        headers: { "Content-Type": "application/json" }
      });
    } catch (error) {
      return new Response(`Error: ${error.message}`, { status: 500 });
    }
  }
};
export {
  index_default as default
};
//# sourceMappingURL=index.js.map
