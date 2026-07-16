import test from 'node:test'
import assert from 'node:assert/strict'

import { getLocalizedAuthError, getLocalizedUiError } from '../lib/authErrors.ts'

test('authentication API errors are mapped to Chinese user-facing messages', () => {
  assert.equal(getLocalizedAuthError(new Error('Incorrect email or password'), '登录失败'), '邮箱或密码错误')
  assert.equal(getLocalizedAuthError(new Error('Invalid invitation code'), '注册失败'), '邀请码无效，请检查后重试')
  assert.equal(getLocalizedAuthError(new Error('Email already registered'), '注册失败'), '该邮箱已注册，请直接登录')
})

test('unknown English API details fall back instead of leaking into Chinese auth UI', () => {
  assert.equal(getLocalizedAuthError(new Error('Unexpected upstream failure'), '请稍后重试'), '请稍后重试')
  assert.equal(getLocalizedAuthError(new Error('当前账户无法登录'), '请稍后重试'), '当前账户无法登录')
})

test('settings and other product surfaces do not expose raw English API details', () => {
  assert.equal(getLocalizedUiError(new Error('Unexpected upstream failure'), '保存失败'), '保存失败')
  assert.equal(getLocalizedUiError('当前密码错误，请重试', '修改密码失败'), '当前密码错误，请重试')
  assert.equal(getLocalizedUiError('Current password is incorrect', '修改密码失败'), '当前密码错误')
})
