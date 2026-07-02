import React, { useEffect, useRef } from 'react';
import SuggestionCards from './SuggestionCards';
import { RAGResponse } from '../lib/api';

interface Message {
  role: 'user' | 'ai';
  content: string;
  sources?: RAGResponse['sources'];
}

interface ChatAreaProps {
  messages: Message[];
}

export default function ChatArea({ messages }: ChatAreaProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="chat-history" style={{ alignItems: 'center', justifyContent: 'center', paddingBottom: '0' }}>
        <div style={{ width: '64px', height: '64px', borderRadius: '50%', background: '#E8F0FE', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '24px' }}>
          <span style={{ fontSize: '32px', color: 'var(--color-secondary)' }}>⚖️</span>
        </div>
        <div className="greeting">
          <h1 className="greeting-title">Bonjour.</h1>
          <h2 className="greeting-subtitle">Comment puis-je vous aider aujourd'hui ?</h2>
        </div>
        <SuggestionCards />
      </div>
    );
  }

  return (
    <div className="chat-history">
      {messages.map((msg, idx) => (
        <div key={idx} className={`message ${msg.role}`}>
          {msg.role === 'ai' && msg.content === '' ? (
            <div className="typing-loader">
              <div className="typing-dot"></div>
              <div className="typing-dot"></div>
              <div className="typing-dot"></div>
            </div>
          ) : (
            <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.6' }}>{msg.content}</div>
          )}
          
          {msg.sources && msg.sources.length > 0 && (
            <div style={{ marginTop: '16px', display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {msg.sources.map((src, i) => (
                <div key={i} className="citation-chip">
                  {src.article_number ? `Article ${src.article_number}` : src.document_title}
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
