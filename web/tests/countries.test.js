import test from 'node:test';
import assert from 'node:assert/strict';
import {
  COUNTRIES,
  getAvailableCountries,
  normalizeCountryCode,
  getCountryName,
  getCountrySearchTerms,
} from '../src/countries.js';

test('countries registry: all entries have required fields and valid ISO codes', () => {
  assert.ok(COUNTRIES.length >= 50, 'Expected at least 50 countries in registry');
  for (const c of COUNTRIES) {
    assert.ok(c.code && c.code.length === 2, `Country code should be 2 uppercase letters: ${c.code}`);
    assert.ok(c.es && c.es.length > 0, `Country ${c.code} should have Spanish name`);
    assert.ok(c.en && c.en.length > 0, `Country ${c.code} should have English name`);
    assert.ok(['latam', 'north_america', 'worldwide'].includes(c.scope), `Invalid scope for ${c.code}: ${c.scope}`);
  }
});

test('getAvailableCountries returns localized names depending on language', () => {
  const esWorldwide = getAvailableCountries('worldwide', 'es');
  const enWorldwide = getAvailableCountries('worldwide', 'en');

  const esJapan = esWorldwide.find((c) => c.code === 'JP');
  const enJapan = enWorldwide.find((c) => c.code === 'JP');
  assert.equal(esJapan.name, 'Japón');
  assert.equal(enJapan.name, 'Japan');

  const esGermany = esWorldwide.find((c) => c.code === 'DE');
  const enGermany = enWorldwide.find((c) => c.code === 'DE');
  assert.equal(esGermany.name, 'Alemania');
  assert.equal(enGermany.name, 'Germany');

  const esUs = esWorldwide.find((c) => c.code === 'US');
  const enUs = enWorldwide.find((c) => c.code === 'US');
  assert.equal(esUs.name, 'Estados Unidos');
  assert.equal(enUs.name, 'United States');
});

test('getAvailableCountries filters correctly by territorial scope', () => {
  const latam = getAvailableCountries('latam', 'en');
  assert.ok(latam.some((c) => c.code === 'UY'), 'Latam should include Uruguay');
  assert.ok(!latam.some((c) => c.code === 'US'), 'Latam should not include US');
  assert.ok(!latam.some((c) => c.code === 'DE'), 'Latam should not include Germany');

  const latamNa = getAvailableCountries('latam_na', 'en');
  assert.ok(latamNa.some((c) => c.code === 'UY'), 'Latam+NA should include Uruguay');
  assert.ok(latamNa.some((c) => c.code === 'US'), 'Latam+NA should include US');
  assert.ok(latamNa.some((c) => c.code === 'CA'), 'Latam+NA should include Canada');
  assert.ok(!latamNa.some((c) => c.code === 'DE'), 'Latam+NA should not include Germany');

  const worldwide = getAvailableCountries('worldwide', 'en');
  assert.ok(worldwide.some((c) => c.code === 'DE'), 'Worldwide should include Germany');
  assert.ok(worldwide.some((c) => c.code === 'JP'), 'Worldwide should include Japan');
});

test('normalizeCountryCode resolves names and aliases to ISO code', () => {
  assert.equal(normalizeCountryCode('Japón'), 'JP');
  assert.equal(normalizeCountryCode('Japan'), 'JP');
  assert.equal(normalizeCountryCode('jp'), 'JP');

  assert.equal(normalizeCountryCode('Germany'), 'DE');
  assert.equal(normalizeCountryCode('Alemania'), 'DE');
  assert.equal(normalizeCountryCode('Deutschland'), 'DE');

  assert.equal(normalizeCountryCode('United States'), 'US');
  assert.equal(normalizeCountryCode('Estados Unidos'), 'US');
  assert.equal(normalizeCountryCode('USA'), 'US');
});

test('getCountryName dynamically translates country code or name', () => {
  assert.equal(getCountryName('JP', 'en'), 'Japan');
  assert.equal(getCountryName('JP', 'es'), 'Japón');

  assert.equal(getCountryName('DE', 'en'), 'Germany');
  assert.equal(getCountryName('DE', 'es'), 'Alemania');

  // Passing Spanish or English name translates to target language
  assert.equal(getCountryName('Japón', 'en'), 'Japan');
  assert.equal(getCountryName('Japan', 'es'), 'Japón');
  assert.equal(getCountryName('Germany', 'es'), 'Alemania');
  assert.equal(getCountryName('Alemania', 'en'), 'Germany');
});

test('getCountrySearchTerms returns bilingual terms for ATS regex matching', () => {
  const jpTerms = getCountrySearchTerms('JP');
  assert.ok(jpTerms.includes('Japan'));
  assert.ok(jpTerms.includes('Japón'));

  const deTerms = getCountrySearchTerms('DE');
  assert.ok(deTerms.includes('Germany'));
  assert.ok(deTerms.includes('Alemania'));
  assert.ok(deTerms.includes('Deutschland'));
});
