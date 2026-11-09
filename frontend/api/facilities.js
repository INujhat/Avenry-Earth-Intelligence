/** Same-origin Vercel function. Avoid browser CORS restrictions on public Overpass instances. */
export default async function handler(req,res){
 res.setHeader('Cache-Control','public, s-maxage=300, stale-while-revalidate=600');
 if(req.method!=='GET')return res.status(405).json({error:'Method not allowed'});
 const lat=Number(req.query.lat),lon=Number(req.query.lon),radius=Number(req.query.radius);
 if(!Number.isFinite(lat)||Math.abs(lat)>90||!Number.isFinite(lon)||Math.abs(lon)>180||![2000,5000,10000].includes(radius))return res.status(400).json({error:'Invalid location or radius'});
 const query='[out:json][timeout:12];(nwr["amenity"~"^(hospital|clinic|pharmacy|shelter|police|fire_station)$"](around:'+radius+','+lat+','+lon+');nwr["healthcare"~"^(hospital|clinic)$"](around:'+radius+','+lat+','+lon+');nwr["office"~"^(ngo|charity)$"](around:'+radius+','+lat+','+lon+');nwr["social_facility"="shelter"](around:'+radius+','+lat+','+lon+'););out center tags 150;';
 let last='';
 // U.S. hospital fallback from public HIFLD ArcGIS feature layer (not live availability).
 if(lat>=18&&lat<=72&&lon>=-170&&lon<=-60){
  try{
   const dy=radius/111320,dx=radius/(111320*Math.max(0.2,Math.cos(lat*Math.PI/180)));
   const params=new URLSearchParams({where:'1=1',geometry:[lon-dx,lat-dy,lon+dx,lat+dy].join(','),geometryType:'esriGeometryEnvelope',inSR:'4326',spatialRel:'esriSpatialRelIntersects',outFields:'*',outSR:'4326',f:'json',resultRecordCount:'500'});
   const url='https://services.arcgis.com/XG15cJAlne2vxtgt/ArcGIS/rest/services/Hospitals_hifld/FeatureServer/0/query?'+params;
   const response=await fetch(url,{signal:AbortSignal.timeout(6500),headers:{Accept:'application/json'}});
   if(!response.ok)throw Error('ArcGIS HTTP '+response.status);
   const data=await response.json();
   if(data.error)throw Error('ArcGIS '+String(data.error.message||'query failed'));
   const features=Array.isArray(data.features)?data.features:[];
   const elements=features.flatMap((f,i)=>{
    const a=f.attributes||{},g=f.geometry||{};const y=Number(g.y),x=Number(g.x);
    if(!Number.isFinite(x)||!Number.isFinite(y))return [];
    const distance=6371000*2*Math.asin(Math.min(1,Math.sqrt(Math.sin((y-lat)*Math.PI/360)**2+Math.cos(lat*Math.PI/180)*Math.cos(y*Math.PI/180)*Math.sin((x-lon)*Math.PI/360)**2)));
    if(distance>radius)return [];
    return [{type:'node',id:Number(a.OBJECTID||a.FID||i+1),lat:y,lon:x,tags:{amenity:'hospital',name:String(a.NAME||a.Name||'Hospital'), 'addr:street':String(a.ADDRESS||a.Address||''),'addr:city':String(a.CITY||a.City||''),phone:String(a.TELEPHONE||a.PHONE||''),source:'HIFLD / ArcGIS'}}];
   });
   if(elements.length)return res.status(200).json({elements,source:'HIFLD / ArcGIS',partial:true,provider_error:last});
  }catch(e){last+='; HIFLD lookup: '+(e instanceof Error?e.message:'Unavailable');}
 }
 // Global OSM coverage. Parallelize a small number of public providers so a blocked
 // instance does not consume the entire serverless request timeout.
 const endpoints=[
  'https://overpass.private.coffee/api/interpreter',
  'https://overpass.kumi.systems/api/interpreter',
  'https://overpass.nchc.org.tw/api/interpreter',
  'https://overpass-api.de/api/interpreter'
 ];
 const attempt=async(endpoint,method)=>{
  const url=method==='GET'?endpoint+'?'+new URLSearchParams({data:query}):endpoint;
  const response=await fetch(url,{method,headers:{Accept:'application/json','User-Agent':'AvenryEarthIntelligence/1.0 (https://avenry-earth-intelligence.vercel.app/)',...(method==='POST'?{'Content-Type':'application/x-www-form-urlencoded'}:{})},...(method==='POST'?{body:new URLSearchParams({data:query})}:{}),signal:AbortSignal.timeout(8500)});
  if(!response.ok)throw Error(new URL(endpoint).hostname+' HTTP '+response.status);
  const data=await response.json();
  if(!Array.isArray(data.elements))throw Error('Invalid provider response');
  return data.elements;
 };
 const errors=[];
 for(const method of ['POST','GET']){
  const results=await Promise.allSettled(endpoints.map(endpoint=>attempt(endpoint,method)));
  const successes=results.filter(r=>r.status==='fulfilled');
  if(successes.length){
   const nonempty=successes.find(r=>r.value.length>0);
   const elements=(nonempty||successes[0]).value;
   return res.status(200).json({elements,source:'OpenStreetMap via Overpass',partial:false});
  }
  errors.push(...results.map(r=>r.status==='rejected'?String(r.reason?.message||r.reason):'Unknown error'));
 }
 last=errors.slice(-4).join('; ');

 return res.status(503).json({error:'Map providers are temporarily unavailable: '+last});
}
