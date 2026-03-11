import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import en from '../locales/en/common.json'
import fa from '../locales/fa/common.json'

const LANGUAGES = { en: 'English', fa: 'فارسی' }
const DEFAULT_LANG = 'fa'

function loadStoredLang() {
  try {
    return localStorage.getItem('atieh_lang') || DEFAULT_LANG
  } catch {
    return DEFAULT_LANG
  }
}

i18n.use(initReactI18next).init({
  resources: { en: { common: en }, fa: { common: fa } },
  lng: loadStoredLang(),
  fallbackLng: 'en',
  ns: ['common'],
  defaultNS: 'common',
  interpolation: { escapeValue: false },
})

i18n.on('languageChanged', (lng) => {
  document.documentElement.lang = lng
  document.documentElement.dir = lng === 'fa' ? 'rtl' : 'ltr'
  try {
    localStorage.setItem('atieh_lang', lng)
  } catch {}
})

// Apply initial dir
document.documentElement.dir = loadStoredLang() === 'fa' ? 'rtl' : 'ltr'

export { LANGUAGES }
