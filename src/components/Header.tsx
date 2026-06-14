import React from 'react';

export const Header: React.FC = () => {

  return (
    <header
      className="header-border"
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '14px 24px',
        background: 'rgba(8, 14, 8, 0.9)',
        backdropFilter: 'blur(20px)',
        position: 'sticky',
        top: 0,
        zIndex: 40,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span
          style={{
            fontSize: 15,
            fontWeight: 600,
            color: '#d1fae5',
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            textShadow: '0 0 8px rgba(255,255,255,0.08)',
          }}
        >
          Dashboard
        </span>
      </div>

      <div style={{ position: 'absolute', left: '50%', transform: 'translateX(-50%)', textAlign: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 4, justifyContent: 'center' }}>
          <span
            style={{
              fontFamily: "'Space Grotesk', sans-serif",
              fontSize: 36,
              fontWeight: 800,
              color: '#f0fdf4',
              letterSpacing: '-0.02em',
              textShadow: '0 0 16px rgba(255,255,255,0.18)',
            }}
          >
            Garden
          </span>
          <span
            style={{
              fontFamily: "'Space Grotesk', sans-serif",
              fontSize: 36,
              fontWeight: 800,
              color: '#4ade80',
              letterSpacing: '-0.02em',
              textShadow: '0 0 18px rgba(74,222,128,0.28)',
            }}
          >
            Buddy
          </span>
        </div>
      </div>
    </header>
  );
};
