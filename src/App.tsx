import { Leaf } from 'lucide-react';

import { useSensorData } from './hooks/useSensorData';
import { getTempStatus, getHumidityStatus, getSoilStatus, getLightStatus } from './utils/sensorHelpers';

import { Header } from './components/Header';
import { MetricCard } from './components/MetricCard';
import { HealthGauge } from './components/HealthGauge';
import { SensorChart } from './components/SensorChart';
import { IntelligencePanel } from './components/IntelligencePanel';

const CHART_CONFIGS = {
  temperature: { color: '#fb923c', glow: 'rgba(251,146,60,0.8)', unit: 'F', title: 'Temperature Chart (30m)' },
  humidity: { color: '#38bdf8', glow: 'rgba(56,189,248,0.8)', unit: '%', title: 'Humidity Chart (30m)' },
  soil: { color: '#4ade80', glow: 'rgba(74,222,128,0.8)', unit: '%', title: 'Soil Moisture Chart (30m)' },
  light: { color: '#fbbf24', glow: 'rgba(251,191,36,0.8)', unit: '%', title: 'Light Level Chart (30m)' },
};

function SkeletonCard({ h = 140 }: { h?: number }) {
  return <div className="glass-card shimmer" style={{ minHeight: h }} />;
}

export default function App() {
  const { data, loading } = useSensorData();
  const insights = data?.insights ?? [];

  return (
    <div
      className="botanical-bg"
      style={{
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #050905 0%, #07100a 40%, #080f08 70%, #060a06 100%)',
        display: 'flex',
        fontFamily: "'Inter', sans-serif",
      }}
    >
      <div
        style={{
          marginLeft: 0,
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          minHeight: '100vh',
          position: 'relative',
          zIndex: 1,
        }}
      >
        <Header/>

        <main style={{ padding: '14px 18px 20px', flex: 1 }}>
          {loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1.7fr 1fr 1fr', gap: 12 }}>
                {[...Array(5)].map((_, i) => <SkeletonCard key={i} h={i === 2 ? 300 : 140} />)}
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr 1.1fr', gap: 12 }}>
                {[...Array(5)].map((_, i) => <SkeletonCard key={i} h={160} />)}
              </div>
            </div>
          ) : data ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1.72fr 1fr 1fr', gap: 12, alignItems: 'stretch' }}>
                <MetricCard
                  title="Temperature"
                  value={data.temp}
                  unit="F"
                  status={getTempStatus(data.temp)}
                  iconBg="rgba(251,146,60,0.15)"
                  trendData={data.chart.temperature_f}
                  trendColor="#fb923c"
                  glowClass="glow-amber"
                  animDelay="fade-in-up-1"
                />
                <MetricCard
                  title="Humidity"
                  value={data.humidity}
                  unit="%"
                  status={getHumidityStatus(data.humidity)}
                  iconBg="rgba(56,189,248,0.15)"
                  trendData={data.chart.humidity}
                  trendColor="#38bdf8"
                  glowClass="glow-blue"
                  animDelay="fade-in-up-2"
                />
                <HealthGauge score={data.score} />
                <MetricCard
                  title="Soil Moisture"
                  value={data.soil}
                  unit="%"
                  status={getSoilStatus(data.soil)}
                  iconBg="rgba(74,222,128,0.15)"
                  trendData={data.chart.soil_moisture_percent}
                  trendColor="#4ade80"
                  glowClass="glow-green"
                  animDelay="fade-in-up-4"
                />
                <MetricCard
                  title="Light Level"
                  value={data.light}
                  unit="%"
                  status={getLightStatus(data.light)}
                  iconBg="rgba(251,191,36,0.15)"
                  trendData={data.chart.light_percent}
                  trendColor="#fbbf24"
                  glowClass="glow-amber"
                  animDelay="fade-in-up-5"
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr 1.08fr', gap: 12, alignItems: 'stretch' }}>
                <SensorChart
                  title={CHART_CONFIGS.temperature.title}
                  labels={data.chart.time}
                  data={data.chart.temperature_f}
                  unit={CHART_CONFIGS.temperature.unit}
                  color={CHART_CONFIGS.temperature.color}
                  glowColor={CHART_CONFIGS.temperature.glow}
                  animDelay="fade-in-up-6"
                />
                <SensorChart
                  title={CHART_CONFIGS.humidity.title}
                  labels={data.chart.time}
                  data={data.chart.humidity}
                  unit={CHART_CONFIGS.humidity.unit}
                  color={CHART_CONFIGS.humidity.color}
                  glowColor={CHART_CONFIGS.humidity.glow}
                  animDelay="fade-in-up-7"
                />
                <SensorChart
                  title={CHART_CONFIGS.soil.title}
                  labels={data.chart.time}
                  data={data.chart.soil_moisture_percent}
                  unit={CHART_CONFIGS.soil.unit}
                  color={CHART_CONFIGS.soil.color}
                  glowColor={CHART_CONFIGS.soil.glow}
                  animDelay="fade-in-up-7"
                />
                <SensorChart
                  title={CHART_CONFIGS.light.title}
                  labels={data.chart.time}
                  data={data.chart.light_percent}
                  unit={CHART_CONFIGS.light.unit}
                  color={CHART_CONFIGS.light.color}
                  glowColor={CHART_CONFIGS.light.glow}
                  animDelay="fade-in-up-8"
                />
                <IntelligencePanel insights={insights} />
              </div>

              <div
                className="glass-card fade-in-up fade-in-up-9"
                style={{ padding: '14px 20px', display: 'flex', alignItems: 'center', gap: 24 }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 20, fontWeight: 700, color: '#f8fafc', letterSpacing: '0.06em', textTransform: 'uppercase', textShadow: '0 0 8px rgba(255,255,255,0.06)' }}>
                    System Overview
                  </span>
                </div>

                <div style={{ flex: 1, display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
                  {[
                    { label: 'Temperature', value: `${data.temp.toFixed(1)}F`, color: '#fb923c', pct: Math.max(0, Math.min(100, ((data.temp - 50) / 50) * 100)) },
                    { label: 'Humidity', value: `${data.humidity.toFixed(1)}%`, color: '#38bdf8', pct: data.humidity },
                    { label: 'Soil Moisture', value: `${data.soil.toFixed(1)}%`, color: '#4ade80', pct: data.soil },
                    { label: 'Light Level', value: `${data.light.toFixed(1)}%`, color: '#fbbf24', pct: data.light },
                  ].map(({ label, value, color, pct }) => (
                    <div key={label}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
                        <span style={{ fontSize: 11, color: 'rgba(107,114,128,0.9)' }}>{label}</span>
                        <span style={{ fontSize: 11, color, fontWeight: 600 }}>{value}</span>
                      </div>
                      <div style={{ height: 3, borderRadius: 2, background: 'rgba(255,255,255,0.04)', overflow: 'hidden' }}>
                        <div
                          style={{
                            height: '100%',
                            width: `${pct}%`,
                            background: `linear-gradient(90deg, ${color}66, ${color})`,
                            borderRadius: 2,
                            transition: 'width 1s cubic-bezier(0.4,0,0.2,1)',
                            boxShadow: `0 0 6px ${color}50`,
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>

                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    padding: '6px 20px',
                    background: 'rgba(74,222,128,0.07)',
                    borderRadius: 10,
                    border: '1px solid rgba(74,222,128,0.15)',
                    minWidth: 90,
                  }}
                >
                  <span style={{ fontSize: 10, color: 'rgba(107,114,128,0.8)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Health</span>
                  <span style={{ fontSize: 26, fontWeight: 800, color: '#4ade80', fontFamily: "'Space Grotesk', sans-serif", lineHeight: 1.1, textShadow: '0 0 16px rgba(74,222,128,0.5)' }}>
                    {data.score}
                  </span>
                  <span style={{ fontSize: 9, color: 'rgba(74,222,128,0.6)' }}>/ 100</span>
                </div>
              </div>

            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '60vh', gap: 16 }}>
              <div
                style={{
                  width: 64, height: 64, borderRadius: 16,
                  background: 'rgba(248,113,113,0.1)',
                  border: '1px solid rgba(248,113,113,0.2)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}
              >
                <Leaf size={28} color="#f87171" />
              </div>
              <p style={{ color: 'rgba(232,245,233,0.6)', fontSize: 15 }}>
                Unable to reach sensor backend. Retrying...
              </p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}