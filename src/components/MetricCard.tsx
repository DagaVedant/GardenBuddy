import React, { useRef, useEffect, useState } from 'react';
import { SensorStatus } from '../types';

interface MetricCardProps {
  title: string;
  value: number;
  unit: string;
  status: SensorStatus;
  iconBg: string;
  trendData: number[];
  trendColor: string;
  glowClass?: string;
  animDelay?: string;
}

function statusLabel(status: SensorStatus): string {
  if (status === 'optimal') return 'Optimal';
  if (status === 'warning') return 'Warning';
  if (status === 'critical') return 'Critical';
  if (status === 'moist') return 'Moist';
  return 'Unknown';
}

function MiniSparkline({ data, color }: { data: number[]; color: string }) {
  if (!data || data.length < 2) return null;

  const w = 80;
  const h = 28;
  const pad = 3;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  const points = data.map((v, i) => {
    const x = pad + (i / (data.length - 1)) * (w - pad * 2);
    const y = h - pad - ((v - min) / range) * (h - pad * 2);
    return `${x},${y}`;
  });

  const pathD = `M ${points.join(' L ')}`;

  const areaD = `M ${points[0]} L ${points.join(' L ')} L ${w - pad},${h - pad} L ${pad},${h - pad} Z`;

  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} style={{ overflow: 'visible' }}>
      <defs>
        <linearGradient id={`sg-${color.replace('#', '')}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.25" />
          <stop offset="100%" stopColor={color} stopOpacity="0.02" />
        </linearGradient>
      </defs>
      <path d={areaD} fill={`url(#sg-${color.replace('#', '')})`} />
      <path d={pathD} stroke={color} strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <circle
        cx={parseFloat(points[points.length - 1].split(',')[0])}
        cy={parseFloat(points[points.length - 1].split(',')[1])}
        r="2.5"
        fill={color}
      />
    </svg>
  );
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  unit,
  status,
  iconBg,
  trendData,
  trendColor,
  glowClass,
  animDelay,
}) => {
  const [displayValue, setDisplayValue] = useState(value);
  const prevValue = useRef(value);
  const [flashing, setFlashing] = useState(false);

  useEffect(() => {
    if (value !== prevValue.current) {
      setFlashing(true);
      const t = setTimeout(() => setFlashing(false), 400);
      prevValue.current = value;
      const start = displayValue;
      const end = value;
      const duration = 600;
      const startTime = performance.now();
      const animate = (now: number) => {
        const progress = Math.min((now - startTime) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        setDisplayValue(parseFloat((start + (end - start) * eased).toFixed(1)));
        if (progress < 1) requestAnimationFrame(animate);
      };
      requestAnimationFrame(animate);
      return () => clearTimeout(t);
    }
  }, [value]);

  const statusClass =
    status === 'optimal' ? 'status-optimal' :
    status === 'warning' ? 'status-warning' :
    status === 'critical' ? 'status-critical' :
    'status-moist';

  return (
    <div
      className={`glass-card ${glowClass || 'glow-green'} fade-in-up ${animDelay || ''}`}
      style={{ padding: '18px 20px', position: 'relative', overflow: 'hidden' }}
    >
      <div
        style={{
          position: 'absolute',
          top: -20,
          right: -20,
          width: 80,
          height: 80,
          borderRadius: '50%',
          background: iconBg,
          filter: 'blur(30px)',
          opacity: 0.4,
          pointerEvents: 'none',
        }}
      />

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <span
          style={{
            fontSize: 15,
            fontWeight: 700,
            color: '#f8fafc',
            letterSpacing: '0.03em',
            textShadow: '0 0 10px rgba(255,255,255,0.08)',
          }}
        >
          {title}
        </span>
      </div>

      <div
        className={`metric-value ${flashing ? 'flash-update' : ''}`}
        style={{ fontSize: 34, color: '#f0fdf4', marginBottom: 8 }}
      >
        {displayValue.toFixed(1)}
        <span
          style={{
            fontSize: 17,
            fontWeight: 500,
            color: 'rgba(232, 245, 233, 0.6)',
            marginLeft: 3,
          }}
        >
          {unit}
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span className={`status-badge ${statusClass}`}>{statusLabel(status)}</span>
        <MiniSparkline data={trendData.slice(-12)} color={trendColor} />
      </div>
    </div>
  );
};