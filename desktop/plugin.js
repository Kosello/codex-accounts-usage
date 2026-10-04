import { Tip, useQuery, useQueryClient, useValue, host } from '@hermes/plugin-sdk'
import { jsx } from 'react/jsx-runtime'
import { useState } from 'react'

export function percent(value) {
  return Number.isFinite(value) ? `${Math.round(value)}%` : 'n/a'
}
export function chipLabel(account) {
  if (!account) return 'Codex: …'
  const windows = account.windows || []
  const s = windows.find(w => w.seconds === 18000)
  const w = windows.find(w => w.seconds === 604800)
  const values = [s ? `5h ${percent(s.used_percent)}` : null, w ? `W ${percent(w.used_percent)}` : null].filter(Boolean)
  if (!values.length) values.push(...windows.map(w => `${w.label} ${percent(w.used_percent)}`))
  return `Codex ${account.label} · ${values.join(' / ') || 'n/a'}${account.status === 'stale' ? ' ⚠' : ''}`
}
function detail(account) {
  if (!account) return 'Reading account limits…'
  const lines = [`${account.label}${account.email ? ` · ${account.email}` : ''}`, account.plan ? `ChatGPT ${account.plan} · Codex allowance` : 'Codex allowance', 'Percentages USED (5-hour / weekly)']
  for (const w of account.windows || []) {
    const reset = w.reset_at ? new Date(w.reset_at * 1000).toLocaleString() : 'unknown'
    lines.push(`${w.label}: ${percent(w.used_percent)} used · resets ${reset}`)
  }
  if (account.error) lines.push(`${account.status === 'stale' ? 'STALE — last successful reading. ' : ''}${account.error}`)
  if (account.updated_at) lines.push(`Updated ${new Date(account.updated_at * 1000).toLocaleString()}`)
  lines.push('Click to refresh account usage')
  return lines.join('\n')
}
function Accounts({ ctx }) {
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
  return jsx('span', { style: { display: 'inline-flex', height: '100%', alignItems: 'center', gap: '4px' }, children: accounts.map(account => jsx(Tip, { label: jsx('span', { style: { whiteSpace: 'pre-line' }, children: detail(account) }), children: jsx('button', { type: 'button', disabled: isFetching || refreshing, onClick: refresh, 'aria-label': `${chipLabel(account)}, percentages used`, style: { height: '100%', padding: '0 6px', fontSize: '11px', whiteSpace: 'nowrap', color: account.status !== 'ok' ? 'var(--ui-badge-warning)' : 'var(--ui-text-secondary)' }, children: chipLabel(account) }) }, account.id)) })
}
export default {
  id: 'codex-accounts-usage', name: 'Codex Accounts Usage',
  register(ctx) { ctx.register({ id: 'accounts', area: 'statusBar.right', order: 131, render: () => jsx(Accounts, { ctx }) }) }
}
