import React, { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { getLanguageByCode } from '../i18n/languages';
import { getSavedLanguage, setGoogleTranslateCookie, applyLanguageSettings } from '../i18n';

export const GlobalTranslationManager: React.FC = () => {
  const location = useLocation();

  useEffect(() => {
    const currentCode = getSavedLanguage();
    if (!currentCode || currentCode === 'en') {
      return;
    }

    const langObj = getLanguageByCode(currentCode);
    const googleCode = langObj.googleCode || currentCode;

    // 1. Maintain HTML document attributes and text direction
    applyLanguageSettings(currentCode);

    // 2. Ensure googtrans cookie persists on navigation
    setGoogleTranslateCookie(googleCode);

    // 3. Keep native Google Translate DOM combo synced if mounted
    const combo = document.querySelector<HTMLSelectElement>('.goog-te-combo');
    if (combo && combo.value !== googleCode) {
      combo.value = googleCode;
      combo.dispatchEvent(new Event('change'));
    }
  }, [location.pathname, location.search]);

  return null;
};
