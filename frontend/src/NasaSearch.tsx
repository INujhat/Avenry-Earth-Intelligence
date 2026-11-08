import {Suspense,lazy,useMemo} from 'react';
import type {Place} from './LocationExplorer';
const LocationExplorer=lazy(()=>import('./LocationExplorer'));
import {useState} from 'react';
type Feature={properties?:Record<string,unknown>;geometry?:unknown};
type SearchResult={features?:Feature[]};
const regions=[{name:'Sylhet, Bangladesh',lat:24.89,lon:91.87},{name:'Houston, Texas',lat:29.76,lon:-95.37},{name:'New Orleans, Louisiana',lat:29.95,lon:-90.07},{name:'Kerala, India',lat:10.5,lon:76.5}];
function iso(d:Date){return d.toISOString().slice(0,10);}
export default function NasaSearch(){
 const [region,setRegion]=useState(0),[customLat,setCustomLat]=useState(''),[customLon,setCustomLon]=useState(''),[customName,setCustomName]=useState('My location'),[start,setStart]=useState('2022-06-01'),[end,setEnd]=useState('2022-06-30');
 const [items,setItems]=useState<Feature[]>([]),[busy,setBusy]=useState(false),[error,setError]=useState(''),[searched,setSearched]=useState(false);
 const custom=region===-1;
 const lat=Number(customLat),lon=Number(customLon);
 const validPlace=!custom||(customLat.trim()!==''&&customLon.trim()!==''&&Number.isFinite(lat)&&Number.isFinite(lon)&&lat>=-90&&lat<=90&&lon>=-180&&lon<=180);
 const selected:Place=custom?{name:customName.trim()||'Custom location',lat:validPlace?lat:0,lon:validPlace?lon:0}:regions[region];
 const mapLink='https://www.openstreetmap.org/?mlat='+selected.lat+'&mlon='+selected.lon+'#map=10/'+selected.lat+'/'+selected.lon;
 const footprints=useMemo<GeoJSON.FeatureCollection>(()=>({type:'FeatureCollection',features:items.filter((f):f is Feature & {geometry:GeoJSON.Geometry}=>!!f.geometry&&typeof f.geometry==='object'&&'type' in f.geometry).map(f=>({type:'Feature',properties:{},geometry:f.geometry}))}),[items]);
 const wkt=(()=>{const {lon,lat}=selected,d=.18;return 'POLYGON(('+[[lon-d,lat-d],[lon+d,lat-d],[lon+d,lat+d],[lon-d,lat+d],[lon-d,lat-d]].map(p=>p.join(' ')).join(',')+'))';})();
 const vertex='https://search.asf.alaska.edu/#/?dataset=Sentinel-1&polygon='+encodeURIComponent(wkt)+'&start='+start+'&end='+end;
 async function search(){
  setBusy(true);setError('');setItems([]);setSearched(true);
  try{
   if(!validPlace)throw Error('Enter valid latitude (−90 to 90) and longitude (−180 to 180) for your location.');
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
   <label style={{display:'grid',gap:6,fontSize:11}}>Region<select value={region} onChange={e=>setRegion(Number(e.target.value))} style={{padding:10,border:'1px solid #dfe7df',borderRadius:5}}>{regions.map((r,i)=><option value={i} key={r.name}>{r.name}</option>)}<option value={-1}>Custom location (coordinates)</option></select></label>
   {custom&&<><label style={{display:'grid',gap:6,fontSize:11}}>Location name<input value={customName} onChange={e=>setCustomName(e.target.value)} placeholder="My neighborhood" style={{padding:9,border:'1px solid #dfe7df',borderRadius:5}}/></label><label style={{display:'grid',gap:6,fontSize:11}}>Latitude<input type="number" step="any" min="-90" max="90" value={customLat} onChange={e=>setCustomLat(e.target.value)} placeholder="e.g. 41.8781" style={{width:125,padding:9,border:'1px solid #dfe7df',borderRadius:5}}/></label><label style={{display:'grid',gap:6,fontSize:11}}>Longitude<input type="number" step="any" min="-180" max="180" value={customLon} onChange={e=>setCustomLon(e.target.value)} placeholder="e.g. -87.6298" style={{width:125,padding:9,border:'1px solid #dfe7df',borderRadius:5}}/></label></>}
   <label style={{display:'grid',gap:6,fontSize:11}}>From<input type="date" value={start} onChange={e=>setStart(e.target.value)} style={{padding:9,border:'1px solid #dfe7df',borderRadius:5}}/></label>
   <label style={{display:'grid',gap:6,fontSize:11}}>To<input type="date" value={end} onChange={e=>setEnd(e.target.value)} style={{padding:9,border:'1px solid #dfe7df',borderRadius:5}}/></label>
   <button className="button primary" onClick={search} disabled={busy||!validPlace}>{busy?'Searching NASA…':'Search NASA imagery'}</button>
  </div>
  <div style={{marginTop:18,marginBottom:14}}>{validPlace?<Suspense fallback={<div style={{padding:30,background:'#edf2ed'}}>Loading interactive location map…</div>}><LocationExplorer place={selected} footprints={footprints}/></Suspense>:<div role="status" style={{padding:24,background:'#f4f7f4',borderRadius:8}}>Enter valid coordinates to display your location on the map.</div>}<p style={{fontSize:11,color:'#6f8075',marginTop:7}}>Live geographic basemap by OpenStreetMap. Search NASA to display returned satellite scene footprints; the basemap itself is not Sentinel-1 imagery.</p></div>
  <div style={{display:'flex',gap:14,flexWrap:'wrap',fontSize:12,margin:'10px 0 14px'}}><a href={mapLink} target="_blank" rel="noopener noreferrer" style={{color:'#265d45',textDecoration:'underline'}}>Open full map ↗</a><button type="button" onClick={()=>navigator.clipboard?.writeText(mapLink).catch(()=>{})} style={{color:'#265d45',textDecoration:'underline',background:'none',padding:0}}>Copy location map link</button></div>
  <div style={{background:'#f1f6f0',border:'1px solid #dce9dc',borderRadius:9,padding:15,marginBottom:12}}><strong style={{fontSize:13}}>How can this help in everyday life?</strong><p style={{fontSize:12,lineHeight:1.7,marginTop:7}}>Explore your neighborhood or a place your family cares about, inspect the surrounding landscape, and discover when radar satellite observations were collected. Useful for students, travelers, community researchers, and anyone curious about changes near rivers or coastlines. A satellite footprint is not a flood alert or a statement that a location is safe.</p></div>
  {error&&<p role="alert" style={{color:'#a54b35',fontSize:12,marginTop:14}}>{error}</p>}
  {searched&&!busy&&!error&&<p style={{fontSize:12,marginTop:15}}>{items.length?items.length+' matching scene(s) returned (maximum 25).':'No matching scenes returned. Try a wider date range.'}</p>}
  {items.length>0&&<div style={{maxHeight:240,overflowY:'auto',marginTop:10}}>{items.map((f,i)=>{const p=f.properties||{};const id=String(p.sceneName||p.fileID||p.granuleName||'Sentinel-1 scene '+(i+1));const url=typeof p.url==='string'&&p.url.startsWith('https://')?p.url:null;return <div key={i} style={{padding:'10px 0',borderBottom:'1px solid #edf1ed',fontSize:11,overflowWrap:'anywhere'}}><strong>{id}</strong><span style={{display:'block',color:'#75817b',marginTop:3}}>{String(p.startTime||p.stopTime||'Date not provided')} · {String(p.polarization||'Radar')}</span>{url&&<a href={url} target="_blank" rel="noreferrer" style={{color:'#265d45',textDecoration:'underline'}}>Open original NASA download (Earthdata login may be required)</a>}</div>;})}</div>}
  <a href={vertex} target="_blank" rel="noreferrer" style={{display:'inline-block',fontSize:12,color:'#265d45',textDecoration:'underline',marginTop:15}}>Open this region and date range in NASA ASF Vertex ↗</a>
  <p style={{fontSize:10,color:'#7c887f',marginTop:10}}>NASA/ESA Sentinel-1 observations · This search does not claim water detection or model readiness.</p>
 </section>;
}
