import React, { useState, useEffect, useRef } from 'react';
import type { Message } from './ChatMessage';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import { ChatAPI } from '../../api/client';

interface ChatWindowProps {
  conversationId: string;
  onUpdateTitle: (title: string) => void;
}

const ChatWindow: React.FC<ChatWindowProps> = ({ conversationId, onUpdateTitle }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const fetchMessages = async () => {
    setIsLoading(true);
    try {
      const msgs = await ChatAPI.getMessages(conversationId);
      const mappedMsgs: Message[] = msgs.map((m: any) => ({
        id: m.id,
        role: m.role,
        content: m.content,
      }));
      setMessages(mappedMsgs);
    } catch (err) {
      console.error('Error fetching messages:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (conversationId) {
      fetchMessages();
    }
  }, [conversationId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (content: string) => {
    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
    };

    setMessages(prev => [...prev, userMsg]);
    setIsStreaming(true);

    const assistantMsgId = (Date.now() + 1).toString();
    setStreamingMessageId(assistantMsgId);
    setMessages(prev => [
      ...prev,
      { id: assistantMsgId, role: 'assistant', content: '' }
    ]);

    let finalTitle = '';

    try {
      const stream = ChatAPI.streamChat({
        message: content,
        conversation_id: conversationId,
      });

      for await (const event of stream) {
        if (event.event === 'delta') {
          setMessages(prev => prev.map(m =>
            m.id === assistantMsgId ? { ...m, content: m.content + (event.delta || '') } : m
          ));
        } else if (event.event === 'completion') {
          if (event.data?.conversation_title) {
            finalTitle = event.data.conversation_title;
          }
        } else if (event.event === 'error') {
          setMessages(prev => prev.map(m =>
            m.id === assistantMsgId ? { ...m, content: m.content + '\n\n*An error occurred. Please try again.*' } : m
          ));
        }
      }

      if (finalTitle) {
        onUpdateTitle(finalTitle);
      }
    } catch (err) {
      console.error('Chat error:', err);
      setMessages(prev => prev.map(m =>
        m.id === assistantMsgId ? { ...m, content: m.content + '\n\n*Connection error. Please try again.*' } : m
      ));
    } finally {
      setIsStreaming(false);
      setStreamingMessageId(null);
    }
  };

  return (
    <div className="chat-window">
      <div className="chat-messages">
        <div className="chat-messages-inner">
          {isLoading && messages.length === 0 ? (
            <div style={{ textAlign: 'center', color: 'var(--text-3)' }}>Loading messages...</div>
          ) : (
            messages.map(msg => (
              <ChatMessage
                key={msg.id}
                message={msg}
                isStreaming={isStreaming && msg.id === streamingMessageId && msg.content.length > 0}
              />
            ))
          )}
          {isStreaming && streamingMessageId && (() => {
            const streamMsg = messages.find(m => m.id === streamingMessageId);
            if (!streamMsg || streamMsg.content.length === 0) {
              return (
                <div className="message-row assistant">
                  <div className="message-bubble" style={{ padding: '8px 16px' }}>
                    <div className="loading-indicator">
                      <div className="dot-flashing"></div>
                    </div>
                  </div>
                </div>
              );
            }
            return null;
          })()}
          <div ref={messagesEndRef} />
        </div>
      </div>
      <div className="chat-input-inner">
        <ChatInput onSend={handleSend} disabled={isStreaming} />
      </div>
    </div>
  );
};

export default ChatWindow;
