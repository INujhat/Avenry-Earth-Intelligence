import {useEffect,useState} from 'react';
import {loadObservations} from './Observations';

type Alert={id:string;properties:{event?:string;headline?:string;severity?:string;urgency?:string;description?:string;instruction?:string;effective?:string;expires?:string;areaDesc?:string;web?:string;senderName?:string}};
type AlertResponse={features?:Alert[]};
type Gauge={id:string;name:string;latitude:number;longitude:number;status?:{observed?:{primary?:number;primaryUnit?:string;flood?:{stage?:number}}}};
const presets=[{name:'Houston, Texas',lat:29.76,lon:-95.37},{name:'New Orleans, Louisiana',lat:29.95,lon:-90.07},{name:'Chicago, Illinois',lat:41.88,lon:-87.63}];
function date(s?:string){if(!s)return 'Not provided';const d=new Date(s);return Number.isNaN(d.valueOf())?'Not provided':d.toLocaleString();}
export default function FloodConditions(){
 const [saved,setSaved]=useState(()=>loadObservations());
 const [selection,setSelection]=useState('saved');
 const [alerts,setAlerts]=useState<Alert[]>([]),[busy,setBusy]=useState(false),[error,setError]=useState(''),[checked,setChecked]=useState('');
 useEffect(()=>{const fn=()=>setSaved(loadObservations());window.addEventListener('avenry:observations-updated',fn);return()=>window.removeEventListener('avenry:observations-updated',fn);},[]);
 const place=selection==='saved'?(saved?{name:saved.region,lat:saved.latitude,lon:saved.longitude}:null):presets[Number(selection)];
 const usa=place&&place.lat>=18&&place.lat<=72&&place.lon>=-180&&place.lon<=-65;
 async function load(){
  if(!place||!usa)return;setBusy(true);setError('');setAlerts([]);setChecked('');
  try{
   const url='https://api.weather.gov/alerts/active?point='+place.lat.toFixed(4)+','+place.lon.toFixed(4);
   const res=await fetch(url,{headers:{Accept:'application/geo+json'}});
   if(!res.ok)throw Error('National Weather Service returned HTTP '+res.status);
   const data=await res.json() as AlertResponse;
   if(!Array.isArray(data.features))throw Error('Unexpected alert response');
   setAlerts(data.features);setChecked(new Date().toISOString());
  }catch(e){setError(e instanceof Error?e.message:'Unable to retrieve alerts');}finally{setBusy(false);}
 }
 function download(){
  if(!place||!checked)return;
  const report={title:'Avenry — Official Weather Alert Snapshot',location:place,checked_at:checked,source:'https://api.weather.gov/alerts/active',scope:'Active NWS alerts at a point. Not a flood prediction, satellite detection, or safety clearance.',alerts:alerts.map(a=>({event:a.properties.event,headline:a.properties.headline,severity:a.properties.severity,urgency:a.properties.urgency,area:a.properties.areaDesc,effective:a.properties.effective,expires:a.properties.expires,description:a.properties.description,instruction:a.properties.instruction}))};
  const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));
  const link=document.createElement('a');link.href=url;link.download='avenry-weather-alert-snapshot.json';link.click();URL.revokeObjectURL(url);
 }
 return <section style={{display:'grid',gap:18}}>
  <div style={{background:'#fff',border:'1px solid #e1e7e1',borderRadius:10,padding:23}}>
   <span className="eyebrow green">OFFICIAL DATA / UNITED STATES</span>
   <h2 style={{fontSize:21,margin:'9px 0'}}>Weather and flood alerts</h2>
   <p style={{fontSize:13,color:'#66786d',lineHeight:1.8}}>Check active National Weather Service alerts for a selected U.S. location. These are official weather alerts, not Avenry AI predictions or a guarantee of safety.</p>
   <div style={{display:'flex',alignItems:'end',gap:12,flexWrap:'wrap',marginTop:17}}>
    <label style={{display:'grid',gap:6,fontSize:12}}>Location<select value={selection} onChange={e=>{setSelection(e.target.value);setChecked('');setAlerts([]);setError('');}} style={{padding:10,border:'1px solid #dfe7df',borderRadius:6}}><option value="saved" disabled={!saved}>{saved?'Latest NASA search: '+saved.region:'Search NASA first to use your location'}</option>{presets.map((p,i)=><option key={p.name} value={String(i)}>{p.name}</option>)}</select></label>
    <button className="button primary" disabled={!place||!usa||busy} onClick={load}>{busy?'Checking official alerts…':'Check active alerts'}</button>
    {checked&&<button className="button secondary" onClick={download}>Export alert snapshot (JSON)</button>}
   </div>
   {!place&&<p style={{fontSize:12,marginTop:12}}>Select a U.S. preset, or run a NASA location search first.</p>}
   {place&&!usa&&<p style={{fontSize:12,marginTop:12}}>NWS alerts in this module cover U.S. locations only. Select a U.S. preset or search a U.S. location.</p>}
   {error&&<p role="alert" style={{color:'#a54b35',marginTop:15,fontSize:12}}>{error}. Try again later or consult the official NWS site.</p>}
   {checked&&<p role="status" style={{marginTop:17,fontSize:12}}>Checked {date(checked)} · {alerts.length} active alert(s) returned for this point. {alerts.length===0?'No active alerts returned does not mean conditions are safe.':''}</p>}
   {alerts.length>0&&<div style={{display:'grid',gap:12,marginTop:15}}>{alerts.map((a,i)=><article key={a.id||i} style={{padding:16,border:'1px solid #e1e7e1',borderRadius:8}}><div style={{display:'flex',justifyContent:'space-between',gap:12,flexWrap:'wrap'}}><strong style={{fontSize:15}}>{a.properties.event||'Weather alert'}</strong><span style={{fontSize:11,color:'#815b3c'}}>{a.properties.severity||'Severity unknown'}</span></div><p style={{fontSize:12,marginTop:7}}>{a.properties.headline}</p><p style={{fontSize:11,color:'#66786d',marginTop:8}}>Area: {a.properties.areaDesc||'Not specified'} · Expires: {date(a.properties.expires)}</p>{a.properties.instruction&&<details style={{marginTop:10,fontSize:12}}><summary>Official safety instructions</summary><p style={{whiteSpace:'pre-wrap',lineHeight:1.6,marginTop:8}}>{a.properties.instruction}</p></details>}</article>)}</div>}
   <p style={{fontSize:11,color:'#748079',lineHeight:1.7,marginTop:16}}>Source: <a href="https://www.weather.gov/" target="_blank" rel="noreferrer" style={{textDecoration:'underline',color:'#265d45'}}>National Weather Service</a> via api.weather.gov. Alerts change rapidly. For emergencies, follow local authorities and official warnings. The absence of alerts is not proof of safety.</p>
  </div>
  <div style={{background:'#fff',border:'1px solid #e1e7e1',borderRadius:10,padding:22}}>
   <h3 style={{fontSize:17}}>Historical flood records</h3><p style={{fontSize:12,color:'#66786d',lineHeight:1.8,marginTop:9}}>Explore NOAA's documented storm and flood events. This is a source link, not yet a location-filtered event database inside Avenry. Event records should not be interpreted as satellite-detected inundation.</p>
   <a href="https://www.ncdc.noaa.gov/stormevents/" target="_blank" rel="noreferrer" style={{fontSize:12,color:'#265d45',textDecoration:'underline',display:'inline-block',marginTop:12}}>Explore NOAA Storm Events Database ↗</a>
  </div>
 </section>;
}
