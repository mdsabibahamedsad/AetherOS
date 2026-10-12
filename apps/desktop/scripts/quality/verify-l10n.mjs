#!/usr/bin/env node
import { readFileSync, writeFileSync, existsSync, readdirSync } from 'fs';
import { resolve } from 'path';

const ROOT = resolve(import.meta.dirname, '../..');
const I18N_DIR = resolve(ROOT, 'src/i18n');
const REPORT_PATH = resolve(ROOT, 'docs/LOCALIZATION_REPORT.md');

if (!existsSync(I18N_DIR)) {
  console.log('No i18n directory found at src/i18n');
  process.exit(0);
}

const locales = readdirSync(I18N_DIR).filter(f => f.endsWith('.json') || f.endsWith('.ts'));
const baseLocale = 'en';
const coverage = {};

function flattenKeys(obj, prefix = '') {
  let keys = [];
  for (const [key, value] of Object.entries(obj)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      keys.push(...flattenKeys(value, fullKey));
    } else {
      keys.push(fullKey);
    }
  }
  return keys;
}

let baseKeys = [];
const localeData = {};

for (const file of locales) {
  const path = resolve(I18N_DIR, file);
  let data;
  if (file.endsWith('.json')) {
    data = JSON.parse(readFileSync(path, 'utf-8'));
  } else {
    continue;
  }
  const locale = file.replace('.json', '');
  localeData[locale] = data;
  const keys = flattenKeys(data);
  coverage[locale] = { total: keys.length };
  if (locale === baseLocale) baseKeys = keys;
}

for (const [locale, info] of Object.entries(coverage)) {
  if (locale === baseLocale) continue;
  const localeKeys = flattenKeys(localeData[locale]);
  const missing = baseKeys.filter(k => !localeKeys.includes(k));
  const extra = localeKeys.filter(k => !baseKeys.includes(k));
  info.missing = missing;
  info.extra = extra;
  info.coverage = Math.round(((baseKeys.length - missing.length) / baseKeys.length) * 100);
}

const report = `# Localization Coverage Report

**Date:** ${new Date().toISOString().split('T')[0]}
**Project:** AetherOS Desktop

## Summary

| Locale | Total Strings | Coverage | Missing | Extra |
|--------|--------------|----------|---------|-------|
${Object.entries(coverage).map(([locale, info]) =>
  `| ${locale} | ${info.total} | ${info.coverage !== undefined ? info.coverage + '%' : '100%'} | ${info.missing?.length || 0} | ${info.extra?.length || 0} |`
).join('\n')}

${baseKeys.length} base keys in en locale.

## Missing Keys by Locale

${Object.entries(coverage).filter(([, info]) => info.missing?.length).map(([locale, info]) =>
  `### ${locale}\n${info.missing.map(k => `- \`${k}\``).join('\n')}`
).join('\n\n') || '*All locales are up to date*'}

## Recommendations
- Run automated translation placeholder check for missing keys
- Verify RTL support for Arabic, Hebrew locales if applicable
- Ensure ICU messageformat compatibility if used
- Check for truncated translations in UI (longer translated strings)
`;

writeFileSync(REPORT_PATH, report, 'utf-8');
console.log(`Localization report written to ${REPORT_PATH}`);
