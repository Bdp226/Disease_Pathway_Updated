import React from 'react';
import { COLORS, SOLUTION_COLORS } from '../utils/constants.js';
import Linkify from './Linkify.jsx';
import { API_BASE_URL } from '../utils/constants.js';

// ── Severity config ─────────────────────────────────────────────────────────
const SEVERITY_CONFIG = {
  critical: { label: 'Critical', color: '#ff4444', bg: 'rgba(255,68,68,0.15)' },
  high:     { label: 'High',     color: '#ff8c00', bg: 'rgba(255,140,0,0.15)' },
  medium:   { label: 'Medium',   color: '#ffd700', bg: 'rgba(255,215,0,0.15)' },
  low:      { label: 'Low',      color: '#44cc77', bg: 'rgba(68,204,119,0.15)' },
};

const TAG_COLORS = ['#00bcd4', '#7c4dff', '#ff6b6b', '#4caf50', '#ff9800', '#e91e63', '#2196f3', '#9c27b0'];

const SeverityBadge = ({ severity }) => {
  if (!severity) return null;
  const cfg = SEVERITY_CONFIG[severity.toLowerCase()] || SEVERITY_CONFIG.medium;
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '4px',
      padding: '3px 10px',
      borderRadius: '20px',
      backgroundColor: cfg.bg,
      border: `1px solid ${cfg.color}`,
      color: cfg.color,
      fontSize: '0.75rem',
      fontWeight: '700',
      letterSpacing: '0.5px',
      textTransform: 'uppercase'
    }}>
      {cfg.label}
    </span>
  );
};

const TagChip = ({ tag, index }) => (
  <span style={{
    display: 'inline-block',
    padding: '2px 8px',
    borderRadius: '12px',
    backgroundColor: `${TAG_COLORS[index % TAG_COLORS.length]}22`,
    border: `1px solid ${TAG_COLORS[index % TAG_COLORS.length]}55`,
    color: TAG_COLORS[index % TAG_COLORS.length],
    fontSize: '0.7rem',
    fontWeight: '600'
  }}>
    {tag}
  </span>
);

const TrendingBadge = () => (
  <span style={{
    display: 'inline-flex',
    alignItems: 'center',
    gap: '3px',
    padding: '2px 8px',
    borderRadius: '12px',
    background: 'linear-gradient(135deg, #ff6b35, #f7c948)',
    color: '#fff',
    fontSize: '0.7rem',
    fontWeight: '700'
  }}>
    Trending
  </span>
);

// ── Track view silently ──────────────────────────────────────────────────────
const trackView = (painPointId) => {
  if (!painPointId) return;
  fetch(`${API_BASE_URL}/pain-points/${painPointId}/track-view`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  }).catch(() => {});
};

