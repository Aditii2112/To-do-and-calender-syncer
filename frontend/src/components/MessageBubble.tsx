interface MessageBubbleProps {
  role: 'user' | 'assistant';
  content: string | React.ReactNode;
}

export function MessageBubble({ role, content }: MessageBubbleProps) {
  const isUser = role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
          isUser
            ? 'bg-oasis-600 text-white rounded-br-md'
            : 'bg-white text-gray-800 border border-gray-100 shadow-sm rounded-bl-md'
        }`}
      >
        {typeof content === 'string' ? (
          <span className="whitespace-pre-wrap">
            {content.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
              part.startsWith('**') && part.endsWith('**') ? (
                <strong key={i}>{part.slice(2, -2)}</strong>
              ) : (
                part
              )
            )}
          </span>
        ) : (
          content
        )}
      </div>
    </div>
  );
}
