import {useEffect,useMemo,useState} from 'react';
import {ArrowUpRight,Database,MapPin,Satellite,ShieldAlert} from 'lucide-react';
export type Observation={id:string;date:string;polarization:string;orbit:string;platform:string;url:string|null};
export type ObservationStore={region:string;latitude:number;longitude:number;start:string;end:string;updated_at:string;scenes:Observation[]};
export function loadObservations():ObservationStore|null{try{const value=localStorage.getItem('avenry-nasa-observations-v1');if(!value)return null;const data=JSON.parse(value) as ObservationStore;return Array.isArray(data.scenes)?data:null;}catch{return null;}}
export default function Observations(){
 const [data,setData]=useState<ObservationStore|null>(()=>loadObservations());
 const [filter,setFilter]=useState('');
 useEffect(()=>{const update=()=>setData(loadObservations());window.addEventListener('avenry:observations-updated',update);window.addEventListener('storage',update);return()=>{window.removeEventListener('avenry:observations-updated',update);window.removeEventListener('storage',update);};},[]);
 const shown=useMemo(()=>data?.scenes.filter(s=>(s.id+' '+s.date+' '+s.polarization+' '+s.orbit).toLowerCase().includes(filter.toLowerCase()))||[],[data,filter]);
 function download(){if(!data)return;const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='avenry-nasa-observations.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
 return <section style={{display:'grid',gap:18}}>
  <div style={{background:'#fff',padding:23,border:'1px solid #e1e7e1',borderRadius:10}}>
   <div style={{display:'flex',alignItems:'center',gap:10,marginBottom:9}}><Satellite size={21} color="#265d45"/><h2 style={{fontSize:19}}>Real NASA satellite observations</h2></div>
   <p style={{fontSize:13,lineHeight:1.8,color:'#66786d'}}>This is a record of satellite scenes returned by NASA Alaska Satellite Facility (ASF). It shows when and where Sentinel-1 radar observed a region. These are real acquisition records, not AI water detections.</p>
   {data?<div style={{display:'flex',flexWrap:'wrap',gap:12,marginTop:17}}>
    <span className="pill"><MapPin size={13}/> {data.region}</span><span className="pill">{data.start} to {data.end}</span><span className="pill">{data.scenes.length} scene records</span>
   </div>:<div className="warning-note" style={{marginTop:18}}>No NASA search has been saved in this browser. Go to Overview, choose a location and dates, then select Search NASA imagery. The returned records will appear here.</div>}
  </div>
  {data&&<div style={{background:'#fff',border:'1px solid #e1e7e1',borderRadius:10,padding:20}}>
   <div style={{display:'flex',flexWrap:'wrap',gap:12,alignItems:'center',justifyContent:'space-between',marginBottom:16}}>
    <div><h3 style={{fontSize:16}}>Acquisition records</h3><p style={{fontSize:11,color:'#718078',marginTop:6}}>Latest saved search · {new Date(data.updated_at).toLocaleString()} · Showing {shown.length} of {data.scenes.length}</p></div>
    <div style={{display:'flex',gap:8,flexWrap:'wrap'}}><input aria-label="Filter NASA observations" placeholder="Filter scene, date, orbit…" value={filter} onChange={e=>setFilter(e.target.value)} style={{padding:10,border:'1px solid #dfe7df',borderRadius:7}}/><button className="button secondary" onClick={download}><Database size={14}/> Export JSON</button></div>
   </div>
   {shown.length?<div className="table-wrap"><table><thead><tr><th>NASA SCENE</th><th>ACQUIRED</th><th>POLARIZATION</th><th>ORBIT</th><th>DATA</th></tr></thead><tbody>{shown.map((s,i)=><tr key={s.id+i}><td style={{maxWidth:260,overflowWrap:'anywhere'}}><strong>{s.id}</strong></td><td>{s.date||'Not supplied'}</td><td>{s.polarization}</td><td>{s.orbit}</td><td>{s.url?<a href={s.url} target="_blank" rel="noopener noreferrer" style={{color:'#265d45',textDecoration:'underline'}}>NASA <ArrowUpRight size={13} style={{display:'inline'}}/></a>:'Unavailable'}</td></tr>)}</tbody></table></div>:<div className="empty">No matching observations.</div>}
   <div style={{display:'flex',gap:9,alignItems:'start',background:'#f3f7f2',padding:13,borderRadius:8,marginTop:16,fontSize:12,color:'#52665a',lineHeight:1.6}}><ShieldAlert size={17} style={{flexShrink:0}}/> A NASA acquisition record means a satellite observed the region on that date. It does not establish water levels, flood extent, flood risk, or safety. Downloading radar imagery may require an Earthdata login.</div>
  </div>}
 </section>;
}
