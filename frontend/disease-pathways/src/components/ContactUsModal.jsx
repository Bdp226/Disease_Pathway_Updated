import React, { useState } from 'react';
import { createPortal } from 'react-dom';
import { contactUsAPI } from '../utils/api.js';
import { COLORS } from '../utils/constants.js';
import { MdClose } from 'react-icons/md';

const ContactUsModal = ({ isOpen, onClose }) => {
  const [formData, setFormData] = useState({
    user_name: '',
    user_email: '',
    subject: '',
    description: ''
  });

  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (!formData.user_name.trim()) throw new Error('Name is required');
      if (!formData.user_email.trim()) throw new Error('Email is required');
      if (!formData.subject.trim()) throw new Error('Subject is required');
      if (!formData.description.trim()) throw new Error('Message is required');

      await contactUsAPI.submitContactForm(formData);
      setSuccess(true);
      setFormData({ user_name: '', user_email: '', subject: '', description: '' });
      setTimeout(() => { setSuccess(false); onClose(); }, 2000);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleClose = () => {
    setFormData({ user_name: '', user_email: '', subject: '', description: '' });
    setError('');
    setSuccess(false);
    onClose();
  };

  if (!isOpen) return null;

  const inputStyle = {
    width: '100%',
    padding: '0.75rem',
    borderRadius: '8px',
    border: `2px solid ${COLORS.lightGray}`,
    background: COLORS.white,
    color: COLORS.gray,
    fontSize: '1rem',
    outline: 'none',
    boxSizing: 'border-box'
  };

  const labelStyle = {
    display: 'block',
    color: COLORS.gray,
    fontSize: '0.95rem',
    fontWeight: '600',
    marginBottom: '0.5rem'
  };

  return createPortal(
    <>
      {/* Backdrop */}
      <div
        onClick={handleClose}
        style={{
          position: 'fixed',
          inset: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
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
          backgroundColor: '#ffffff',
          borderRadius: '16px',
          boxShadow: '0 20px 60px rgba(0,0,0,0.25)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}
      >
        {/* Header */}
        <div style={{
          padding: '1.5rem 2rem 1rem 2rem',
          borderBottom: `1px solid ${COLORS.lightGray}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexShrink: 0
        }}>
          <div>
            <h2 style={{ color: COLORS.accentOrange, fontSize: '1.6rem', fontWeight: '700', margin: 0 }}>
              Contact Us
            </h2>
            <p style={{ color: COLORS.gray, fontSize: '0.9rem', margin: '0.25rem 0 0 0', opacity: 0.7 }}>
              We'd love to hear from you!
            </p>
          </div>
          <button
            onClick={handleClose}
            style={{
              background: 'none',
              border: 'none',
              color: COLORS.gray,
              fontSize: '1.4rem',
              cursor: 'pointer',
              padding: '0.25rem',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            <MdClose />
          </button>
        </div>

        {/* Scrollable Body */}
        <div style={{ overflowY: 'auto', padding: '1.5rem 2rem', flexGrow: 1 }}>
          {success ? (
            <div style={{ textAlign: 'center', padding: '2rem 0' }}>
              <div style={{ fontSize: '3rem', color: COLORS.primaryTeal, marginBottom: '1rem' }}>✓</div>
              <h3 style={{ color: COLORS.gray, marginBottom: '0.5rem' }}>Message Sent!</h3>
              <p style={{ color: COLORS.gray, opacity: 0.7 }}>We'll get back to you soon.</p>
            </div>
          ) : (
            <form id="contact-us-form" onSubmit={handleSubmit}>
              <div style={{ marginBottom: '1.25rem' }}>
                <label style={labelStyle}>Full Name <span style={{ color: '#d32f2f' }}>*</span></label>
                <input
                  type="text"
                  value={formData.user_name}
                  onChange={(e) => handleChange('user_name', e.target.value)}
                  placeholder="Enter your full name"
                  style={inputStyle}
                />
              </div>

              <div style={{ marginBottom: '1.25rem' }}>
                <label style={labelStyle}>Email Address <span style={{ color: '#d32f2f' }}>*</span></label>
                <input
                  type="email"
                  value={formData.user_email}
                  onChange={(e) => handleChange('user_email', e.target.value)}
                  placeholder="Enter your email address"
                  style={inputStyle}
                />
              </div>

              <div style={{ marginBottom: '1.25rem' }}>
                <label style={labelStyle}>Subject <span style={{ color: '#d32f2f' }}>*</span></label>
                <input
                  type="text"
                  value={formData.subject}
                  onChange={(e) => handleChange('subject', e.target.value)}
                  placeholder="Brief subject of your message"
                  style={inputStyle}
                />
              </div>

              <div style={{ marginBottom: '1rem' }}>
                <label style={labelStyle}>Message <span style={{ color: '#d32f2f' }}>*</span></label>
                <textarea
                  value={formData.description}
                  onChange={(e) => handleChange('description', e.target.value)}
                  placeholder="Please describe your message in detail..."
                  rows="4"
                  style={{ ...inputStyle, resize: 'vertical', minHeight: '100px' }}
                />
              </div>

              {error && (
                <div style={{
                  background: 'rgba(244,67,54,0.1)',
                  border: '1px solid rgba(244,67,54,0.3)',
                  borderRadius: '8px',
                  padding: '0.75rem 1rem',
                  color: '#f44336',
                  fontSize: '0.9rem'
                }}>
                  {error}
                </div>
              )}
            </form>
          )}
        </div>

        {/* Footer — always visible */}
        {!success && (
          <div style={{
            padding: '1rem 2rem 1.5rem 2rem',
            borderTop: `1px solid ${COLORS.lightGray}`,
            display: 'flex',
            justifyContent: 'flex-end',
            gap: '0.75rem',
            flexShrink: 0,
            backgroundColor: '#ffffff'
          }}>
            <button
              type="button"
              onClick={handleClose}
              style={{
                padding: '0.65rem 1.25rem',
                background: 'transparent',
                color: COLORS.gray,
                border: `2px solid ${COLORS.lightGray}`,
                borderRadius: '8px',
                fontSize: '0.95rem',
                fontWeight: '600',
                cursor: 'pointer'
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              form="contact-us-form"
              disabled={loading}
              style={{
                padding: '0.65rem 1.5rem',
                background: loading
                  ? '#ccc'
                  : `linear-gradient(135deg, ${COLORS.primaryTeal}, ${COLORS.primaryTealLight || COLORS.primaryTeal})`,
                color: '#ffffff',
                border: 'none',
                borderRadius: '8px',
                fontSize: '0.95rem',
                fontWeight: '600',
                cursor: loading ? 'not-allowed' : 'pointer'
              }}
            >
              {loading ? 'Sending...' : 'Send Message'}
            </button>
          </div>
        )}
      </div>
    </>,
    document.body
  );
};

export default ContactUsModal;