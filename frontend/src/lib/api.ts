export interface RAGResponse {
  question: string;
  answer: string;
  sources: {
    article_number: string | null;
    document_title: string;
    domain: string;
    doc_type: string;
    date_enacted: string;
    source_url: string;
    excerpt: string;
    rrf_score?: number;
  }[];
  retrieved_count: number;
  retrieval_ms: number;
  generation_ms: number;
  had_citations: boolean;
  was_grounded: boolean;
  qa_log_id: string | null;
}

export const askQuestion = async (question: string): Promise<RAGResponse> => {
  const response = await fetch("http://127.0.0.1:8001/api/ask", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question }),
  });

  if (!response.ok) {
    throw new Error("Failed to fetch response from API");
  }

  return response.json();
};

export const askQuestionStream = async (
  question: string,
  onSources: (sources: any[]) => void,
  onChunk: (chunk: string) => void,
  onDone: (logId: string | null) => void,
  onError: (error: Error) => void
) => {
  try {
    const response = await fetch("http://127.0.0.1:8001/api/ask/stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ question }),
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch response: ${response.status}`);
    }

    if (!response.body) {
      throw new Error("ReadableStream not yet supported in this browser.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const parsed = JSON.parse(line);
          if (parsed.type === "sources") {
            onSources(parsed.data);
          } else if (parsed.type === "token") {
            onChunk(parsed.content);
          } else if (parsed.type === "done") {
            onDone(parsed.qa_log_id || null);
          }
        } catch (e) {
          console.error("Failed to parse stream chunk:", line, e);
        }
      }
    }
  } catch (err: any) {
    onError(err);
  }
};
