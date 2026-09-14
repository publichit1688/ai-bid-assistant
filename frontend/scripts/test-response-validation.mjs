import assert from 'node:assert/strict';
import test from 'node:test';
import { requireObjectResponse, requireProjectFiles } from '../src/responseValidation.js';

test('project list preserves valid records and empty lists', () => {
  const records = [{ id: 1, filename: 'synthetic.pdf' }];
  assert.equal(requireProjectFiles(records), records);
  assert.deepEqual(requireProjectFiles([]), []);
});

test('project list rejects HTML and non-array responses before state update', () => {
  for (const value of ['<!doctype html><html></html>', null, {}, 42]) {
    assert.throws(() => requireProjectFiles(value), TypeError);
  }
});

test('project list rejects invalid rows that could crash rendering', () => {
  for (const value of [[null], ['file'], [[]]]) {
    assert.throws(() => requireProjectFiles(value), TypeError);
  }
});

test('dashboard object guard rejects HTML without exposing response contents', () => {
  const data = { total_projects: 0 };
  assert.equal(requireObjectResponse(data), data);
  for (const value of ['<html>private response</html>', null, []]) {
    assert.throws(() => requireObjectResponse(value), { message: 'Invalid API object response' });
  }
});