// ── Main Component ───────────────────────────────────────────────────────────
const PainPointCard = ({ 
  painPoint, 
  index, 
  onClick, 
  stageColors, 
  isDarkTheme = false,
  isTrending = false
}) => {
  const getSolutionCount = () => {
    return Object.values(painPoint.solutions || {}).reduce((total, solutions) => {
      return total + (Array.isArray(solutions) ? solutions.length : (solutions ? 1 : 0));
    }, 0);
  };

  const hasNewFields = () => {
    return (painPoint.coverage && painPoint.coverage.trim()) || 
           (painPoint.existing_solutions && painPoint.existing_solutions.trim());
  };

  const parsedTags = Array.isArray(painPoint.tags)
    ? painPoint.tags
    : (typeof painPoint.tags === 'string' && painPoint.tags)
      ? painPoint.tags.split(',').map(t => t.trim()).filter(Boolean)
      : [];

  const handleClick = () => {
    trackView(painPoint.id);
    onClick(painPoint);
  };

  return (
    <button 
      className="pain-point-card"
      onClick={handleClick}
      style={{
        background: isDarkTheme 
          ? `rgba(255, 255, 255, 0.08)` 
          : `rgba(255, 255, 255, 0.25)`,
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        border: `1px solid ${stageColors?.primary || COLORS.primaryTeal}60`,
        padding: '2rem',
        borderRadius: '16px',
        cursor: 'pointer',
        textAlign: 'left',
        width: '100%',
        fontFamily: 'inherit',
        height: '100%',
        minHeight: '320px',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
        overflow: 'hidden',
        boxShadow: `0 8px 32px ${stageColors?.primary || COLORS.primaryTeal}20`,
        userSelect: 'none',
        WebkitUserSelect: 'none',
        MozUserSelect: 'none',
        msUserSelect: 'none',
        outline: 'none',
        WebkitTapHighlightColor: 'transparent',
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'translateY(-8px) scale(1.02)';
        e.currentTarget.style.boxShadow = `0 25px 50px ${stageColors?.primary || COLORS.primaryTeal}30`;
        e.currentTarget.style.borderColor = stageColors?.primary || COLORS.primaryTeal;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'translateY(0) scale(1)';
        e.currentTarget.style.boxShadow = `0 8px 32px ${stageColors?.primary || COLORS.primaryTeal}20`;
        e.currentTarget.style.borderColor = `${stageColors?.primary || COLORS.primaryTeal}60`;
      }}
      onFocus={(e) => e.currentTarget.blur()}
      onContextMenu={(e) => e.preventDefault()}
      tabIndex="-1"
    >
      {/* Color Accent Bar */}
      <div style={{
        position: 'absolute',
        top: 0, left: 0, right: 0,
        height: '6px',
        background: `linear-gradient(90deg, ${stageColors?.primary || COLORS.primaryTeal}, ${stageColors?.secondary || COLORS.primaryTealLight})`,
        borderRadius: '16px 16px 0 0',
        pointerEvents: 'none'
      }} />

      {/* Header: Title + Severity + Trending */}
      <div style={{ marginBottom: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginBottom: '0.5rem' }}>
          <h3 style={{ 
            color: COLORS.white,
            fontSize: '1rem',
            fontWeight: '700',
            margin: 0,
            textShadow: `0 0 10px ${stageColors?.primary || COLORS.primaryTeal}40`
          }}>
            Pain Point
          </h3>
          {isTrending && <TrendingBadge />}
        </div>
        {/* Severity badge */}
        {painPoint.severity && <SeverityBadge severity={painPoint.severity} />}
      </div>

      {/* Tags row */}
      {parsedTags.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginBottom: '0.75rem' }}>
          {parsedTags.map((tag, i) => (
            <TagChip key={tag} tag={tag} index={i} />
          ))}
        </div>
      )}

      {/* Description */}
      <div style={{ flex: 1, marginBottom: '1rem' }}>
        <p style={{
          color: COLORS.white,
          margin: 0,
          display: '-webkit-box',
          WebkitLineClamp: 7,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          fontSize: '0.95rem',
          lineHeight: '1.6',
          fontWeight: '500',
          opacity: 0.9,
          pointerEvents: 'auto'
        }}>
          <Linkify linkColor={stageColors?.primary || COLORS.primaryTeal}>{painPoint.description}</Linkify>
        </p>
      </div>

      {/* Additional Info */}
      {hasNewFields() && (
        <div style={{
          marginBottom: '1rem',
          padding: '0.75rem',
          background: `rgba(255, 255, 255, 0.05)`,
          backdropFilter: 'blur(8px)',
          borderRadius: '8px',
          border: `1px solid ${stageColors?.primary || COLORS.primaryTeal}40`
        }}>
          <div style={{ fontSize: '0.8rem', color: stageColors?.primary || COLORS.primaryTeal, fontWeight: '600', marginBottom: '0.25rem' }}>
            Additional Information Available:
          </div>
          <div style={{ fontSize: '0.75rem', color: COLORS.white }}>
            {painPoint.coverage && painPoint.coverage.trim() && (
              <span style={{ marginRight: '0.75rem' }}>• Our portfolio coverage </span>
            )}
            {painPoint.existing_solutions && painPoint.existing_solutions.trim() && (
              <span>• Existing Solutions</span>
            )}
          </div>
        </div>
      )}

      {/* Footer */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingTop: '1rem',
        borderTop: `1px solid ${stageColors?.primary || COLORS.primaryTeal}40`,
        marginTop: 'auto'
      }}>
        <div style={{ color: COLORS.white, fontWeight: '600', fontSize: '0.85rem' }}>
          {getSolutionCount() > 0 ? `${getSolutionCount()} solutions` : 'Click for details'}
        </div>
        <div style={{ fontSize: '1.3rem', color: stageColors?.primary || COLORS.primaryTeal, fontWeight: 'bold' }}>
          →
        </div>
      </div>
    </button>
  );
};

export default PainPointCard;
