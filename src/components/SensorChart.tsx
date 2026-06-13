import React, { useRef, useEffect } from 'react';

import {
  Chart,
  LineController,
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Tooltip,
  Filler,
  ChartOptions,
  ChartData,
} from 'chart.js';

Chart.register(LineController, LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Filler);

interface SensorChartProps {
  title: string;
  labels: string[];
  data: number[];
  unit: string;
  color: string;
  glowColor: string;
  animDelay?: string;
  moreOptionsId?: string;
}

export const SensorChart: React.FC<SensorChartProps> = ({
  title,
  labels,
  data,
  unit,
  color,
  glowColor,
  animDelay,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartRef = useRef<Chart | null>(null);

  useEffect(() => {
    if (!canvasRef.current) return;

    const ctx = canvasRef.current.getContext('2d');
    if (!ctx) return;

    const toAlpha = (rgba: string, a: number) => rgba.replace(/[\d.]+\)$/, `${a})`);
    const gradient = ctx.createLinearGradient(0, 0, 0, 120);
    gradient.addColorStop(0, toAlpha(glowColor, 0.35));
    gradient.addColorStop(0.6, toAlpha(glowColor, 0.08));
    gradient.addColorStop(1, 'rgba(0,0,0,0)');

    const chartData: ChartData<'line'> = {
      labels: labels.length ? labels : [''],
      datasets: [
        {
          data: data.length ? data : [0],
          borderColor: color,
          borderWidth: 2,
          backgroundColor: gradient,
          fill: true,
          tension: 0.45,
          pointRadius: (ctx2) => (ctx2.dataIndex === data.length - 1 ? 4 : 0),
          pointHoverRadius: 5,
          pointBackgroundColor: color,
          pointBorderColor: 'rgba(0,0,0,0.5)',
          pointBorderWidth: 1.5,
        },
      ],
    };

    const options: ChartOptions<'line'> = {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 600, easing: 'easeInOutQuart' },
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          enabled: true,
          backgroundColor: 'rgba(10,18,10,0.92)',
          titleColor: 'rgba(156,163,175,0.8)',
          bodyColor: '#e8f5e9',
          borderColor: color,
          borderWidth: 1,
          padding: 10,
          cornerRadius: 8,
          displayColors: true,
          callbacks: {
            label: (item) => ` ${item.formattedValue}${unit}`,
          },
        },
      },
      scales: {
        x: {
          grid: { color: 'rgba(74,222,128,0.04)', drawTicks: false },
          border: { display: false },
          ticks: {
            color: 'rgba(107,114,128,0.7)',
            font: { size: 9, family: 'Inter' },
            maxRotation: 0,
            maxTicksLimit: 6,
            padding: 4,
          },
        },
        y: {
          grid: { color: 'rgba(74,222,128,0.04)', drawTicks: false },
          border: { display: false },
          ticks: {
            color: 'rgba(107,114,128,0.7)',
            font: { size: 9, family: 'Inter' },
            padding: 6,
            maxTicksLimit: 5,
            callback: (val) => `${val}${unit}`,
          },
        },
      },
    };

    if (chartRef.current) {
      // Update existing chart in place — no destroy/recreate flicker
      chartRef.current.data = chartData;
      chartRef.current.options = options;
      chartRef.current.update('none');
    } else {
      chartRef.current = new Chart(ctx, { type: 'line', data: chartData, options });
    }
  }, [data, labels, color, glowColor, unit]);

  // Destroy only on unmount
  useEffect(() => {
    return () => {
      chartRef.current?.destroy();
      chartRef.current = null;
    };
  }, []);

  return (
    <div
      className={`glass-card fade-in-up ${animDelay || ''}`}
      style={{ padding: '16px 18px', position: 'relative', overflow: 'hidden' }}
    >
      <div
        style={{
          position: 'absolute',
          bottom: 0,
          left: '50%',
          transform: 'translateX(-50%)',
          width: '70%',
          height: 60,
          background: glowColor,
          filter: 'blur(30px)',
          opacity: 0.08,
          pointerEvents: 'none',
        }}
      />

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
        <span className="chart-title">{title}</span>
        <div style={{ display: 'flex', gap: 3 }}>
          {[1, 2, 3].map(i => (
            <div key={i} style={{ width: 4, height: 4, borderRadius: '50%', background: 'rgba(107,114,128,0.5)' }} />
          ))}
        </div>
      </div>

      <div className="chart-container" style={{ height: 120 }}>
        <canvas ref={canvasRef} />
      </div>
    </div>
  );
};