import React from 'react';
import { Insight } from '../types';
import { ChevronUp } from 'lucide-react';

interface IntelligencePanelProps {
  insights: Insight[];
}

export const IntelligencePanel: React.FC<IntelligencePanelProps> = ({ insights }) => {
  return (
    <div
      className="glass-card fade-in-up fade-in-up-2"
      style={{
        padding: '18px 18px',
        display: 'flex',
        flexDirection: 'column',
        gap: 18,
        height: '100%',
      }}
    >
      {/* Title */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span
          style={{
            fontFamily: "'Space Grotesk', sans-serif",
            fontSize: 16,
            fontWeight: 800,
            color: '#f8fafc',
            letterSpacing: '-0.01em',
            textShadow: '0 0 14px rgba(74,222,128,0.16)',
          }}
        >
          Live Intelligence Panel
        </span>
      </div>

      {/* Insights section */}
      <div
        style={{
          background: 'rgba(0,0,0,0.2)',
          borderRadius: 12,
          padding: '12px 14px',
          border: '1px solid rgba(74,222,128,0.06)',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 10,
          }}
        >
          <span
            style={{
              fontSize: 13,
              fontWeight: 700,
              color: '#f8fafc',
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
              textShadow: '0 0 8px rgba(255,255,255,0.06)',
            }}
          >
            System Insights
          </span>
          <ChevronUp size={14} color="rgba(74,222,128,0.5)" />
        </div>

        <p
          style={{
            fontSize: 11,
            color: 'rgba(107,114,128,0.8)',
            lineHeight: 1.6,
            marginBottom: 12,
          }}
        >
          Real-time AI recommendations based on sensor data, consolidated to actionable insights.
        </p>

        <div>
          {insights.map((insight, i) => (
            <div key={i} className="insight-item">
              <div
                className="insight-dot"
                style={{
                  background:
                    insight.type === 'critical'
                      ? '#f87171'
                      : insight.type === 'warning'
                      ? '#fbbf24'
                      : '#4ade80',
                }}
              />
              <span>{insight.message}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
