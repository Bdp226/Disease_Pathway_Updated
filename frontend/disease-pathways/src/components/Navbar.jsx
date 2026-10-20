import React, { useState, useRef, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { MdHealthAndSafety, MdExpandMore, MdLogout, MdAdminPanelSettings } from 'react-icons/md';
import { COLORS } from '../utils/constants.js';
import { authAPI, isAuthenticated, getCurrentUser, isAdmin } from '../utils/api.js';
import ContactUsModal from './ContactUsModal';
import GlobalSearch from './GlobalSearch';

const Navbar = ({ isHome }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [user, setUser] = useState(getCurrentUser());
  const [authenticated, setAuthenticated] = useState(isAuthenticated());
  const menuRef = useRef(null);

  const isActive = (path) => location.pathname === path;
  const [isContactModalOpen, setIsContactModalOpen] = useState(false);
  const [isScrolled, setIsScrolled] = useState(false);
  const [isHoveringTop, setIsHoveringTop] = useState(false);

  useEffect(() => {
    const updateAuthState = () => {
      setUser(getCurrentUser());
      setAuthenticated(isAuthenticated());
    };

    const handleStorageChange = (e) => {
      if (e.key === 'disease_pathway_token' || e.key === 'disease_pathway_user') {
        updateAuthState();
      }
    };

    window.addEventListener('storage', handleStorageChange);
    updateAuthState();

    return () => {
      window.removeEventListener('storage', handleStorageChange);
    };
  }, []);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setShowUserMenu(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  useEffect(() => {
    if (!isHome) return;

    const handleScroll = () => {
      // If we've scrolled more than 50px, we consider the nav "out of view"
      setIsScrolled(window.scrollY > 50);
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, [isHome]);

  const shouldShow = !isHome || !isScrolled || isHoveringTop;

  const triggerZoneStyle = {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    height: '20px',
    zIndex: 1099,
    background: 'transparent',
    display: isHome && isScrolled ? 'block' : 'none' 
  };

  const handleLogout = () => {
    authAPI.logout();
    setUser(null);
    setAuthenticated(false);
    setShowUserMenu(false);
    navigate('/login', { replace: true });
  };

  const navColors = {
    bg: 'rgba(8, 12, 16, 0.96)',
    border: 'rgba(255, 255, 255, 0.16)',
    text: '#d5e1ea',
    textStrong: '#f3f8fc'
  };

  const navLinkStyle = (path) => ({
    color: isActive(path) ? COLORS.accentOrange : navColors.text,
    textDecoration: 'none',
    fontSize: '0.92rem',
    letterSpacing: '0.02em',
    fontWeight: '650',
    transition: 'all 0.3s ease',
    borderBottom: isActive(path) ? `2px solid ${COLORS.accentOrange}` : 'none',
    paddingBottom: '0.25rem'
  });

  return (
    <>

      {/* Invisible trigger only active when nav is scrolled away */}
      <div 
        style={triggerZoneStyle} 
        onMouseEnter={() => setIsHoveringTop(true)} 
      />

      <nav
        onMouseLeave={() => setIsHoveringTop(false)}
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          zIndex: 1100,
          padding: '1rem 2.5rem',
          background: navColors.bg,
          borderBottom: `1px solid ${navColors.border}`,
          boxShadow: shouldShow ? '0 14px 36px rgba(0, 0, 0, 0.45), inset 0 -1px 0 rgba(255, 255, 255, 0.06)' : 'none',
          backdropFilter: 'blur(16px)',
          
          // Animation logic
          transform: shouldShow ? 'translateY(0)' : 'translateY(-100%)',
          opacity: shouldShow ? 1 : 0,
          transition: 'transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.3s ease',
          pointerEvents: shouldShow ? 'auto' : 'none'
        }}
      >
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          maxWidth: '1300px',
          margin: '0 auto'
        }}>
          {/* Logo/Brand */}
          <Link 
            to="/" 
            style={{
              fontSize: '1.8rem',
              fontWeight: 'bold',
              textDecoration: 'none',
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem'
            }}
          >
            <img 
              src="/logo.png" 
              alt="Logo" 
              style={{
                height: '40px',
                width: 'auto'
              }}
            />
          </Link>

          {/* Navigation Links + Search */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '2.2rem'
          }}>
            {/* Global Semantic Search */}
            <GlobalSearch isDarkTheme={true} />
            <Link
              to="/"
              style={navLinkStyle('/')}
              onMouseEnter={(e) => {
                const t = e.currentTarget;
                t.style.color = COLORS.accentOrange;
                t.style.borderBottom = `2px solid ${COLORS.accentOrange}`;
              }}
              onMouseLeave={(e) => {
                const t = e.currentTarget;
                if (isActive('/')) {
                  t.style.color = COLORS.accentOrange;
                  t.style.borderBottom = `2px solid ${COLORS.accentOrange}`;
                } else {
                  t.style.color = navColors.text;
                  t.style.borderBottom = 'none';
                }
              }}
            >
              About
            </Link>

            <Link
              to="/diseases"
              style={navLinkStyle('/diseases')}
              onMouseEnter={(e) => {
                const t = e.currentTarget;
                t.style.color = COLORS.accentOrange;
                t.style.borderBottom = `2px solid ${COLORS.accentOrange}`;
              }}
              onMouseLeave={(e) => {
                const t = e.currentTarget;
                if (isActive('/diseases')) {
                  t.style.color = COLORS.accentOrange;
                  t.style.borderBottom = `2px solid ${COLORS.accentOrange}`;
                } else {
                  t.style.color = navColors.text;
                  t.style.borderBottom = 'none';
                }
              }}
            >
              Diseases
            </Link>

            {authenticated && isAdmin() && (
              <Link
                to="/admin"
                style={navLinkStyle('/admin')}
                onMouseEnter={(e) => {
                  const t = e.currentTarget;
                  t.style.color = COLORS.accentOrange;
                  t.style.borderBottom = `2px solid ${COLORS.accentOrange}`;
                }}
                onMouseLeave={(e) => {
                  const t = e.currentTarget;
                  if (isActive('/admin')) {
                    t.style.color = COLORS.accentOrange;
                    t.style.borderBottom = `2px solid ${COLORS.accentOrange}`;
                  } else {
                    t.style.color = navColors.text;
                    t.style.borderBottom = 'none';
                  }
                }}
              >
                Dashboard
              </Link>
            )}

            <button
              onClick={() => setIsContactModalOpen(true)}
              style={{
                background: 'none',
                border: 'none',
                color: isContactModalOpen ? COLORS.accentOrange : navColors.text,
                textDecoration: 'none',
                fontSize: '0.92rem',
                fontWeight: '650',
                letterSpacing: '0.02em',
                transition: 'all 0.3s ease',
                paddingBottom: '0.25rem',
                borderBottom: isContactModalOpen ? `2px solid ${COLORS.accentOrange}` : 'none',
                cursor: 'pointer'
              }}
              onMouseEnter={(e) => {
                const t = e.currentTarget;
                if (!isContactModalOpen) {
                  t.style.color = COLORS.accentOrange;
                  t.style.borderBottom = `2px solid ${COLORS.accentOrange}`;
                }
              }}
              onMouseLeave={(e) => {
                const t = e.currentTarget;
                if (!isContactModalOpen) {
                  t.style.color = navColors.text;
                  t.style.borderBottom = 'none';
                }
              }}
            >
              Contact Us
            </button>

            {/* Authentication Section */}
            <div style={{ position: 'relative' }}>
              {authenticated ? (
                <div ref={menuRef}>
                  <div 
                    onClick={() => setShowUserMenu(!showUserMenu)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.75rem',
                      cursor: 'pointer',
                      padding: '0.4rem 0.8rem',
                      borderRadius: '12px',
                      background: showUserMenu ? 'rgba(236, 103, 2, 0.1)' : 'transparent',
                      transition: 'background 0.3s ease'
                    }}
                  >
                    <div style={{
                      width: '32px',
                      height: '32px',
                      borderRadius: '50%',
                      background: isAdmin() ? 
                        `linear-gradient(135deg, ${COLORS.accentOrange}, ${COLORS.accentOrangeLight})` :
                        `linear-gradient(135deg, ${COLORS.primaryTeal}, ${COLORS.primaryTealLight})`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: COLORS.white,
                      fontSize: '1rem'
                    }}>
                      {isAdmin() ? <MdAdminPanelSettings /> : <MdHealthAndSafety />}
                    </div>
                    
                    <span style={{ 
                      color: navColors.textStrong, 
                      fontSize: '0.9rem', 
                      fontWeight: '600' 
                    }}>
                      {user?.full_name?.split(' ')[0]}
                    </span>
                    
                    <MdExpandMore style={{ 
                      color: navColors.text,
                      transform: showUserMenu ? 'rotate(180deg)' : 'rotate(0deg)',
                      transition: 'transform 0.3s ease'
                    }} />
                  </div>

                  {showUserMenu && (
                    <div style={{
                      position: 'absolute',
                      top: '110%',
                      right: 0,
                      minWidth: '220px',
                      background: '#111821',
                      borderRadius: '12px',
                      boxShadow: '0 18px 40px rgba(0,0,0,0.35)',
                      border: '1px solid rgba(255,255,255,0.1)',
                      overflow: 'hidden'
                    }}>
                      <div style={{ 
                        padding: '1rem', 
                        borderBottom: '1px solid rgba(255,255,255,0.08)',
                        background: 'rgba(236, 103, 2, 0.08)'
                      }}>
                        <div style={{ color: '#f0f6fb', fontSize: '0.9rem', fontWeight: '700' }}>{user?.full_name}</div>
                        <div style={{ color: '#9fb0be', fontSize: '0.75rem', opacity: 0.9 }}>{user?.email}</div>
                      </div>
                      <div 
                        onClick={handleLogout}
                        style={{
                          padding: '0.8rem 1rem',
                          color: '#c8d4de',
                          fontSize: '0.9rem',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.75rem',
                          transition: 'background 0.2s ease'
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(236, 103, 2, 0.1)'}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                      >
                        <MdLogout /> Sign Out
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <Link
                  to="/login"
                  style={{
                    padding: '0.6rem 1.4rem',
                    background: `linear-gradient(135deg, ${COLORS.primaryTeal}, ${COLORS.primaryTealLight})`,
                    color: COLORS.white,
                    textDecoration: 'none',
                    borderRadius: '10px',
                    fontSize: '0.9rem',
                    fontWeight: '700',
                    boxShadow: `0 10px 24px ${COLORS.primaryTeal}44`
                  }}
                >
                  Sign In
                </Link>
              )}
            </div>
          </div>
        </div>
      </nav>

      <ContactUsModal 
        isOpen={isContactModalOpen}
        onClose={() => setIsContactModalOpen(false)}
      />
    </>
  );
};

export default Navbar;