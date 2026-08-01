import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export interface Citation {
  media_id?: string;
  title?: string;
  chunk_id?: string;
  modality?: string;
  score?: number;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  citations?: Citation[];
}

interface ChatMessageProps {
  message: Message;
  isStreaming?: boolean;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message, isStreaming }) => {
  return (
    <div className={`message-row ${message.role}`}>
      <div className="message-bubble">
        <div className={`message-content${isStreaming ? ' streaming' : ''}`}>
          {message.role === 'assistant' ? (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          ) : (
            message.content
          )}
          {isStreaming && <span className="streaming-cursor">▍</span>}
        </div>
      </div>
    </div>
  );
};

export default ChatMessage;
