import test from 'node:test';
import assert from 'node:assert/strict';
import es from '../src/i18n/es.js';
import en from '../src/i18n/en.js';
import { currentLang, t, setLanguage, toggleLanguage } from '../src/i18n/index.js';

function getLeafKeys(obj, prefix = '') {
  const leaves = {};
  for (const [key, value] of Object.entries(obj)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      Object.assign(leaves, getLeafKeys(value, fullKey));
    } else {
      leaves[fullKey] = value;
    }
  }
  return leaves;
}

test('i18n dictionaries: es and en have matching structure and valid strings', () => {
  const esLeaves = getLeafKeys(es);
  const enLeaves = getLeafKeys(en);

  const esKeys = Object.keys(esLeaves).sort();
  const enKeys = Object.keys(enLeaves).sort();

  // Check missing keys in en
  const missingInEn = esKeys.filter((k) => !(k in enLeaves));
  assert.deepEqual(missingInEn, [], `Keys in es.js missing in en.js: ${missingInEn.join(', ')}`);

  // Check missing keys in es
  const missingInEs = enKeys.filter((k) => !(k in esLeaves));
  assert.deepEqual(missingInEs, [], `Keys in en.js missing in es.js: ${missingInEs.join(', ')}`);

  // Ensure no values are empty or undefined
  for (const [key, val] of Object.entries(esLeaves)) {
    assert.ok(typeof val === 'string' && val.trim().length > 0, `es.${key} should not be empty`);
  }
  for (const [key, val] of Object.entries(enLeaves)) {
    assert.ok(typeof val === 'string' && val.trim().length > 0, `en.${key} should not be empty`);
  }
});

test('i18n interpolation: placeholders match between es and en', () => {
  const esLeaves = getLeafKeys(es);
  const enLeaves = getLeafKeys(en);

  const placeholderRegex = /\{([a-zA-Z0-9_]+)\}/g;

  for (const key of Object.keys(esLeaves)) {
    const esMatches = [...esLeaves[key].matchAll(placeholderRegex)].map((m) => m[1]).sort();
    const enMatches = [...enLeaves[key].matchAll(placeholderRegex)].map((m) => m[1]).sort();
    assert.deepEqual(
      enMatches,
      esMatches,
      `Interpolation placeholders mismatch for key "${key}": es=${JSON.stringify(esMatches)} en=${JSON.stringify(enMatches)}`
    );
  }
});

test('i18n reactivity: setLanguage and toggleLanguage work correctly', () => {
  setLanguage('es');
  assert.equal(currentLang.value, 'es');
  assert.equal(t('common.save'), 'Guardar');
  assert.equal(t('nav.search'), 'Buscar vacantes');

  setLanguage('en');
  assert.equal(currentLang.value, 'en');
  assert.equal(t('common.save'), 'Save');
  assert.equal(t('nav.search'), 'Search Jobs');

  toggleLanguage();
  assert.equal(currentLang.value, 'es');

  toggleLanguage();
  assert.equal(currentLang.value, 'en');

  // Test variable replacement
  assert.equal(t('topbar.agentActive', { name: 'Claude' }), 'Active engine: Claude. Click to configure.');
  setLanguage('es');
  assert.equal(t('topbar.agentActive', { name: 'Claude' }), 'Motor activo: Claude. Clic para ajustar.');
});

test('i18n prototype pollution safeguard: forbidden props return key safely', () => {
  assert.equal(t('__proto__.polluted'), '__proto__.polluted');
  assert.equal(t('constructor.prototype'), 'constructor.prototype');
  assert.equal(t('prototype.test'), 'prototype.test');
});
