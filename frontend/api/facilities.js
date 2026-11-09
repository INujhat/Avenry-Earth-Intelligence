/** Same-origin Vercel function. Avoid browser CORS restrictions on public Overpass instances. */
export default async function handler(req,res){
 res.setHeader('Cache-Control','public, s-maxage=300, stale-while-revalidate=600');
 if(req.method!=='GET')return res.status(405).json({error:'Method not allowed'});
 const lat=Number(req.query.lat),lon=Number(req.query.lon),radius=Number(req.query.radius);
 if(!Number.isFinite(lat)||Math.abs(lat)>90||!Number.isFinite(lon)||Math.abs(lon)>180||![2000,5000,10000].includes(radius))return res.status(400).json({error:'Invalid location or radius'});
 const query='[out:json][timeout:12];(nwr["amenity"~"^(hospital|clinic|pharmacy|shelter|police|fire_station)$"](around:'+radius+','+lat+','+lon+');nwr["healthcare"~"^(hospital|clinic)$"](around:'+radius+','+lat+','+lon+');nwr["office"~"^(ngo|charity)$"](around:'+radius+','+lat+','+lon+');nwr["social_facility"="shelter"](around:'+radius+','+lat+','+lon+'););out center tags 150;';
 // Identify the application as required by public Overpass instance usage policies.
 const endpoints=['https://overpass.private.coffee/api/interpreter','https://overpass.kumi.systems/api/interpreter'];let last='';for(const endpoint of endpoints){try{const response=await fetch(endpoint,{method:'POST',headers:{'Accept':'application/json','Content-Type':'application/x-www-form-urlencoded','User-Agent':'AvenryEarthIntelligence/1.0 (+https://avenry-earth-intelligence.vercel.app/)','Referer':'https://avenry-earth-intelligence.vercel.app/'},body:new URLSearchParams({data:query}),signal:AbortSignal.timeout(14500)});if(!response.ok){last='Provider HTTP '+response.status;if(response.status===406||response.status===429)break;continue;}const data=await response.json();if(!Array.isArray(data.elements))throw Error('Invalid provider response');return res.status(200).json({elements:data.elements});}catch(e){last=e instanceof Error?e.message:'Unavailable';}}

 return res.status(503).json({error:'Map providers are temporarily unavailable: '+last});
}
