import React from 'react';
import StakeholderCard from './StakeholderCard.jsx';
import { COLORS } from '../utils/constants.js';

const StakeholderSection = ({ 
  stakeholders, 
  stageColors, 
  isDarkTheme = false 
}) => {
  // Split stakeholders by arrow separator
  const stakeholderList = stakeholders.split('\n').map(s => s.trim()).filter(s => s);

  const normalizeText = (value = '') => value
    .toLowerCase()
    .replace(/&/g, ' and ')
    .replace(/[^a-z0-9\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  const parseStakeholderRole = (stakeholderText = '') => {
    const cleaned = (stakeholderText || '')
      .replace(/\u2013|\u2014/g, ' - ')
      .replace(/\u2022/g, ' ')
      .replace(/\s*[-:\u2013\u2014]\s*/g, ' - ')
      .split(' - ')[0]
      .trim();

    return cleaned
      .replace(/\//g, ' ')
      .replace(/&/g, ' and ')
      .replace(/[^a-zA-Z0-9\s]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  };

  const iconAliases = [
    { keywords: ['patient', 'general population', 'survivor'], file: 'Patients' },
    { keywords: ['family', 'caregiver', 'caregivers'], file: 'FamilyCaregivers' },
    { keywords: ['general practitioner', 'primary care physician', 'gp', 'family doctor', 'physician'], file: 'General Practitioner' },
    { keywords: ['pulmonologist', 'respiratory specialist', 'lung specialist'], file: 'General Practitioner' },
    { keywords: ['medical oncologist', 'oncologist', 'radiation oncologist'], file: 'General Practitioner' },
    { keywords: ['radiologist', 'imaging', 'ct', 'mri'], file: 'Radiologists' },
    { keywords: ['pathologist', 'molecular pathologist', 'molecular diagnostics laboratory', 'laboratory', 'lab'], file: 'Lab Specialists' },
    { keywords: ['thoracic surgeon', 'surgeon'], file: 'Cardiac Surgeons' },
    { keywords: ['nurse', 'nursing'], file: 'Nurse' },
    { keywords: ['pharmacist', 'medication adherence'], file: 'Pharmacists' },
    { keywords: ['dietitian', 'nutritionist', 'dietician'], file: 'Dietitionist' },
    { keywords: ['psychologist', 'mental health', 'counselor', 'counsellor'], file: 'Mental Health Professional' },
    { keywords: ['rehabilitation therapist', 'physiotherapist', 'occupational therapist', 'vocational counselor', 'rehab'], file: 'Rehab Specialists Physiotherapists' },
    { keywords: ['medical device', 'medtech', 'technology provider', 'diagnostics company'], file: 'MedTech Companies' },
    { keywords: ['digital health provider', 'digital health', 'telemedicine', 'virtual follow up', 'telehealth'], file: 'Digital Health Providers' },
    { keywords: ['ministry', 'government', 'public health'], file: 'Government health agencies' },
    { keywords: ['emergency physician', 'emergency'], file: 'Emergency Physicians' },
    { keywords: ['paramedic'], file: 'Paramedics' },
    { keywords: ['community organization', 'ngo', 'support group'], file: 'Community organizations' },
    { keywords: ['insurance', 'payer', 'insurer'], file: 'Insurance Companies' },
    { keywords: ['pharma', 'pharmaceutical'], file: 'Pharma Companies' },
    { keywords: ['public health authority', 'health agency'], file: 'Public Health Authorities' },
    { keywords: ['interventional radiologist'], file: 'Radiologists' },
    { keywords: ['primary care physician', 'primary care'], file: 'General Practitioner' },
    { keywords: ['remote symptom reporting', 'mobile app', 'digital symptom tracking'], file: 'Digital Health Providers' }
  ];

  const getStakeholderImage = (stakeholderText) => {
    const text = stakeholderText || '';
    const normalizedText = normalizeText(text);
    const roleMatch = parseStakeholderRole(text);
    const roleKey = normalizeText(roleMatch);

    const directMatches = {
      'patient': 'Patients',
      'family': 'FamilyCaregivers',
      'general practitioner': 'General Practitioner',
      'pulmonologist': 'General Practitioner',
      'medical oncologist': 'General Practitioner',
      'radiation oncologist': 'General Practitioner',
      'radiologist': 'Radiologists',
      'pathologist': 'Lab Specialists',
      'molecular pathologist': 'Lab Specialists',
      'molecular diagnostics laboratory': 'Lab Specialists',
      'thoracic surgeon': 'Cardiac Surgeons',
      'interventional radiologist': 'Radiologists',
      'nurse': 'Nurse',
      'pharmacist': 'Pharmacists',
      'nutritionist': 'Dietitionist',
      'psychologist': 'Mental Health Professional',
      'rehabilitation therapist': 'Rehab Specialists Physiotherapists',
      'occupational therapist': 'Rehab Specialists Physiotherapists',
      'medical device companies': 'MedTech Companies',
      'medtech and digital health companies': 'Digital Health Providers',
      'digital health provider': 'Digital Health Providers',
      'telemedicine provider': 'Digital Health Providers',
      'ministry of health': 'Government health agencies',
      'primary care physician': 'General Practitioner',
      'family doctor': 'General Practitioner',
      'caregiver': 'FamilyCaregivers'
    };

    if (directMatches[roleKey]) {
      return `/Stakeholders/${encodeURIComponent(directMatches[roleKey])}.png`;
    }

    for (const alias of iconAliases) {
      if (alias.keywords.some(keyword => normalizedText.includes(normalizeText(keyword)))) {
        return `/Stakeholders/${encodeURIComponent(alias.file)}.png`;
      }
    }

    return '/Stakeholders/General%20Practitioner.png';
  };

  const uniqueStakeholderList = [];
  const seenIconPaths = new Set();

  stakeholderList.forEach((stakeholder) => {
    const imagePath = getStakeholderImage(stakeholder);
    if (!seenIconPaths.has(imagePath)) {
      seenIconPaths.add(imagePath);
      uniqueStakeholderList.push({ stakeholder, imagePath });
    }
  });

  return (
    <div>
      <h3 style={{
        color: COLORS.white,
        fontSize: '1.2rem',
        fontWeight: '600',
        marginBottom: '1rem',
        textAlign: 'center',
        textShadow: `0 0 10px ${stageColors?.primary || COLORS.primaryTeal}40`
      }}>
        Key Stakeholders
      </h3>
      
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: '1rem',
        maxWidth: '1000px',
        margin: '0 auto'
      }}>
        {uniqueStakeholderList.map(({ stakeholder, imagePath }, index) => (
          <StakeholderCard
            key={`${stakeholder}-${index}`}
            stakeholder={stakeholder}
            index={index}
            imagePath={imagePath}
            stageColors={stageColors}
            isDarkTheme={isDarkTheme}
          />
        ))}
      </div>
    </div>
  );
};

export default StakeholderSection;
