import React, { useEffect, useRef, useState } from 'react';

interface HealthGaugeProps {
  score: number;
}

function getScoreLabel(score: number): { label: string; color: string; glow: string } {
  if (score >= 85) return { label: 'Excellent', color: '#4ade80', glow: 'rgba(74,222,128,0.5)' };
  if (score >= 70) return { label: 'Healthy', color: '#4ade80', glow: 'rgba(74,222,128,0.4)' };
  if (score >= 50) return { label: 'Warning', color: '#fbbf24', glow: 'rgba(251,191,36,0.4)' };
  return { label: 'Critical', color: '#f87171', glow: 'rgba(248,113,113,0.4)' };
}

// SVG arc path helper
function describeArc(cx: number, cy: number, r: number, startAngle: number, endAngle: number) {
  const toRad = (a: number) => (a * Math.PI) / 180;
  const x1 = cx + r * Math.cos(toRad(startAngle));
  const y1 = cy + r * Math.sin(toRad(startAngle));
  const x2 = cx + r * Math.cos(toRad(endAngle));
  const y2 = cy + r * Math.sin(toRad(endAngle));
  const largeArc = endAngle - startAngle > 180 ? 1 : 0;
  return `M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}`;
}

export const HealthGauge: React.FC<HealthGaugeProps> = ({ score }) => {
  const [displayScore, setDisplayScore] = useState(score);
  const animRef = useRef<number>(0);
  const prevScore = useRef(score);

  useEffect(() => {
    const start = prevScore.current;
    const end = score;
    const duration = 1200;
    const startTime = performance.now();

    cancelAnimationFrame(animRef.current);

    const animate = (now: number) => {
      const progress = Math.min((now - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 4);
      const current = Math.round(start + (end - start) * eased);
      setDisplayScore(current);
      if (progress < 1) {
        animRef.current = requestAnimationFrame(animate);
      } else {
        prevScore.current = end;
      }
    };

    animRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animRef.current);
  }, [score]);

  const { label, color, glow } = getScoreLabel(displayScore);

  // Gauge arc: from 145deg to 395deg (250deg sweep)
  const cx = 110;
  const cy = 110;
  const radius = 85;
  const startAngle = 145;
  const totalSweep = 250;
  const endAngle = startAngle + (displayScore / 100) * totalSweep;

  // Track arc path
  const trackPath = describeArc(cx, cy, radius, startAngle, startAngle + totalSweep);
  const fillPath = describeArc(cx, cy, radius, startAngle, Math.max(startAngle + 0.5, endAngle));

  return (
    <div
      className="glass-card fade-in-up fade-in-up-3"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px 20px 18px',
        position: 'relative',
        overflow: 'hidden',
        minHeight: 280,
      }}
    >
      {/* Title */}
      <div
        style={{
          fontSize: 16,
          fontWeight: 700,
          color: '#e8f5e9',
          letterSpacing: '-0.01em',
          textAlign: 'center',
          marginBottom: 4,
          fontFamily: "'Space Grotesk', sans-serif",
        }}
      >
        Overall Plant Health Score
      </div>

      {/* Background ambient glow */}
      <div
        style={{
          position: 'absolute',
          top: '30%',
          left: '50%',
          transform: 'translateX(-50%)',
          width: 160,
          height: 160,
          borderRadius: '50%',
          background: glow,
          filter: 'blur(50px)',
          opacity: 0.2,
          pointerEvents: 'none',
          transition: 'background 0.8s ease',
        }}
      />

      {/* SVG Gauge */}
      <div style={{ position: 'relative', margin: '8px 0 4px' }}>
        <svg
          width={220}
          height={180}
          viewBox="0 0 220 180"
          style={{ overflow: 'visible' }}
        >
          <defs>
            <linearGradient id="gauge-grad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#16a34a" />
              <stop offset="50%" stopColor="#22c55e" />
              <stop offset="100%" stopColor="#4ade80" />
            </linearGradient>
            <filter id="gauge-glow">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Outer decorative ring */}
          <circle
            cx={cx} cy={cy} r={98}
            fill="none"
            stroke="rgba(74,222,128,0.04)"
            strokeWidth="1"
          />

          {/* Track (background arc) */}
          <path
            d={trackPath}
            fill="none"
            stroke="rgba(74,222,128,0.08)"
            strokeWidth="12"
            strokeLinecap="round"
          />

          {/* Inner track shadow */}
          <path
            d={trackPath}
            fill="none"
            stroke="rgba(0,0,0,0.3)"
            strokeWidth="14"
            strokeLinecap="round"
            style={{ opacity: 0.4 }}
          />

          {/* Filled arc */}
          <path
            d={fillPath}
            fill="none"
            stroke="url(#gauge-grad)"
            strokeWidth="12"
            strokeLinecap="round"
            filter="url(#gauge-glow)"
            style={{ transition: 'd 0.8s ease' }}
          />

          {/* Glowing tip dot */}
          {displayScore > 1 && (() => {
            const tipAngle = ((startAngle + (displayScore / 100) * totalSweep) * Math.PI) / 180;
            const tipX = cx + radius * Math.cos(tipAngle);
            const tipY = cy + radius * Math.sin(tipAngle);
            return (
              <g>
                <circle cx={tipX} cy={tipY} r={8} fill={color} opacity={0.2} />
                <circle cx={tipX} cy={tipY} r={5} fill={color} opacity={0.6} />
                <circle cx={tipX} cy={tipY} r={3} fill={color} />
              </g>
            );
          })()}

          {/* Center content */}
          {/* Score number */}
          <text
            x={cx}
            y={cy + 8}
            textAnchor="middle"
            fill={color}
            fontSize="44"
            fontWeight="800"
            fontFamily="'Space Grotesk', sans-serif"
            style={{
              textShadow: `0 0 30px ${glow}`,
              transition: 'fill 0.5s ease',
            }}
            filter="url(#gauge-glow)"
          >
            {displayScore}
          </text>

          {/* Inner decorative ring */}
          <circle
            cx={cx} cy={cy} r={66}
            fill="rgba(0,0,0,0.15)"
            stroke="rgba(74,222,128,0.06)"
            strokeWidth="1"
          />
        </svg>

        {/* Status badge centered below score */}
        <div
          style={{
            position: 'absolute',
            bottom: -2,
            left: '50%',
            transform: 'translateX(-50%)',
            background: `rgba(${color === '#4ade80' ? '74,222,128' : color === '#fbbf24' ? '251,191,36' : '248,113,113'},0.15)`,
            border: `1px solid ${color}40`,
            borderRadius: 999,
            padding: '3px 18px',
            fontSize: 12,
            fontWeight: 700,
            color: color,
            letterSpacing: '0.08em',
            textTransform: 'uppercase' as const,
            whiteSpace: 'nowrap' as const,
            transition: 'all 0.5s ease',
          }}
        >
          {label}
        </div>
      </div>

      {/* Subtitle */}
      <div
        style={{
          fontSize: 11.5,
          color: 'rgba(156,163,175,0.6)',
          marginTop: 20,
          textAlign: 'center',
          letterSpacing: '0.03em',
        }}
      >
        Overall Plant Health Score
        <br />
        <span style={{ fontSize: 10.5, opacity: 0.7 }}>Derived from all sensor inputs</span>
      </div>
    </div>
  );
};
