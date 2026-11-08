import {Suspense,lazy,useMemo} from 'react';
import type {Place} from './LocationExplorer';
const LocationExplorer=lazy(()=>import('./LocationExplorer'));
import {useState} from 'react';
type Feature={properties?:Record<string,unknown>;geometry?:unknown};
type SearchResult={features?:Feature[]};
const regions=[{name:'Sylhet, Bangladesh',lat:24.89,lon:91.87},{name:'Houston, Texas',lat:29.76,lon:-95.37},{name:'New Orleans, Louisiana',lat:29.95,lon:-90.07},{name:'Kerala, India',lat:10.5,lon:76.5}];
function iso(d:Date){return d.toISOString().slice(0,10);}
export default function NasaSearch(){
 const [region,setRegion]=useState(0),[start,setStart]=useState('2022-06-01'),[end,setEnd]=useState('2022-06-30');
 const [items,setItems]=useState<Feature[]>([]),[busy,setBusy]=useState(false),[error,setError]=useState(''),[searched,setSearched]=useState(false);
 const selected:Place=regions[region];
 const footprints=useMemo<GeoJSON.FeatureCollection>(()=>({type:'FeatureCollection',features:items.filter((f):f is Feature & {geometry:GeoJSON.Geometry}=>!!f.geometry&&typeof f.geometry==='object'&&'type' in f.geometry).map(f=>({type:'Feature',properties:{},geometry:f.geometry}))}),[items]);
 const wkt=(()=>{const {lon,lat}=selected,d=.18;return 'POLYGON(('+[[lon-d,lat-d],[lon+d,lat-d],[lon+d,lat+d],[lon-d,lat+d],[lon-d,lat-d]].map(p=>p.join(' ')).join(',')+'))';})();
 const vertex='https://search.asf.alaska.edu/#/?dataset=Sentinel-1&polygon='+encodeURIComponent(wkt)+'&start='+start+'&end='+end;
 async function search(){
  setBusy(true);setError('');setItems([]);setSearched(true);
  try{
   if(!start||!end||start>end)throw Error('Choose a valid start and end date.');
   const params=new URLSearchParams({platform:'Sentinel-1',processingLevel:'GRD_HD',intersectsWith:wkt,start,end,output:'geojson',maxResults:'25'});
   const response=await fetch('https://api.daac.asf.alaska.edu/services/search/param?'+params.toString(),{headers:{Accept:'application/geo+json,application/json'}});
   if(!response.ok)throw Error('NASA search returned HTTP '+response.status);
   const data=await response.json() as SearchResult;
   if(!Array.isArray(data.features))throw Error('NASA returned an unexpected scene format.');
   setItems(data.features);
  }catch(e){setError((e instanceof Error?e.message:'NASA search unavailable')+'. You can continue in NASA ASF Vertex using the link below.');}
  finally{setBusy(false);}
 }
 return <section style={{background:'#fff',border:'1px solid #dfe7df',borderRadius:10,padding:22,marginBottom:28}}>
  <span className="eyebrow green">NASA EARTHDATA / LIVE SCENE DISCOVERY</span>
  <h2 style={{fontSize:20,margin:'9px 0'}}>Find real Sentinel-1 radar scenes</h2>
  <p style={{fontSize:12,color:'#6f8075',lineHeight:1.7,marginBottom:18}}>Search NASA ASF directly. Scene discovery is separate from AI inference: raw GRD products must be calibrated, georeferenced, and converted to the model's VV/VH inputs before analysis.</p>
  <div style={{display:'flex',gap:12,flexWrap:'wrap',alignItems:'end'}}>
   <label style={{display:'grid',gap:6,fontSize:11}}>Region<select value={region} onChange={e=>setRegion(Number(e.target.value))} style={{padding:10,border:'1px solid #dfe7df',borderRadius:5}}>{regions.map((r,i)=><option value={i} key={r.name}>{r.name}</option>)}</select></label>
   <label style={{display:'grid',gap:6,fontSize:11}}>From<input type="date" value={start} onChange={e=>setStart(e.target.value)} style={{padding:9,border:'1px solid #dfe7df',borderRadius:5}}/></label>
   <label style={{display:'grid',gap:6,fontSize:11}}>To<input type="date" value={end} onChange={e=>setEnd(e.target.value)} style={{padding:9,border:'1px solid #dfe7df',borderRadius:5}}/></label>
   <button className="button primary" onClick={search} disabled={busy}>{busy?'Searching NASA…':'Search NASA imagery'}</button>
  </div>
  <div style={{marginTop:18,marginBottom:14}}><Suspense fallback={<div style={{padding:30,background:'#edf2ed'}}>Loading interactive location map…</div>}><LocationExplorer place={selected} footprints={footprints}/></Suspense><p style={{fontSize:11,color:'#6f8075',marginTop:7}}>Live geographic basemap by OpenStreetMap. Search NASA to display returned satellite scene footprints; the basemap itself is not Sentinel-1 imagery.</p></div>
  {error&&<p role="alert" style={{color:'#a54b35',fontSize:12,marginTop:14}}>{error}</p>}
  {searched&&!busy&&!error&&<p style={{fontSize:12,marginTop:15}}>{items.length?items.length+' matching scene(s) returned (maximum 25).':'No matching scenes returned. Try a wider date range.'}</p>}
  {items.length>0&&<div style={{maxHeight:240,overflowY:'auto',marginTop:10}}>{items.map((f,i)=>{const p=f.properties||{};const id=String(p.sceneName||p.fileID||p.granuleName||'Sentinel-1 scene '+(i+1));const url=typeof p.url==='string'&&p.url.startsWith('https://')?p.url:null;return <div key={i} style={{padding:'10px 0',borderBottom:'1px solid #edf1ed',fontSize:11,overflowWrap:'anywhere'}}><strong>{id}</strong><span style={{display:'block',color:'#75817b',marginTop:3}}>{String(p.startTime||p.stopTime||'Date not provided')} · {String(p.polarization||'Radar')}</span>{url&&<a href={url} target="_blank" rel="noreferrer" style={{color:'#265d45',textDecoration:'underline'}}>Open original NASA download (Earthdata login may be required)</a>}</div>;})}</div>}
  <a href={vertex} target="_blank" rel="noreferrer" style={{display:'inline-block',fontSize:12,color:'#265d45',textDecoration:'underline',marginTop:15}}>Open this region and date range in NASA ASF Vertex ↗</a>
  <p style={{fontSize:10,color:'#7c887f',marginTop:10}}>NASA/ESA Sentinel-1 observations · This search does not claim water detection or model readiness.</p>
 </section>;
}
