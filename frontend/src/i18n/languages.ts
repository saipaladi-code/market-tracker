export interface Language {
  code: string;
  name: string;
  native: string;
  dir: 'ltr' | 'rtl';
  googleCode?: string;
}

export const SUPPORTED_LANGUAGES: Language[] = [
  { code: 'en', name: 'English', native: 'English', dir: 'ltr', googleCode: 'en' },
  { code: 'te', name: 'Telugu', native: 'తెలుగు', dir: 'ltr', googleCode: 'te' },
  { code: 'hi', name: 'Hindi', native: 'हिन्दी', dir: 'ltr', googleCode: 'hi' },
  { code: 'ta', name: 'Tamil', native: 'தமிழ்', dir: 'ltr', googleCode: 'ta' },
  { code: 'kn', name: 'Kannada', native: 'ಕನ್ನಡ', dir: 'ltr', googleCode: 'kn' },
  { code: 'ml', name: 'Malayalam', native: 'മലയാളം', dir: 'ltr', googleCode: 'ml' },
  { code: 'mr', name: 'Marathi', native: 'मराठी', dir: 'ltr', googleCode: 'mr' },
  { code: 'bn', name: 'Bengali', native: 'বাংলা', dir: 'ltr', googleCode: 'bn' },
  { code: 'gu', name: 'Gujarati', native: 'ગુજરાતી', dir: 'ltr', googleCode: 'gu' },
  { code: 'pa', name: 'Punjabi', native: 'ਪੰਜਾਬੀ', dir: 'ltr', googleCode: 'pa' },
  { code: 'ur', name: 'Urdu', native: 'اردو', dir: 'rtl', googleCode: 'ur' },
  { code: 'or', name: 'Odia', native: 'ଓଡ଼ିଆ', dir: 'ltr', googleCode: 'or' },
  { code: 'as', name: 'Assamese', native: 'অসমীয়া', dir: 'ltr', googleCode: 'as' },
  { code: 'es', name: 'Spanish', native: 'Español', dir: 'ltr', googleCode: 'es' },
  { code: 'fr', name: 'French', native: 'Français', dir: 'ltr', googleCode: 'fr' },
  { code: 'de', name: 'German', native: 'Deutsch', dir: 'ltr', googleCode: 'de' },
  { code: 'ar', name: 'Arabic', native: 'العربية', dir: 'rtl', googleCode: 'ar' },
  { code: 'zh', name: 'Chinese (Simplified)', native: '简体中文', dir: 'ltr', googleCode: 'zh-CN' },
  { code: 'ja', name: 'Japanese', native: '日本語', dir: 'ltr', googleCode: 'ja' },
  { code: 'ko', name: 'Korean', native: '한국어', dir: 'ltr', googleCode: 'ko' }
];

export const RTL_LANGUAGES = ['ur', 'ar'];

export function getLanguageByCode(code: string): Language {
  const clean = (code || 'en').toLowerCase().trim();
  const root = clean.split('-')[0];
  return (
    SUPPORTED_LANGUAGES.find((l) => l.code.toLowerCase() === clean) ||
    SUPPORTED_LANGUAGES.find((l) => l.code.toLowerCase() === root) ||
    SUPPORTED_LANGUAGES[0]
  );
}
