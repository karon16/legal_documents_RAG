import React, { useState } from 'react';
import { Globe, Paperclip, ArrowUp } from 'lucide-react';

interface ChatInputProps {
  onSendMessage: (msg: string) => void;
  isLoading: boolean;
}

export default function ChatInput({ onSendMessage, isLoading }: ChatInputProps) {
  const [input, setInput] = useState('');

  const handleSend = () => {
    if (input.trim() && !isLoading) {
      onSendMessage(input.trim());
      setInput('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-input-container">
      <textarea
        className="chat-input"
        placeholder="Posez votre question juridique..."
        rows={2}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
      />
      <div className="chat-input-actions">
        <div className="action-left">
          <button className="action-btn">
            <Globe size={16} />
            Recherche Web
          </button>
          <button className="action-btn">
            <Paperclip size={16} />
          </button>
        </div>
        <button 
          className="send-btn" 
          onClick={handleSend}
          disabled={!input.trim() || isLoading}
          style={{ opacity: !input.trim() || isLoading ? 0.5 : 1 }}
        >
          <ArrowUp size={16} />
        </button>
      </div>
    </div>
  );
}
