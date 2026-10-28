/**
 * Bilingual country registry and utilities for geographic filtering in job search.
 */

export const COUNTRIES = [
  // LATAM
  { code: 'AR', es: 'Argentina', en: 'Argentina', scope: 'latam' },
  { code: 'BO', es: 'Bolivia', en: 'Bolivia', scope: 'latam' },
  { code: 'BR', es: 'Brasil', en: 'Brazil', scope: 'latam' },
  { code: 'CL', es: 'Chile', en: 'Chile', scope: 'latam' },
  { code: 'CO', es: 'Colombia', en: 'Colombia', scope: 'latam' },
  { code: 'CR', es: 'Costa Rica', en: 'Costa Rica', scope: 'latam' },
  { code: 'CU', es: 'Cuba', en: 'Cuba', scope: 'latam' },
  { code: 'DO', es: 'República Dominicana', en: 'Dominican Republic', scope: 'latam' },
  { code: 'EC', es: 'Ecuador', en: 'Ecuador', scope: 'latam' },
  { code: 'SV', es: 'El Salvador', en: 'El Salvador', scope: 'latam' },
  { code: 'GT', es: 'Guatemala', en: 'Guatemala', scope: 'latam' },
  { code: 'HN', es: 'Honduras', en: 'Honduras', scope: 'latam' },
  { code: 'MX', es: 'México', en: 'Mexico', scope: 'latam' },
  { code: 'NI', es: 'Nicaragua', en: 'Nicaragua', scope: 'latam' },
  { code: 'PA', es: 'Panamá', en: 'Panama', scope: 'latam' },
  { code: 'PY', es: 'Paraguay', en: 'Paraguay', scope: 'latam' },
  { code: 'PE', es: 'Perú', en: 'Peru', scope: 'latam' },
  { code: 'PR', es: 'Puerto Rico', en: 'Puerto Rico', scope: 'latam' },
  { code: 'UY', es: 'Uruguay', en: 'Uruguay', scope: 'latam' },
  { code: 'VE', es: 'Venezuela', en: 'Venezuela', scope: 'latam' },

  // North America
  { code: 'CA', es: 'Canadá', en: 'Canada', scope: 'north_america' },
  { code: 'US', es: 'Estados Unidos', en: 'United States', aliases: ['USA', 'US', 'EEUU'], scope: 'north_america' },

  // Worldwide
  { code: 'DE', es: 'Alemania', en: 'Germany', aliases: ['Deutschland'], scope: 'worldwide' },
  { code: 'AU', es: 'Australia', en: 'Australia', scope: 'worldwide' },
  { code: 'AT', es: 'Austria', en: 'Austria', scope: 'worldwide' },
  { code: 'BE', es: 'Bélgica', en: 'Belgium', scope: 'worldwide' },
  { code: 'CN', es: 'China', en: 'China', scope: 'worldwide' },
  { code: 'KR', es: 'Corea del Sur', en: 'South Korea', aliases: ['Korea', 'Corea'], scope: 'worldwide' },
  { code: 'DK', es: 'Dinamarca', en: 'Denmark', scope: 'worldwide' },
  { code: 'AE', es: 'Emiratos Árabes Unidos', en: 'United Arab Emirates', aliases: ['UAE', 'EAU'], scope: 'worldwide' },
  { code: 'ES', es: 'España', en: 'Spain', scope: 'worldwide' },
  { code: 'PH', es: 'Filipinas', en: 'Philippines', scope: 'worldwide' },
  { code: 'FI', es: 'Finlandia', en: 'Finland', scope: 'worldwide' },
  { code: 'FR', es: 'Francia', en: 'France', scope: 'worldwide' },
  { code: 'IN', es: 'India', en: 'India', scope: 'worldwide' },
  { code: 'IE', es: 'Irlanda', en: 'Ireland', scope: 'worldwide' },
  { code: 'IL', es: 'Israel', en: 'Israel', scope: 'worldwide' },
  { code: 'IT', es: 'Italia', en: 'Italy', scope: 'worldwide' },
  { code: 'JP', es: 'Japón', en: 'Japan', scope: 'worldwide' },
  { code: 'NO', es: 'Noruega', en: 'Norway', scope: 'worldwide' },
  { code: 'NZ', es: 'Nueva Zelanda', en: 'New Zealand', scope: 'worldwide' },
  { code: 'NL', es: 'Países Bajos', en: 'Netherlands', aliases: ['Holland', 'Holanda'], scope: 'worldwide' },
  { code: 'PL', es: 'Polonia', en: 'Poland', scope: 'worldwide' },
  { code: 'PT', es: 'Portugal', en: 'Portugal', scope: 'worldwide' },
  { code: 'GB', es: 'Reino Unido', en: 'United Kingdom', aliases: ['UK', 'Great Britain', 'Inglaterra', 'England', 'Scotland'], scope: 'worldwide' },
  { code: 'CZ', es: 'República Checa', en: 'Czech Republic', aliases: ['Czechia', 'Chequia'], scope: 'worldwide' },
  { code: 'RO', es: 'Rumania', en: 'Romania', scope: 'worldwide' },
  { code: 'SG', es: 'Singapur', en: 'Singapore', scope: 'worldwide' },
  { code: 'ZA', es: 'Sudáfrica', en: 'South Africa', scope: 'worldwide' },
  { code: 'SE', es: 'Suecia', en: 'Sweden', scope: 'worldwide' },
  { code: 'CH', es: 'Suiza', en: 'Switzerland', scope: 'worldwide' },
  { code: 'UA', es: 'Ucrania', en: 'Ukraine', scope: 'worldwide' },
]

