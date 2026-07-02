"use client";

import React, { useState } from 'react';
import Sidebar from '../components/Sidebar';
import ChatArea from '../components/ChatArea';
import ChatInput from '../components/ChatInput';
import { askQuestionStream } from '../lib/api';
import { Share2, Settings, ChevronDown } from 'lucide-react';

export default function Home() {
  const [messages, setMessages] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleSendMessage = async (content: string) => {
    // Add user message and empty AI message
    const userMsg = { role: 'user', content };
    const aiMsg = { role: 'ai', content: '', sources: [] };

    setMessages((prev) => [...prev, userMsg, aiMsg]);
    setIsLoading(true);

    try {
      await askQuestionStream(
        content,
        (sources) => {
          setMessages((prev) => {
            const newMessages = [...prev];
            const lastIndex = newMessages.length - 1;
            newMessages[lastIndex] = {
              ...newMessages[lastIndex],
              sources: sources
            };
            return newMessages;
          });
        },
        (chunk) => {
          setMessages((prev) => {
            const newMessages = [...prev];
            const lastIndex = newMessages.length - 1;
            newMessages[lastIndex] = {
              ...newMessages[lastIndex],
              content: newMessages[lastIndex].content + chunk
            };
            return newMessages;
          });
        },
        (logId) => {
          setIsLoading(false);
        },
        (error) => {
          console.error("Stream error:", error);
          setMessages((prev) => {
            const newMessages = [...prev];
            newMessages[newMessages.length - 1].content = "Désolé, une erreur de communication avec le serveur s'est produite.";
            return newMessages;
          });
          setIsLoading(false);
        }
      );
    } catch (error) {
      console.error("Failed to start stream:", error);
      setIsLoading(false);
    }
  };

  return (
    <div className="app-container">
      <Sidebar />
      <main className="main-content">
        {/* Header */}
        <header style={{ width: '100%', padding: '24px 0', display: 'flex', justifyContent: 'flex-end', alignItems: 'center', background: "none" }}>

          <div style={{ display: 'flex', gap: '12px' }}>
            <button style={{ width: '40px', height: '40px', borderRadius: '50%', border: '1px solid var(--color-neutral-light)', background: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}>
              <Share2 size={18} color="var(--color-neutral-dark)" />
            </button>
            <button style={{ width: '40px', height: '40px', borderRadius: '50%', border: '1px solid var(--color-neutral-light)', background: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}>
              <Settings size={18} color="var(--color-neutral-dark)" />
            </button>
          </div>
        </header>

        {/* Chat Area */}
        <ChatArea messages={messages} />

        {/* Input Area in normal flex flow at bottom */}
        <div style={{ paddingBottom: '32px', width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', position: 'relative' }}>
          <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />

          <div style={{ position: 'absolute', bottom: '8px', fontSize: '12px', color: '#9CA3AF' }}>
            JusticeCongo IA peut commettre des erreurs. Vérifiez les informations importantes.
          </div>
        </div>
      </main>
    </div>
  );
}
