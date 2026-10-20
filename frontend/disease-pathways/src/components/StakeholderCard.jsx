import React, { useState } from 'react';
import { COLORS } from '../utils/constants.js';

const StakeholderCard = ({ 
  stakeholder,  
  imagePath,  // Changed from 'icon' to 'imagePath'
  stageColors, 
  isDarkTheme = false 
}) => {
  const [imageError, setImageError] = useState(false);
  const [imageLoaded, setImageLoaded] = useState(false);

  // Extract first word as fallback text
  const fallbackText = stakeholder.trim().split(' ')[0].charAt(0).toUpperCase();

  return (
    <div style={{
      background: isDarkTheme 
        ? 'rgba(255, 255, 255, 0.09)'
        : 'rgba(255, 255, 255, 0.18)',
      backdropFilter: 'blur(10px)',
      borderRadius: '16px',
      padding: '1.5rem',
      border: `1px solid ${stageColors?.accent || COLORS.primaryTeal}55`,
      boxShadow: `0 4px 10px rgba(0, 0, 0, 0.22)`,
      transition: 'all 0.3s ease',
      cursor: 'pointer'
    }}
    onMouseEnter={(e) => {
      e.currentTarget.style.transform = 'translateY(-5px)';
      e.currentTarget.style.boxShadow = `0 8px 16px rgba(0, 0, 0, 0.28)`;
      e.currentTarget.style.borderColor = stageColors?.primary || COLORS.primaryTeal;
    }}
    onMouseLeave={(e) => {
      e.currentTarget.style.transform = 'translateY(0)';
      e.currentTarget.style.boxShadow = `0 4px 10px rgba(0, 0, 0, 0.22)`;
      e.currentTarget.style.borderColor = `${stageColors?.accent || COLORS.primaryTeal}55`;
    }}
    >
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '1rem'
      }}>
        {/* NEW: Image Icon Circle */}
        <div style={{
          width: '56px',
          height: '56px',
          borderRadius: '50%',
          background: '#f7fafc',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '1.5rem',
          flexShrink: 0,
          boxShadow: `0 4px 10px ${stageColors?.accent || COLORS.primaryTeal}45`,
          border: `1px solid ${stageColors?.accent || COLORS.primaryTeal}55`,
          position: 'relative',
          overflow: 'hidden'
        }}>
          {/* Loading state */}
          {!imageLoaded && !imageError && (
            <div style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              color: COLORS.white,
              fontSize: '1.2rem',
              fontWeight: '600'
            }}>
              {fallbackText}
            </div>
          )}

          {/* Image */}
          {!imageError && (
            <img 
              src={imagePath}
              alt={stakeholder}
              loading="eager"  // Lazy loading for performance
              onLoad={() => setImageLoaded(true)}
              onError={() => {
                console.warn(`Failed to load image: ${imagePath}`);
                setImageError(true);
              }}
              style={{
                width: '74%',
                height: '74%',
                objectFit: 'contain',
                objectPosition: 'center center',
                display: imageLoaded ? 'block' : 'none'
              }}
            />
          )}

          {/* Fallback text if image fails */}
          {imageError && (
            <div style={{
              color: COLORS.white,
              fontSize: '1.2rem',
              fontWeight: '600'
            }}>
              {fallbackText}
            </div>
          )}
        </div>

        {/* Stakeholder Text */}
        <div style={{
          color: COLORS.white,
          fontSize: '0.95rem',
          
          lineHeight: '1.4',
          flex: 1
        }}>
          {stakeholder}
        </div>
      </div>
    </div>
  );
};

export default StakeholderCard;
