import React, { useState, useEffect } from 'react';
import { diseaseAPI } from '../utils/api.js';
import DiseaseGrid from '../components/DiseaseGrid.jsx';
import PlaceholderDiseaseGrid from '../components/PlaceholderDiseaseGrid.jsx'; // Ensure this import is here
import LoadingSpinner from '../components/LoadingSpinner.jsx';
import { AnalyticsDashboard } from '../components/AnalyticsDashboard.jsx';
import { COLORS } from '../utils/constants.js';


const DiseaseSelection = () => {
  const [diseases, setDiseases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const placeholders = [
    { name: "Alzheimer's Disease", specialty: "Neuro-Degenerative" },
    { name: "Lung Cancer", specialty: "Cancer" }
  ];

  useEffect(() => {
    const fetchDiseases = async () => {
      try {
        const data = await diseaseAPI.getAllDiseases();
        setDiseases(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchDiseases();
  }, []);

  return (
    <div style={{
      paddingTop: '104px',
      minHeight: '100vh',
      background:
        'radial-gradient(900px 600px at 90% 0%, rgba(236,103,2,0.16), transparent 55%), radial-gradient(900px 700px at 10% 0%, rgba(0,153,153,0.14), transparent 55%), #070b0f'
    }}>
      <div className="container">
        <h1 style={{ 
          fontFamily: 'SHBree',
          textAlign: 'center', 
          marginBottom: '0.75rem', 
          color: COLORS.accentOrange,
          fontSize: '2.8rem',
          letterSpacing: '-0.01em'
        }}>
          Select a Disease Pathway
        </h1>

        <p style={{
          textAlign: 'center',
          color: '#9eb0bf',
          maxWidth: '760px',
          margin: '0 auto 2.75rem auto',
          lineHeight: '1.65',
          fontSize: '1.02rem'
        }}>
          Explore structured pathways, stage insights, and high-impact pain points across clinical domains.
        </p>

        
        {loading ? (
          <LoadingSpinner />
        ) : error ? (
          <div style={{ 
            textAlign: 'center', 
            color: '#FF6B35', 
            fontSize: '1.2rem',
            padding: '2rem'
          }}>
            Error: {error}
          </div>
        ) : (
          <>
            {/* 1. RENDER LIVE DISEASES (If any exist) */}
            {diseases.length > 0 ? (
              <DiseaseGrid diseases={diseases} />
            ) : (
              <div style={{ 
                textAlign: 'center', 
                color: '#9eb0bf', 
                fontSize: '1.1rem',
                padding: '3rem',
                border: '1px dashed rgba(255,255,255,0.2)',
                borderRadius: '12px',
                marginBottom: '3rem'
              }}>
                No live pathways found in the database.
              </div>
            )}

            {/* 2. RENDER PLACEHOLDERS (Always visible) */}
            <div style={{ marginTop: '5rem', marginBottom: '5rem' }}>
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center', 
                gap: '20px', 
                marginBottom: '2rem' 
              }}>
              </div>

              <PlaceholderDiseaseGrid placeholders={placeholders} />
            </div>

            {/* 3. RENDER ANALYTICS DASHBOARD */}
            <div style={{ marginTop: '3rem', marginBottom: '3rem' }}>
              <AnalyticsDashboard />
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default DiseaseSelection;