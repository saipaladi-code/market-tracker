import { useState, useEffect, useCallback } from 'react';

export type BrokerId = 'upstox' | 'groww';

export const BROKER_STORAGE_KEY = 'FIN_SENTIMENT_PREFERRED_BROKER';
export const BROKER_CHANGE_EVENT = 'fin-sentiment-broker-changed';

/**
 * Returns the currently preferred broker from localStorage or defaults to 'upstox'.
 */
export function getSelectedBroker(): BrokerId {
  if (typeof window === 'undefined') return 'upstox';
  try {
    const stored = window.localStorage.getItem(BROKER_STORAGE_KEY);
    if (stored === 'groww' || stored === 'upstox') {
      return stored;
    }
  } catch (e) {
    console.debug('Failed to read broker preference from localStorage:', e);
  }
  return 'upstox';
}

/**
 * Persists the preferred broker to localStorage and dispatches an event
 * so all active components across the application synchronize immediately.
 */
export function setSelectedBrokerPreference(broker: BrokerId): void {
  if (broker !== 'upstox' && broker !== 'groww') return;
  if (typeof window === 'undefined') return;

  try {
    window.localStorage.setItem(BROKER_STORAGE_KEY, broker);
    window.dispatchEvent(
      new CustomEvent(BROKER_CHANGE_EVENT, { detail: { broker } })
    );
  } catch (e) {
    console.debug('Failed to write broker preference to localStorage:', e);
  }
}

/**
 * Returns the user-facing display name for a broker ('Upstox' or 'Groww').
 */
export function getBrokerDisplayName(broker: BrokerId): string {
  return broker === 'upstox' ? 'Upstox' : 'Groww';
}

/**
 * React hook to read and update the active broker preference reactively.
 */
export function useBrokerPreference(): [BrokerId, (b: BrokerId) => void] {
  const [broker, setBrokerState] = useState<BrokerId>(getSelectedBroker);

  useEffect(() => {
    const handleCustomChange = (e: Event) => {
      const customEvent = e as CustomEvent<{ broker?: BrokerId }>;
      if (customEvent.detail?.broker) {
        setBrokerState(customEvent.detail.broker);
      } else {
        setBrokerState(getSelectedBroker());
      }
    };

    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === BROKER_STORAGE_KEY && (e.newValue === 'upstox' || e.newValue === 'groww')) {
        setBrokerState(e.newValue);
      }
    };

    window.addEventListener(BROKER_CHANGE_EVENT, handleCustomChange);
    window.addEventListener('storage', handleStorageChange);

    return () => {
      window.removeEventListener(BROKER_CHANGE_EVENT, handleCustomChange);
      window.removeEventListener('storage', handleStorageChange);
    };
  }, []);

  const setBroker = useCallback((newBroker: BrokerId) => {
    setSelectedBrokerPreference(newBroker);
    setBrokerState(newBroker);
  }, []);

  return [broker, setBroker];
}

