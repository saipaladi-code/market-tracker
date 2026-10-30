export interface Language {
  code: string;
  name: string;
  native: string;
  dir: 'ltr' | 'rtl';
}

export const SUPPORTED_LANGUAGES: Language[] = [
  { code: 'en', name: 'English', native: 'English', dir: 'ltr' },
  { code: 'te', name: 'Telugu', native: 'తెలుగు', dir: 'ltr' },
  { code: 'hi', name: 'Hindi', native: 'हिन्दी', dir: 'ltr' },
  { code: 'ta', name: 'Tamil', native: 'தமிழ்', dir: 'ltr' },
  { code: 'kn', name: 'Kannada', native: 'ಕನ್ನಡ', dir: 'ltr' },
  { code: 'ml', name: 'Malayalam', native: 'മലയാളം', dir: 'ltr' },
  { code: 'mr', name: 'Marathi', native: 'मराठी', dir: 'ltr' },
  { code: 'bn', name: 'Bengali', native: 'বাংলা', dir: 'ltr' },
  { code: 'gu', name: 'Gujarati', native: 'ગુજરાતી', dir: 'ltr' },
  { code: 'pa', name: 'Punjabi', native: 'ਪੰਜਾਬੀ', dir: 'ltr' },
  { code: 'ur', name: 'Urdu', native: 'اردو', dir: 'rtl' },
  { code: 'or', name: 'Odia', native: 'ଓଡ଼ିଆ', dir: 'ltr' },
  { code: 'as', name: 'Assamese', native: 'অসমীয়া', dir: 'ltr' },
  { code: 'es', name: 'Spanish', native: 'Español', dir: 'ltr' },
  { code: 'fr', name: 'French', native: 'Français', dir: 'ltr' },
  { code: 'de', name: 'German', native: 'Deutsch', dir: 'ltr' },
  { code: 'ar', name: 'Arabic', native: 'العربية', dir: 'rtl' },
  { code: 'zh', name: 'Chinese (Simplified)', native: '简体中文', dir: 'ltr' },
  { code: 'ja', name: 'Japanese', native: '日本語', dir: 'ltr' },
  { code: 'ko', name: 'Korean', native: '한국어', dir: 'ltr' }
];

export const RTL_LANGUAGES = ['ur', 'ar'];
