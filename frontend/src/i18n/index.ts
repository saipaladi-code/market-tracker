import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import { resources } from './locales';
import { RTL_LANGUAGES } from './languages';

const STORAGE_KEY = 'FIN_SENTIMENT_LANGUAGE';

const savedLanguage = typeof window !== 'undefined'
  ? localStorage.getItem(STORAGE_KEY) || 'en'
  : 'en';

// Update document direction and language attributes
export function applyLanguageSettings(lang: string) {
  if (typeof document === 'undefined') return;
  const isRtl = RTL_LANGUAGES.includes(lang.toLowerCase());
  document.documentElement.dir = isRtl ? 'rtl' : 'ltr';
  document.documentElement.lang = lang;
  try {
    localStorage.setItem(STORAGE_KEY, lang);
  } catch {}
}

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: savedLanguage,
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false, // React already escapes values
    },
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
    },
  });

// Apply on initial load
applyLanguageSettings(savedLanguage);

// Update HTML tag whenever language changes
i18n.on('languageChanged', (lng) => {
  applyLanguageSettings(lng);
});

export default i18n;
