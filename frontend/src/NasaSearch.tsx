import {Suspense,lazy,useMemo} from 'react';
import type {Place} from './LocationExplorer';
const LocationExplorer=lazy(()=>import('./LocationExplorer'));
import {useState} from 'react';
type Feature={properties?:Record<string,unknown>;geometry?:unknown};
type SearchResult={features?:Feature[]};
const regions=[
 {name:'Sylhet, Bangladesh',lat:24.89,lon:91.87},
 {name:'Houston, Texas, USA',lat:29.76,lon:-95.37},
 {name:'New Orleans, Louisiana, USA',lat:29.95,lon:-90.07},
 {name:'Kerala, India',lat:10.5,lon:76.5},
 {name:'Dhaka, Bangladesh',lat:23.81,lon:90.41},
 {name:'Sunamganj, Bangladesh',lat:25.07,lon:91.40},
 {name:'Chattogram, Bangladesh',lat:22.36,lon:91.78},
 {name:'Chicago, Illinois, USA',lat:41.88,lon:-87.63},
 {name:'Miami, Florida, USA',lat:25.76,lon:-80.19},
 {name:'New York City, New York, USA',lat:40.71,lon:-74.01},
 {name:'Sacramento, California, USA',lat:38.58,lon:-121.49},
 {name:'Richmond, Virginia, USA',lat:37.54,lon:-77.44},
 {name:'Jakarta, Indonesia',lat:-6.21,lon:106.85},
 {name:'Manila, Philippines',lat:14.60,lon:120.98},
 {name:'Bangkok, Thailand',lat:13.76,lon:100.50},
 {name:'Lahore, Pakistan',lat:31.55,lon:74.34},
 {name:'Karachi, Pakistan',lat:24.86,lon:67.01},
 {name:'Chennai, India',lat:13.08,lon:80.27},
 {name:'Mumbai, India',lat:19.08,lon:72.88},
 {name:'Nairobi, Kenya',lat:-1.29,lon:36.82},
 {name:'Lagos, Nigeria',lat:6.52,lon:3.38},
 {name:'Beira, Mozambique',lat:-19.84,lon:34.84},
 {name:'Venice, Italy',lat:45.44,lon:12.33},
 {name:'Kaiserslautern, Germany',lat:49.44,lon:7.77},
 {name:'Brisbane, Australia',lat:-27.47,lon:153.03},
 {name:'Porto Alegre, Brazil',lat:-30.03,lon:-51.23}
];
export default function NasaSearch(){
 const [region,setRegion]=useState(0),[customLat,setCustomLat]=useState(''),[customLon,setCustomLon]=useState(''),[customName,setCustomName]=useState('My location'),[start,setStart]=useState('2022-06-01'),[end,setEnd]=useState('2022-06-30');
 const [limit,setLimit]=useState(100),[page,setPage]=useState(0);
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
  setBusy(true);setError('');setItems([]);setPage(0);setSearched(true);
  try{
   if(!validPlace)throw Error('Enter valid latitude (−90 to 90) and longitude (−180 to 180) for your location.');
   if(!start||!end||start>end)throw Error('Choose a valid start and end date.');
   const params=new URLSearchParams({platform:'Sentinel-1',processingLevel:'GRD_HD',intersectsWith:wkt,start,end,output:'geojson',maxResults:String(limit)});
   const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),25000);let response:Response;try{response=await fetch('https://api.daac.asf.alaska.edu/services/search/param?'+params.toString(),{headers:{Accept:'application/geo+json,application/json'},signal:controller.signal});}finally{clearTimeout(timeout);}
   if(!response.ok)throw Error('NASA search returned HTTP '+response.status);
   const data=await response.json() as SearchResult;
   if(!Array.isArray(data.features))throw Error('NASA returned an unexpected scene format.');
   setItems(data.features);setPage(0);
   try{const saved={region:selected.name,latitude:selected.lat,longitude:selected.lon,start,end,updated_at:new Date().toISOString(),scenes:data.features.map((f,i)=>{const p=f.properties||{};return {id:String(p.sceneName||p.fileID||p.granuleName||'Sentinel-1 scene '+(i+1)),date:String(p.startTime||p.stopTime||''),polarization:String(p.polarization||'Unknown'),orbit:String(p.flightDirection||'Unknown'),platform:String(p.platform||'Sentinel-1'),url:typeof p.url==='string'&&p.url.startsWith('https://')?p.url:null};})};localStorage.setItem('avenry-nasa-observations-v1',JSON.stringify(saved));window.dispatchEvent(new Event('avenry:observations-updated'));}catch{/* Storage is optional; NASA search results remain visible here. */}
  }catch(e){setError((e instanceof Error?e.message:'NASA search unavailable')+'. If the browser blocks NASA requests or the service is slow, use the NASA ASF Vertex link below.');}
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
   <label style={{display:'grid',gap:6,fontSize:11}}>Maximum records<select value={limit} onChange={e=>setLimit(Number(e.target.value))} style={{padding:10,border:'1px solid #dfe7df',borderRadius:5}}><option value={25}>25</option><option value={100}>100</option><option value={250}>250</option></select></label>
   <button className="button primary" onClick={search} disabled={busy||!validPlace}>{busy?'Searching NASA…':'Search NASA imagery'}</button>
  </div>
  <div role="status" aria-live="polite" style={{padding:16,marginTop:16,background:busy?'#eaf2ed':error?'#fff2eb':'#f1f6f0',border:'1px solid #dce9dc',borderRadius:8,fontSize:13,lineHeight:1.7}}>{busy?'Searching NASA ASF for real satellite acquisition records…':error?'Search failed: '+error:searched?items.length?`${items.length} real NASA satellite record(s) found. See the results directly below the map. These are acquisition records, not flood predictions.`:'NASA returned no records for this date range. Try a longer date range or a different location.':'Choose a region and date range, then search NASA. The map below is a geographic basemap; actual satellite records appear after a successful search.'}</div>
  {items.length>0&&<div style={{background:'#fff',border:'1px solid #dce9dc',borderRadius:8,padding:14,marginTop:12}}><strong style={{fontSize:13}}>NASA search results ({items.length}{items.length===limit?' · search limit reached':''})</strong><p style={{fontSize:11,color:'#66786d',marginTop:6}}>The returned scenes are listed in Observations and below the map. Satellite discovery does not activate the separate AI water-analysis model.</p></div>}
  <div style={{marginTop:18,marginBottom:14}}>{validPlace?<Suspense fallback={<div style={{padding:30,background:'#edf2ed'}}>Loading interactive location map…</div>}><LocationExplorer place={selected} footprints={footprints}/></Suspense>:<div role="status" style={{padding:24,background:'#f4f7f4',borderRadius:8}}>Enter valid coordinates to display your location on the map.</div>}<p style={{fontSize:11,color:'#6f8075',marginTop:7}}>Live geographic basemap by OpenStreetMap. Search NASA to display returned satellite scene footprints; the basemap itself is not Sentinel-1 imagery.</p></div>
  <div style={{display:'flex',gap:14,flexWrap:'wrap',fontSize:12,margin:'10px 0 14px'}}><a href={mapLink} target="_blank" rel="noopener noreferrer" style={{color:'#265d45',textDecoration:'underline'}}>Open full map ↗</a><button type="button" onClick={()=>navigator.clipboard?.writeText(mapLink).catch(()=>{})} style={{color:'#265d45',textDecoration:'underline',background:'none',padding:0}}>Copy location map link</button></div>
  <div style={{background:'#f1f6f0',border:'1px solid #dce9dc',borderRadius:9,padding:15,marginBottom:12}}><strong style={{fontSize:13}}>How can this help in everyday life?</strong><p style={{fontSize:12,lineHeight:1.7,marginTop:7}}>Explore your neighborhood or a place your family cares about, inspect the surrounding landscape, and discover when radar satellite observations were collected. Useful for students, travelers, community researchers, and anyone curious about changes near rivers or coastlines. A satellite footprint is not a flood alert or a statement that a location is safe.</p></div>
  {error&&<p role="alert" style={{color:'#a54b35',fontSize:12,marginTop:14}}>{error}</p>}
  {searched&&!busy&&!error&&<p style={{fontSize:12,marginTop:15}}>{items.length?items.length+' matching scene(s) returned (requested maximum '+limit+').':'No matching scenes returned. Try a wider date range.'}</p>}
  {items.length>0&&<div style={{marginTop:12}}><div style={{display:'flex',alignItems:'center',justifyContent:'space-between',gap:12,flexWrap:'wrap',fontSize:12}}><span>Showing {page*25+1}–{Math.min((page+1)*25,items.length)} of {items.length} records</span><div style={{display:'flex',gap:8}}><button className="button secondary" disabled={page===0} onClick={()=>setPage(p=>Math.max(0,p-1))}>Previous</button><button className="button secondary" disabled={(page+1)*25>=items.length} onClick={()=>setPage(p=>p+1)}>Next</button></div></div><div style={{maxHeight:270,overflowY:'auto',marginTop:10}}>{items.slice(page*25,(page+1)*25).map((f,i)=>{const p=f.properties||{};const id=String(p.sceneName||p.fileID||p.granuleName||'Sentinel-1 scene '+(i+1));const url=typeof p.url==='string'&&p.url.startsWith('https://')?p.url:null;return <div key={i} style={{padding:'10px 0',borderBottom:'1px solid #edf1ed',fontSize:11,overflowWrap:'anywhere'}}><strong>{id}</strong><span style={{display:'block',color:'#75817b',marginTop:3}}>{String(p.startTime||p.stopTime||'Date not provided')} · {String(p.polarization||'Radar')}</span>{url&&<a href={url} target="_blank" rel="noreferrer" style={{color:'#265d45',textDecoration:'underline'}}>Open original NASA download (Earthdata login may be required)</a>}</div>;})}</div></div>}
  <a href={vertex} target="_blank" rel="noreferrer" style={{display:'inline-block',fontSize:12,color:'#265d45',textDecoration:'underline',marginTop:15}}>Open this region and date range in NASA ASF Vertex ↗</a>
  <p style={{fontSize:10,color:'#7c887f',marginTop:10}}>NASA/ESA Sentinel-1 observations · Up to 250 records per request, not necessarily all available acquisitions. This search does not claim water detection or model readiness.</p>
 </section>;
}
