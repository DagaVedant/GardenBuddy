export interface SensorData {
  temp: number;
  humidity: number;
  soil: number;
  light: number;
  score: number;
  insights?: Insight[];
  chart: {
    time: string[];
    temperature_f: number[];
    humidity: number[];
    soil_moisture_percent: number[];
    light_percent: number[];
  };
}

export type SensorStatus = 'optimal' | 'warning' | 'critical' | 'moist';

export interface Insight {
  message: string;
  type: 'info' | 'warning' | 'critical';
}
