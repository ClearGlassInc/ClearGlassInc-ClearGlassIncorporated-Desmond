export type ZoneId = 'Zone A' | 'Zone B' | 'Zone C' | 'ICU Pod' | 'Clean Room' | 'Boardroom';

export interface AirSystemState {
  airflow: number;
  pressure: number;
  temperature: number;
  humidity: number;
  filtration: number;
  ventAngle: number;
  activeZone: ZoneId;
  autonomousMode: boolean;
}

export interface ZoneProfile {
  id: ZoneId;
  label: string;
  nodes: number;
  occupancy: number;
  targetTemperature: number;
  targetHumidity: number;
  pressureMode: 'positive' | 'neutral' | 'negative';
}

export const zones: ZoneProfile[] = [
  { id: 'Zone A', label: 'Executive Atrium', nodes: 12, occupancy: 68, targetTemperature: 22.2, targetHumidity: 44, pressureMode: 'positive' },
  { id: 'Zone B', label: 'Demo Theater', nodes: 15, occupancy: 74, targetTemperature: 21.8, targetHumidity: 45, pressureMode: 'neutral' },
  { id: 'Zone C', label: 'Engineering Bay', nodes: 18, occupancy: 61, targetTemperature: 22.5, targetHumidity: 43, pressureMode: 'positive' },
  { id: 'ICU Pod', label: 'Clinical Pod', nodes: 21, occupancy: 52, targetTemperature: 21.4, targetHumidity: 42, pressureMode: 'positive' },
  { id: 'Clean Room', label: 'Fabrication Clean Room', nodes: 24, occupancy: 36, targetTemperature: 20.8, targetHumidity: 40, pressureMode: 'positive' },
  { id: 'Boardroom', label: 'Investor Boardroom', nodes: 9, occupancy: 83, targetTemperature: 22.0, targetHumidity: 46, pressureMode: 'neutral' },
];

export const zoneIds = zones.map((zone) => zone.id) as ZoneId[];