export const COUNTRY_BY_CODE = Object.fromEntries(COUNTRIES.map((c) => [c.code, c]))

function stripAccents(str) {
  return str.normalize('NFD').replace(/[\u0300-\u036f]/g, '')
}

/**
 * Normalizes any country name, alias, or code to its canonical ISO code.
 * Falls back to the trimmed string if unknown.
 */
export function normalizeCountryCode(countryOrCode) {
  if (!countryOrCode) return null
  const raw = String(countryOrCode).trim()
  const upper = raw.toUpperCase()
  if (COUNTRY_BY_CODE[upper]) return upper

  const clean = stripAccents(raw.toLowerCase())
  const found = COUNTRIES.find((c) => {
    if (c.code.toLowerCase() === clean) return true
    if (stripAccents(c.es.toLowerCase()) === clean) return true
    if (stripAccents(c.en.toLowerCase()) === clean) return true
    if (c.aliases?.some((a) => stripAccents(a.toLowerCase()) === clean)) return true
    return false
  })
  return found ? found.code : raw
}

/**
 * Returns the localized name of a country given its code or any representation.
 */
export function getCountryName(countryOrCode, lang = 'es') {
  if (!countryOrCode) return ''
  const code = normalizeCountryCode(countryOrCode)
  const item = COUNTRY_BY_CODE[code]
  if (item) {
    return lang === 'en' ? item.en : item.es
  }
  return String(countryOrCode).trim()
}

/**
 * Returns all searchable terms for ATS regex matching (English + Spanish + aliases).
 */
export function getCountrySearchTerms(countryOrCode) {
  const code = normalizeCountryCode(countryOrCode)
  const item = COUNTRY_BY_CODE[code]
  if (!item) return [String(countryOrCode).trim()]

  const terms = new Set([item.en, item.es, ...(item.aliases || [])])
  return Array.from(terms)
}

/**
 * Returns available countries for a given scope, localized and sorted alphabetically.
 */
export function getAvailableCountries(geoScope, lang = 'es') {
  let list = []
  if (geoScope === 'latam') {
    list = COUNTRIES.filter((c) => c.scope === 'latam')
  } else if (geoScope === 'latam_na') {
    list = COUNTRIES.filter((c) => c.scope === 'latam' || c.scope === 'north_america')
  } else {
    list = [...COUNTRIES]
  }

  return list
    .map((c) => ({
      code: c.code,
      name: lang === 'en' ? c.en : c.es,
      es: c.es,
      en: c.en,
      aliases: c.aliases || [],
      scope: c.scope,
    }))
    .sort((a, b) => a.name.localeCompare(b.name, lang === 'en' ? 'en' : 'es'))
}

// Backward-compatibility exports
export const LATAM_COUNTRIES = COUNTRIES.filter((c) => c.scope === 'latam').map((c) => c.es)
export const NORTH_AMERICA_COUNTRIES = COUNTRIES.filter((c) => c.scope === 'north_america').map((c) => c.es)
export const WORLDWIDE_COUNTRIES = COUNTRIES.map((c) => c.es)
