'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { AirSystemState, ZoneId, zoneIds, zones } from '@/lib/types';

const STORAGE_KEY = 'clearglass-air-system-v0.2';

export const initialAirSystemState: AirSystemState = {
  airflow: 68,
  pressure: 101.3,
  temperature: 22.4,
  humidity: 42,
  filtration: 94,
  ventAngle: 45,
  activeZone: 'Zone A',
  autonomousMode: false,
};

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

function sanitizeState(candidate: Partial<AirSystemState>): AirSystemState {
  return {
    airflow: clamp(Number(candidate.airflow ?? initialAirSystemState.airflow), 0, 100),
    pressure: clamp(Number(candidate.pressure ?? initialAirSystemState.pressure), 0.5, 4.5),
    temperature: clamp(Number(candidate.temperature ?? initialAirSystemState.temperature), 16, 28),
    humidity: clamp(Number(candidate.humidity ?? initialAirSystemState.humidity), 20, 80),
    filtration: clamp(Number(candidate.filtration ?? initialAirSystemState.filtration), 70, 100),
    ventAngle: clamp(Number(candidate.ventAngle ?? initialAirSystemState.ventAngle), 0, 90),
    activeZone: zoneIds.includes(candidate.activeZone as ZoneId) ? (candidate.activeZone as ZoneId) : initialAirSystemState.activeZone,
    autonomousMode: Boolean(candidate.autonomousMode ?? initialAirSystemState.autonomousMode),
  };
}

export function useAirSystem() {
  const [state, setState] = useState<AirSystemState>(initialAirSystemState);
  const [isHydrated, setIsHydrated] = useState(false);

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(STORAGE_KEY);
      if (saved) setState(sanitizeState(JSON.parse(saved)));
    } catch {
      window.localStorage.removeItem(STORAGE_KEY);
    } finally {
      setIsHydrated(true);
    }
  }, []);

  useEffect(() => {
    if (!isHydrated) return;
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }, [isHydrated, state]);

  const activeZoneProfile = useMemo(
    () => zones.find((zone) => zone.id === state.activeZone) ?? zones[0],
    [state.activeZone],
  );

  const riskIndex = useMemo(() => {
    const tempRisk = Math.abs(state.temperature - activeZoneProfile.targetTemperature) * 4.2;
    const humidityRisk = Math.abs(state.humidity - activeZoneProfile.targetHumidity) * 0.72;
    const pressureRisk = Math.abs(state.pressure - (activeZoneProfile.pressureMode === 'positive' ? 2.6 : 2.1)) * 12;
    const filterRisk = Math.max(0, 98 - state.filtration) * 1.8;
    const airflowRisk = Math.max(0, activeZoneProfile.occupancy - state.airflow) * 0.24;
    return Math.min(100, Math.round(tempRisk + humidityRisk + pressureRisk + filterRisk + airflowRisk));
  }, [activeZoneProfile, state]);

  const systemHealth = useMemo(() => Math.max(0, 100 - riskIndex), [riskIndex]);

  const patchState = useCallback((patch: Partial<AirSystemState>) => {
    setState((current) => sanitizeState({ ...current, ...patch }));
  }, []);

  const update = useCallback((key: keyof AirSystemState, value: AirSystemState[keyof AirSystemState]) => {
    patchState({ [key]: value });
  }, [patchState]);

  return {
    state,
    isHydrated,
    activeZoneProfile,
    riskIndex,
    systemHealth,
    resetSystem: () => setState(initialAirSystemState),
    update,
    setAirflow: (airflow: number) => patchState({ airflow }),
    setPressure: (pressure: number) => patchState({ pressure }),
    setTemperature: (temperature: number) => patchState({ temperature }),
    setHumidity: (humidity: number) => patchState({ humidity }),
    setFiltration: (filtration: number) => patchState({ filtration }),
    setVentAngle: (ventAngle: number) => patchState({ ventAngle }),
    setActiveZone: (activeZone: ZoneId) => patchState({ activeZone }),
    setAutonomousMode: (autonomousMode: boolean) => patchState({ autonomousMode }),
  };
}
