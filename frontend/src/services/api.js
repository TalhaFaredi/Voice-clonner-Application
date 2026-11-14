export const BASE = window.MELLIFON_API || '/api';
let csrf = '';
export function setCSRF(value) { csrf = value || ''; }
export async function api(path, {method='GET', data, key}={}) {
  const headers = {};
  let body;
  if (data instanceof FormData) body = data;
  else if (data !== undefined) { body = JSON.stringify(data); headers['Content-Type']='application/json'; }
  if (method !== 'GET' && csrf) headers['X-CSRF-Token']=csrf;
  if (key) headers['Idempotency-Key']=key;
  let response;
  try { response = await fetch(BASE+path,{method,headers,body,credentials:'include'}); }
  catch { throw new Error('Cannot reach the audio service. Check that the backend is running.'); }
  let result;
  try { result = await response.json(); } catch { throw new Error('The service returned an unreadable response.'); }
  if (!response.ok) { const error = new Error(result.error || 'Request failed'); error.status=response.status; throw error; }
  if (result.csrf) setCSRF(result.csrf);
  return result;
}
