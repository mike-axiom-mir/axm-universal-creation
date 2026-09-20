// Institutional interchange helpers; professional decisions live in their packages.
import {createHash} from 'node:crypto';

export function need(condition, code) { if (!condition) throw Error(code); }
export function exact(value, required, optional = []) {
  need(value !== null && typeof value === 'object' && !Array.isArray(value), 'OBJECT_REQUIRED');
  need(required.every(k => Object.hasOwn(value, k)), 'FIELD_REQUIRED');
  need(Object.keys(value).every(k => [...required, ...optional].includes(k)), 'FIELD_UNKNOWN');
}
export function data(value) {
  let nodes = 0;
  function copy(v, depth) {
    need(++nodes <= 200000 && depth <= 80, 'DATA_LIMIT');
    if (v === null || typeof v === 'boolean') return v;
    if (typeof v === 'number') { need(Number.isFinite(v) && Math.abs(v) <= Number.MAX_SAFE_INTEGER, 'NUMBER_INVALID'); return v === 0 ? 0 : v; }
    if (typeof v === 'string') {
      need(v.length <= 2097152 && !/[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/u.test(v), 'STRING_INVALID');
      return v;
    }
    need(v && typeof v === 'object', 'JSON_REQUIRED');
    need(Array.isArray(v) ? Object.getPrototypeOf(v) === Array.prototype : [Object.prototype, null].includes(Object.getPrototypeOf(v)), 'PLAIN_DATA_REQUIRED');
    const descriptors = Object.getOwnPropertyDescriptors(v);
    need(Reflect.ownKeys(descriptors).every(k => typeof k === 'string'), 'SYMBOL_REFUSED');
    const out = Array.isArray(v) ? [] : {};
    for (const [key, descriptor] of Object.entries(descriptors)) {
      if (Array.isArray(v) && key === 'length') continue;
      need(descriptor.enumerable && Object.hasOwn(descriptor, 'value'), 'ACCESSOR_REFUSED');
      need(!['__proto__', 'constructor', 'prototype'].includes(key), 'KEY_REFUSED');
      if (Array.isArray(v)) need(/^(0|[1-9][0-9]*)$/.test(key) && Number(key) < v.length, 'ARRAY_INVALID');
      out[key] = copy(descriptor.value, depth + 1);
    }
    if (Array.isArray(v)) need(Object.keys(out).length === v.length, 'ARRAY_INVALID');
    return out;
  }
  const result = copy(value, 0);
  need(Buffer.byteLength(JSON.stringify(result)) <= 8 * 1048576, 'DATA_BYTES_LIMIT');
  return result;
}
export function canonical(value) {
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (value !== null && typeof value === 'object') return '{' + Object.keys(value).sort().map(k => JSON.stringify(k) + ':' + canonical(value[k])).join(',') + '}';
  return JSON.stringify(value);
}
export const digest = value => createHash('sha256').update(typeof value === 'string' ? value : canonical(value)).digest('hex');
export const same = (a, b) => canonical(a) === canonical(b);
export const id = value => typeof value === 'string' && /^[A-Za-z][A-Za-z0-9_.-]{0,95}$/.test(value);
export const sha = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
export function seal(value, field) { return {...value, [field]: digest(value)}; }
export function bound(value, field) { const {[field]: expected, ...body} = value; need(sha(expected) && digest(body) === expected, 'BINDING_MISMATCH:' + field); }
