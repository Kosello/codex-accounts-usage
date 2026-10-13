import { Tip, Switch, atom, PALETTE_AREA, useQuery, useQueryClient, useValue, host } from '@hermes/plugin-sdk'
import { jsx } from 'react/jsx-runtime'
import { useState } from 'react'

export function percent(value) {
  return Number.isFinite(value) ? `${Math.round(value)}%` : 'n/a'
}
export function chipLabel(account, compact = true) {
  if (!account) return 'Codex: …'
  const windows = account.windows || []
  const s = windows.find(w => w.seconds === 18000)
  const w = windows.find(w => w.seconds === 604800)
  const values = [s ? (compact ? percent(s.used_percent) : `5h ${percent(s.used_percent)}`) : null, w ? (compact ? percent(w.used_percent) : `W ${percent(w.used_percent)}`) : null].filter(Boolean)
  if (!values.length) values.push(...windows.map(w => compact ? percent(w.used_percent) : `${w.label} ${percent(w.used_percent)}`))
  return `${compact ? '' : `Codex ${account.label} · `}${values.join(' / ') || 'n/a'}${account.status === 'stale' ? ' ⚠' : ''}`
}
function detail(account) {
  if (!account) return 'Reading account limits…'
  const lines = [`Codex · ${account.label}${account.email ? ` · ${account.email}` : ''}`, account.plan ? `ChatGPT ${account.plan} · Codex allowance` : 'Codex allowance', 'Percentages USED (5-hour / weekly)']
  for (const w of account.windows || []) {
    const reset = w.reset_at ? new Date(w.reset_at * 1000).toLocaleString() : 'unknown'
    lines.push(`${w.label}: ${percent(w.used_percent)} used · resets ${reset}`)
  }
  if (account.status === 'stale') lines.push('STALE — showing the last successful reading')
  if (account.error) lines.push(`${account.status === 'stale' ? 'STALE — last successful reading. ' : ''}${account.error}`)
  if (account.updated_at) lines.push(`Updated ${new Date(account.updated_at * 1000).toLocaleString()}`)
  lines.push('Click to refresh account usage')
  return lines.join('\n')
}
function Accounts({ ctx, settings }) {
  const compact = useValue(settings.compact)
  const qc = useQueryClient()
  const profile = useValue(host.state.profile)
  const connection = useValue(host.state.connectionId || host.state.profile)
  const [refreshing, setRefreshing] = useState(false)
  const key = [ctx.source, 'codex-accounts', connection, profile]
  const { data, error, isFetching } = useQuery({ queryKey: key, queryFn: () => ctx.rest('/usage', { timeoutMs: 65000 }), refetchInterval: 180000, staleTime: 150000, retry: false })
  const accounts = (data?.accounts || []).map(account => error
    ? { ...account, status: 'stale', error: 'Backend unreachable — showing the last successful reading' }
    : account)
  const refresh = async () => {
    if (refreshing || isFetching) return
    setRefreshing(true)
    try {
      const updated = await ctx.rest('/refresh', { method: 'POST', timeoutMs: 65000 })
      qc.setQueryData(key, updated)
    } catch { host.notify({ kind: 'error', message: 'Codex usage refresh failed. Check the backend connection.' }) }
    finally { setRefreshing(false) }
  }
  if (!accounts.length) return jsx(Tip, { label: data?.error || (error ? 'Codex usage backend unavailable. Restart Hermes to load the new backend.' : 'Reading Codex account usage…'), children: jsx('button', { type: 'button', onClick: refresh, style: { padding: '0 6px', fontSize: '11px', color: 'var(--ui-text-tertiary)' }, children: error || data?.error ? 'Codex accounts: n/a' : 'Codex accounts: …' }) })
  return jsx('span', { style: { display: 'inline-flex', height: '100%', alignItems: 'center', gap: '4px' }, children: accounts.map(account => jsx(Tip, { label: jsx('span', { style: { whiteSpace: 'pre-line' }, children: detail(account) }), children: jsx('button', { type: 'button', disabled: isFetching || refreshing, onClick: refresh, 'aria-label': `${chipLabel(account, false)}, percentages used`, style: { height: '100%', padding: '0 6px', fontSize: '11px', whiteSpace: 'nowrap', color: account.status !== 'ok' ? 'var(--ui-badge-warning)' : 'var(--ui-text-secondary)' }, children: chipLabel(account, compact) }) }, account.id)) })
}
export function createSettings(ctx) {
  const compact = atom(true)
  let edited = false
  const apply = value => { if (!edited && typeof value === 'boolean') compact.set(value) }
  try { Promise.resolve(ctx.storage.get('compact', true)).then(apply).catch(() => {}) }
  catch { /* Unreadable storage keeps the compact default. */ }
  const setCompact = value => {
    edited = true
    compact.set(Boolean(value))
    const failed = () => host.notify({ kind: 'error', message: 'Could not save Codex status-bar setting.' })
    try { Promise.resolve(ctx.storage.set('compact', compact.get())).catch(failed) }
    catch { failed() }
  }
  return { compact, setCompact }
}
function Settings({ settings }) {
  const compact = useValue(settings.compact)
  return jsx('div', { style: { padding: '12px', fontSize: '12px' }, children: [
    jsx('label', { style: { display: 'flex', alignItems: 'center', gap: '8px' }, children: [
      jsx(Switch, { checked: compact, onCheckedChange: settings.setCompact, 'aria-label': 'Compact Codex status bar' }),
      'Compact Codex status bar'
    ] }),
    jsx('p', { children: 'Show only percentages used (5-hour / weekly). Hover each account for its identity, windows and resets. Click a chip to refresh all accounts.' })
  ] })
}
export default {
  id: 'codex-accounts-usage', name: 'Codex Accounts Usage',
  register(ctx) {
    const settings = createSettings(ctx)
    ctx.register({ id: 'accounts', area: 'statusBar.right', order: 131, render: () => jsx(Accounts, { ctx, settings }) })
    ctx.register({ id: 'settings', area: 'panes', title: 'Codex Usage Settings', data: { placement: 'right', width: '280px' }, render: () => jsx(Settings, { settings }) })
    ctx.register({ id: 'toggle-compact', area: PALETTE_AREA, data: { id: 'codex-accounts-usage.toggle-compact', label: 'Codex: Toggle compact status bar', keywords: ['codex', 'settings', 'usage', 'compact'], run: () => settings.setCompact(!settings.compact.get()) } })
  }
}
