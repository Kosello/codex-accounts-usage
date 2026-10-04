import fs from 'node:fs'
import assert from 'node:assert/strict'
const source = fs.readFileSync(new URL('../desktop/plugin.js', import.meta.url), 'utf8')
const transformed = source.replace(/^import .*\n/gm, '').replace(/export function /g, 'function ').replace('export default', 'const plugin =')
let refreshed = false
const accounts = [{id:'a',label:'Primary',status:'ok',windows:[{seconds:18000,used_percent:25,label:'5h'},{seconds:604800,used_percent:50,label:'Weekly'}]}, {id:'b',label:'Secondary',status:'ok',windows:[{seconds:18000,used_percent:20,label:'5h'},{seconds:604800,used_percent:3,label:'Weekly'}]}]
const jsx = (type, props, key) => ({type,props,key})
const sdk = {Tip:'Tip',useQuery:()=>({data:{accounts}}),useQueryClient:()=>({setQueryData:()=>{refreshed=true}}),host:{state:{profile:{get:()=> 'default'}},notify:()=>{}}}
const factory = new Function('Tip','useQuery','useQueryClient','host','jsx','useValue','useState', transformed + '; return {plugin,chipLabel,percent}')
const {plugin,chipLabel,percent} = factory(sdk.Tip,sdk.useQuery,sdk.useQueryClient,sdk.host,jsx,atom=>atom.get(),initial=>[initial,()=>{}])
assert.equal(percent(null),'n/a')
assert.equal(chipLabel(accounts[0]),'Codex Primary · 5h 25% / W 50%')
assert.equal(chipLabel({...accounts[0],status:'stale'}),'Codex Primary · 5h 25% / W 50% ⚠')
let contribution
const ctx = {source:'test', register:c=>{contribution=c},rest:async(path,opts)=>{assert.equal(path,'/refresh');assert.equal(opts.method,'POST');return {accounts}}}
plugin.register(ctx)
assert.equal(contribution.area,'statusBar.right')
const component = contribution.render()
const tree = component.type(component.props)
assert.equal(tree.props.children.length,2)
const labels = tree.props.children.map(t=>t.props.children.props.children)
assert.deepEqual(labels,['Codex Primary · 5h 25% / W 50%','Codex Secondary · 5h 20% / W 3%'])
await tree.props.children[0].props.children.props.onClick()
assert(refreshed)
console.log('Frontend: two chips, labels, stale indicator, registration and click-to-refresh verified.')
