import React, { useState } from 'react';
import { COLORS } from '../utils/constants.js';
import { painPointAPI } from '../utils/api.js';

const AddPainPointModal = ({ isOpen, onClose, diseaseName, stageId, stageName, isDarkTheme, onSuccess }) => {
  const [formData, setFormData] = useState({
    description: '',
    sources: '',
    coverage: '',
    existing_solutions: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    if (!formData.description.trim()) {
      setError('Description is required');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await painPointAPI.submitPainPoint(diseaseName, stageId, formData);
      setFormData({ description: '', sources: '', coverage: '', existing_solutions: '' });
      if (onSuccess) onSuccess();
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to submit pain point');
    } finally {
      setLoading(false);
    }
  };

  const modalBg = isDarkTheme ? '#1e1e1e' : '#ffffff';
  const textColor = isDarkTheme ? '#ffffff' : '#000000';
  const labelColor = isDarkTheme ? '#aaaaaa' : '#555555';
  const inputBg = isDarkTheme ? '#2d2d2d' : '#f5f5f5';
  const borderColor = isDarkTheme ? '#444' : '#ccc';

  const inputStyle = {
    width: '100%',
    padding: '10px',
    borderRadius: '6px',
    border: `1px solid ${borderColor}`,
    backgroundColor: inputBg,
    color: textColor,
    boxSizing: 'border-box',
    fontSize: '0.95rem'
  };

  const labelStyle = {
    display: 'block',
    color: textColor,
    marginBottom: '5px',
    fontWeight: 'bold',
    fontSize: '0.9rem'
  };

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: 'fixed',
          inset: 0,
          backgroundColor: 'rgba(0,0,0,0.7)',
          zIndex: 2000
        }}
      />

      {/* Modal */}
      <div
        style={{
          position: 'fixed',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          zIndex: 2001,
          width: '90%',
          maxWidth: '580px',
          maxHeight: '85vh',
          backgroundColor: modalBg,
          borderRadius: '12px',
          boxShadow: '0 10px 40px rgba(0,0,0,0.4)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}
      >
        {/* Header */}
        <div style={{
          padding: '20px 25px 15px 25px',
          borderBottom: `1px solid ${borderColor}`,
          flexShrink: 0,
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between'
        }}>
          <div>
            <h2 style={{ color: COLORS.primaryTeal, margin: '0 0 5px 0', fontSize: '1.3rem' }}>
              Add New Pain Point
            </h2>
            <p style={{ color: labelColor, margin: 0, fontSize: '0.85rem' }}>
              Propose a new pain point for <strong>{stageName}</strong>.{' '}
              An AI assistant will verify it for clinical relevance.
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              fontSize: '1.4rem',
              cursor: 'pointer',
              color: textColor,
              opacity: 0.6,
              flexShrink: 0,
              marginLeft: '10px',
              lineHeight: 1
            }}
          >
            &times;
          </button>
        </div>

        {/* Scrollable Body */}
        <div style={{ overflowY: 'auto', padding: '20px 25px', flexGrow: 1 }}>
          {error && (
            <div style={{
              backgroundColor: 'rgba(255,0,0,0.1)',
              color: 'red',
              padding: '10px',
              borderRadius: '6px',
              marginBottom: '15px',
              fontSize: '0.9rem'
            }}>
              {error}
            </div>
          )}

          <form id="add-pain-point-form" onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            <div>
              <label style={labelStyle}>Description *</label>
              <textarea
                name="description"
                value={formData.description}
                onChange={handleChange}
                rows="4"
                style={inputStyle}
                placeholder="Describe the clinical or operational challenge..."
              />
            </div>

            <div>
              <label style={labelStyle}>Sources (Optional)</label>
              <input
                type="text"
                name="sources"
                value={formData.sources}
                onChange={handleChange}
                style={inputStyle}
                placeholder="E.g., PubMed, Clinical Guidelines, etc."
              />
            </div>

            <div>
              <label style={labelStyle}>Portfolio Coverage (Optional)</label>
              <textarea
                name="coverage"
                value={formData.coverage}
                onChange={handleChange}
                rows="2"
                style={inputStyle}
                placeholder="Our current coverage..."
              />
            </div>

            <div>
              <label style={labelStyle}>Existing Solutions (Optional)</label>
              <textarea
                name="existing_solutions"
                value={formData.existing_solutions}
                onChange={handleChange}
                rows="2"
                style={inputStyle}
                placeholder="Any existing or potential solutions..."
              />
            </div>
          </form>
        </div>

        {/* Footer — always visible */}
        <div style={{
          padding: '15px 25px',
          borderTop: `1px solid ${borderColor}`,
          display: 'flex',
          justifyContent: 'flex-end',
          gap: '10px',
          flexShrink: 0,
          backgroundColor: modalBg
        }}>
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            style={{
              padding: '9px 18px',
              borderRadius: '6px',
              border: `1px solid ${borderColor}`,
              backgroundColor: 'transparent',
              color: textColor,
              cursor: 'pointer',
              fontSize: '0.9rem'
            }}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={loading}
            style={{
              padding: '9px 18px',
              borderRadius: '6px',
              border: 'none',
              backgroundColor: COLORS.primaryTeal,
              color: '#fff',
              fontWeight: 'bold',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.7 : 1,
              fontSize: '0.9rem'
            }}
          >
            {loading ? 'Verifying...' : 'Submit Pain Point'}
          </button>
        </div>
      </div>
    </>
  );
};

export default AddPainPointModal;
