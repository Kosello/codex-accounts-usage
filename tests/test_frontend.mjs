import fs from 'node:fs'
import assert from 'node:assert/strict'
const source = fs.readFileSync(new URL('../desktop/plugin.js', import.meta.url), 'utf8')
const transformed = source.replace(/^import .*\n/gm, '').replace(/export function /g, 'function ').replace('export default', 'const plugin =')
let refreshed = false
const accounts = [{id:'a',label:'Primary',email:'primary@example.com',status:'ok',windows:[{seconds:18000,used_percent:25,label:'5h',reset_at:1800000000},{seconds:604800,used_percent:50,label:'Weekly'}]}, {id:'b',label:'Secondary',status:'stale',windows:[{seconds:18000,used_percent:20,label:'5h'},{seconds:604800,used_percent:3,label:'Weekly'}]}]
const jsx = (type, props, key) => ({type,props,key})
const atom = initial => { let value = initial; return {get:()=>value,set:next=>{value=next}} }
const sdk = {Tip:'Tip',Switch:'Switch',atom,PALETTE_AREA:'palette',useQuery:()=>({data:{accounts}}),useQueryClient:()=>({setQueryData:()=>{refreshed=true}}),host:{state:{profile:atom('default')},notify:()=>{}}}
const factory = new Function(...Object.keys(sdk),'jsx','useValue','useState', transformed + '; return {plugin,chipLabel,percent,createSettings}')
const {plugin,chipLabel,percent,createSettings} = factory(...Object.values(sdk),jsx,a=>a.get(),initial=>[initial,()=>{}])
assert.equal(percent(null),'n/a')
assert.equal(chipLabel(accounts[0]),'25% / 50%')
assert.equal(chipLabel(accounts[1]),'20% / 3% ⚠')
assert.equal(chipLabel(accounts[0],false),'Codex Primary · 5h 25% / W 50%')
assert.equal(chipLabel(accounts[1],false),'Codex Secondary · 5h 20% / W 3% ⚠')
const contributions = []
const saved = new Map()
const storage = {get:key=>saved.get(key),set:(key,value)=>saved.set(key,value)}
const ctx = {source:'test',storage,register:c=>contributions.push(c),rest:async(path,opts)=>{assert.equal(path,'/refresh');assert.equal(opts.method,'POST');return {accounts}}}
plugin.register(ctx)
const status = contributions.find(c=>c.area==='statusBar.right')
const pane = contributions.find(c=>c.area==='panes')
const palette = contributions.find(c=>c.area==='palette')
const render = c => { const component = c.render(); return component.type(component.props) }
const labels = () => render(status).props.children.map(t=>t.props.children.props.children)
assert.deepEqual(labels(),['25% / 50%','20% / 3% ⚠'])
assert.equal(pane.title,'Codex Usage Settings')
const toggle = render(pane).props.children[0].props.children[0]
assert.equal(toggle.props.checked,true)
toggle.props.onCheckedChange(false)
assert.equal(saved.get('compact'),false)
assert.deepEqual(labels(),['Codex Primary · 5h 25% / W 50%','Codex Secondary · 5h 20% / W 3% ⚠'])
const reloaded = createSettings(ctx)
await Promise.resolve()
assert.equal(reloaded.compact.get(),false)
palette.data.run()
assert.equal(saved.get('compact'),true)
assert.deepEqual(labels(),['25% / 50%','20% / 3% ⚠'])
const tree = render(status)
assert.equal(tree.props.children.length,2)
const hover = tree.props.children[0].props.label.props.children
for (const text of ['Codex','Primary','primary@example.com','5-hour / weekly','5h: 25% used','Weekly: 50% used','resets','Click to refresh']) assert(hover.includes(text),text)
assert(tree.props.children[1].props.label.props.children.includes('STALE'))
assert(tree.props.children[0].props.children.props['aria-label'].includes('Codex Primary'))
await tree.props.children[0].props.children.props.onClick()
assert(refreshed)
for (const value of [undefined,null,'false',{},1]) {
  const settings = createSettings({storage:{get:()=>value}})
  await Promise.resolve()
  assert.equal(settings.compact.get(),true)
}
for (const get of [()=>{throw Error('read')},()=>Promise.reject(Error('read'))]) {
  const settings = createSettings({storage:{get}})
  await Promise.resolve(); await Promise.resolve()
  assert.equal(settings.compact.get(),true)
}
let resolveLoad
const late = createSettings({storage:{get:()=>new Promise(resolve=>{resolveLoad=resolve}),set:()=>{}}})
late.setCompact(false)
resolveLoad(true)
await Promise.resolve()
assert.equal(late.compact.get(),false)
console.log('Frontend passed: compact/full labels, stale warning, settings pane, palette toggle, persistence/reload, invalid/failed/late storage, hover identity/windows/resets, refresh.')
