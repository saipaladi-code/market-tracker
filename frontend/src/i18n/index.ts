import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import { resources } from './locales';
import { RTL_LANGUAGES, getLanguageByCode } from './languages';

export const STORAGE_KEY = 'FIN_SENTIMENT_LANGUAGE';

export function getSavedLanguage(): string {
  if (typeof window === 'undefined') return 'en';
  try {
    return localStorage.getItem(STORAGE_KEY) || 'en';
  } catch {
    return 'en';
  }
}

export function clearGoogleTranslateCookie() {
  if (typeof document === 'undefined') return;
  const host = typeof window !== 'undefined' ? window.location.hostname : '';
  const parts = host.split('.');
  const domains = ['', host, '.' + host];
  if (parts.length >= 2) {
    domains.push('.' + parts.slice(-2).join('.'));
  }
  const paths = ['/', ''];

  domains.forEach((d) => {
    paths.forEach((p) => {
      const dAttr = d ? `; domain=${d}` : '';
      const pAttr = p ? `; path=${p}` : '';
      document.cookie = `googtrans=; expires=Thu, 01 Jan 1970 00:00:00 UTC${pAttr}${dAttr}`;
      document.cookie = `googtrans=; expires=Thu, 01 Jan 1970 00:00:00 GMT${pAttr}${dAttr}`;
      document.cookie = `googtrans=; max-age=0${pAttr}${dAttr}`;
    });
  });
}

export function setGoogleTranslateCookie(googleCode: string) {
  if (typeof document === 'undefined') return;
  if (!googleCode || googleCode === 'en') {
    clearGoogleTranslateCookie();
    return;
  }
  const cookieVal = `/en/${googleCode}`;
  const host = typeof window !== 'undefined' ? window.location.hostname : '';

  // Set for root path
  document.cookie = `googtrans=${cookieVal}; path=/; SameSite=Lax`;
  if (host && host.indexOf('.') !== -1) {
    document.cookie = `googtrans=${cookieVal}; path=/; domain=${host}; SameSite=Lax`;
  }
}

// Update document direction and language attributes
export function applyLanguageSettings(lang: string) {
  if (typeof document === 'undefined') return;
  const clean = (lang || 'en').toLowerCase().trim();
  const isRtl = RTL_LANGUAGES.includes(clean);
  document.documentElement.dir = isRtl ? 'rtl' : 'ltr';
  document.documentElement.lang = clean;
  try {
    localStorage.setItem(STORAGE_KEY, clean);
  } catch {}
}

export function changeAppLanguage(langCode: string, reload: boolean = true) {
  const langObj = getLanguageByCode(langCode);
  const targetCode = langObj.code;
  const targetGoogleCode = langObj.googleCode || targetCode;

  // 1. Update document attributes and persistence
  applyLanguageSettings(targetCode);

  // 2. Synchronize Google Translate cookie
  if (targetCode === 'en') {
    clearGoogleTranslateCookie();
  } else {
    setGoogleTranslateCookie(targetGoogleCode);
  }

  // 3. Update react-i18next
  i18n.changeLanguage(targetCode);

  // 4. Update native Google Translate combo if already mounted
  if (typeof document !== 'undefined') {
    const combo = document.querySelector<HTMLSelectElement>('.goog-te-combo');
    if (combo) {
      combo.value = targetGoogleCode;
      combo.dispatchEvent(new Event('change'));
    }
  }

  // 5. Reload to guarantee clean, unfragmented DOM translation if requested
  if (reload && typeof window !== 'undefined') {
    window.location.reload();
  }
}

const initialLanguage = getSavedLanguage();

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: initialLanguage,
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false, // React already escapes values
    },
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
    },
  });

// Apply on initial script evaluation
applyLanguageSettings(initialLanguage);

// Update HTML tag whenever i18n triggers languageChanged
i18n.on('languageChanged', (lng) => {
  applyLanguageSettings(lng);
});

export default i18n;
