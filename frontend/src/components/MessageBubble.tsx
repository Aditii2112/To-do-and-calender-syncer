import type { ReactNode } from 'react';
import './MessageBubble.css';

interface MessageBubbleProps {
  role: 'user' | 'assistant';
  content: string | ReactNode;
}

export function MessageBubble({ role, content }: MessageBubbleProps) {
  return (
    <div className={`message-bubble message-bubble--${role}`}>
      <div className="message-bubble__content">
        {typeof content === 'string' ? (
          <pre className="message-bubble__text">{content}</pre>
        ) : (
          content
        )}
      </div>
    </div>
  );
}
