import React from 'react';

const URL_REGEX = /(https?:\/\/[^\s]+)/g;

const Linkify = ({ children, linkColor = '#00A3AD' }) => {
  if (typeof children !== 'string') {
    return children;
  }

  const parts = children.split(URL_REGEX);
  
  return (
    <>
      {parts.map((part, i) => {
        if (part.match(URL_REGEX)) {
          return (
            <a 
              key={i} 
              href={part} 
              target="_blank" 
              rel="noopener noreferrer"
              style={{ 
                color: linkColor, 
                textDecoration: 'underline', 
                wordBreak: 'break-all',
                position: 'relative',
                zIndex: 2
              }}
              onClick={(e) => e.stopPropagation()}
            >
              {part}
            </a>
          );
        }
        return part;
      })}
    </>
  );
};

export default Linkify;
