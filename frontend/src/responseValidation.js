// Validate before updating React state. A static host may return index.html
// with HTTP 200 for an unconfigured API route.
export function requireObjectResponse(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new TypeError('Invalid API object response');
  }
  return value;
}

export function requireProjectFiles(value) {
  if (!Array.isArray(value)) {
    throw new TypeError('Invalid project list response');
  }
  value.forEach(requireObjectResponse);
  return value;
}
