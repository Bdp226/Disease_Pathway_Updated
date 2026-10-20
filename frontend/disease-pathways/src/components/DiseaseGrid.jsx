import React from 'react';
import { Link } from 'react-router-dom';

const DiseaseGrid = ({ diseases }) => {
  const getSpecialtyConfig = (name) => {
    const lowerName = name.toLowerCase();

    if (lowerName.includes('coronary artery disease') || lowerName === 'cad' || lowerName.includes('cardio') || lowerName.includes('heart')) {
      return {
        label: 'Cardio-vascular',
        accentColor: '#FF6600', // Neon Orange
        bgGlow: 'rgba(255, 102, 0, 0.1)', // 10% opacity for glow
        innerGlow: 'radial-gradient(circle at top left, rgba(255, 102, 0, 0.05) 0%, transparent 70%)'
      };
    }
    
    if (lowerName.includes('cancer')) {
      return {
        label: 'Oncology',
        accentColor: '#5DCED9', // Light Teal
        bgGlow: 'rgba(93, 206, 217, 0.1)',
        innerGlow: 'radial-gradient(circle at top left, rgba(93, 206, 217, 0.05) 0%, transparent 70%)'
      };
    }

    return {
      label: 'General Clinical',
      accentColor: '#00A3AD', // Standard Teal
      bgGlow: 'rgba(0, 163, 173, 0.1)',
      innerGlow: 'radial-gradient(circle at top left, rgba(0, 163, 173, 0.05) 0%, transparent 70%)'
    };
  };

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
      gap: '1.8rem',
      margin: '2rem 0',
      padding: '0',
      backgroundColor: 'transparent',
    }}>
      {diseases.map((disease) => {
        const config = getSpecialtyConfig(disease.name);
        
        return (
          <Link 
            key={disease.id}
            to={`/pathway/${disease.name}`}
            style={{
              padding: '2.2rem',
              borderRadius: '18px',
              // LAYERED BACKGROUND: Inner glow gradient + solid obsidian
              background: `${config.innerGlow}, linear-gradient(180deg, #0f151a 0%, #0d1216 100%)`,
              border: `1px solid rgba(255, 255, 255, 0.1)`,
              cursor: 'pointer',
              transition: 'all 0.34s cubic-bezier(0.22, 1, 0.36, 1)',
              textDecoration: 'none',
              display: 'block',
              position: 'relative',
              boxShadow: 'inset 0 1px 0 rgba(255, 255, 255, 0.06), 0 10px 28px rgba(0, 0, 0, 0.22)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-6px)';
              e.currentTarget.style.borderColor = config.accentColor;
              e.currentTarget.style.boxShadow = `0 14px 36px ${config.bgGlow}, inset 0 1px 0 rgba(255, 255, 255, 0.06)`;
              // Make the internal glow slightly more visible on hover
              e.currentTarget.style.background = `radial-gradient(circle at top left, ${config.accentColor}1A 0%, transparent 70%), linear-gradient(180deg, #111923 0%, #0d1216 100%)`;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)';
              e.currentTarget.style.boxShadow = 'inset 0 1px 0 rgba(255, 255, 255, 0.06), 0 10px 28px rgba(0, 0, 0, 0.22)';
              e.currentTarget.style.background = `${config.innerGlow}, linear-gradient(180deg, #0f151a 0%, #0d1216 100%)`;
            }}
          >
            {/* Tag */}
            <div style={{
              display: 'inline-block',
              padding: '5px 14px',
              borderRadius: '8px',
              fontSize: '11px',
              fontWeight: '800',
              letterSpacing: '1.2px',
              textTransform: 'uppercase',
              backgroundColor: config.bgGlow,
              color: config.accentColor,
              border: `1px solid ${config.accentColor}44`,
              marginBottom: '1.5rem'
            }}>
              {config.label}
            </div>

            <h3 style={{ 
              marginBottom: '1.2rem', 
              color: '#f0f6fb',
              textTransform: 'capitalize',
              fontSize: '1.45rem',
              fontWeight: '700',
              lineHeight: '1.2'
            }}>
              {disease.name}
            </h3>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.8rem' }}>
              <span style={{ color: '#90a0ad', fontSize: '0.95rem' }}>Protocol Stages</span>
              <span style={{ fontWeight: '600', color: '#f0f6fb' }}>
                {disease.stage_count}
              </span>
            </div>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2rem' }}>
              <span style={{ color: '#90a0ad', fontSize: '0.95rem' }}>Total Pain Points</span>
              <span style={{ fontWeight: '800', color: config.accentColor }}>
                {disease.total_pain_points}
              </span>
            </div>
            
            <div style={{
              fontSize: '0.72rem',
              color: '#90a0ad',
              borderTop: '1px solid rgba(255, 255, 255, 0.05)',
              paddingTop: '1.2rem',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              letterSpacing: '0.5px'
            }}>
              <span>LAST UPDATED: {new Date(disease.updated_at).toLocaleDateString()}</span>
              <span style={{ 
                color: config.accentColor, 
                fontSize: '1.2rem',
                fontWeight: 'bold'
              }}>→</span>
            </div>
          </Link>
        );
      })}
    </div>
  );
};

export default DiseaseGrid;