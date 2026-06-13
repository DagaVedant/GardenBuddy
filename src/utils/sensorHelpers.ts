import { SensorStatus } from '../types';

export function getTempStatus(temp: number): SensorStatus {
  if (temp < 50 || temp > 95) return 'critical';
  if (temp < 60 || temp > 88) return 'warning';
  return 'optimal';
}

export function getHumidityStatus(humidity: number): SensorStatus {
  if (humidity < 20 || humidity > 90) return 'critical';
  if (humidity < 30 || humidity > 80) return 'warning';
  return 'optimal';
}

export function getSoilStatus(soil: number): SensorStatus {
  if (soil < 15) return 'critical';
  if (soil < 30) return 'warning';
  if (soil > 70) return 'moist';
  return 'optimal';
}

export function getLightStatus(light: number): SensorStatus {
  if (light < 10) return 'critical';
  if (light < 25) return 'warning';
  return 'optimal';
}
