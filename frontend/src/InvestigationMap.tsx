import {useEffect,useRef} from 'react';
import maplibregl from 'maplibre-gl';

type Facility={name:string;kind:string;lat:number;lon:number;address:string;distance_km:number};
export default function InvestigationMap({location,facilities}:{location:{name:string;lat:number;lon:number};facilities:Facility[]}){
 const node=useRef<HTMLDivElement>(null);
 useEffect(()=>{
  if(!node.current)return;
  const map=new maplibregl.Map({container:node.current,style:{version:8,sources:{osm:{type:'raster',tiles:['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],tileSize:256,attribution:'© OpenStreetMap contributors'}},layers:[{id:'osm',type:'raster',source:'osm'}]},center:[location.lon,location.lat],zoom:11});
  const origin=document.createElement('div');origin.style.cssText='height:18px;width:18px;border:4px solid #fff;background:#1b6650;border-radius:50%;box-shadow:0 1px 7px #555';
  new maplibregl.Marker({element:origin}).setLngLat([location.lon,location.lat]).setPopup(new maplibregl.Popup().setText('Investigation center: '+location.name)).addTo(map);
  const bounds=new maplibregl.LngLatBounds([location.lon,location.lat],[location.lon,location.lat]);
  for(const f of facilities.slice(0,150)){
   const dot=document.createElement('div');dot.style.cssText='height:12px;width:12px;border:2px solid white;border-radius:50%;background:#c27531;box-shadow:0 1px 5px #555';
   new maplibregl.Marker({element:dot}).setLngLat([f.lon,f.lat]).setPopup(new maplibregl.Popup({offset:10}).setText(f.name+' · '+f.kind+' · '+f.distance_km+' km from center')).addTo(map);
   bounds.extend([f.lon,f.lat]);
  }
  if(facilities.length)map.fitBounds(bounds,{padding:55,maxZoom:12,duration:0});
  return()=>map.remove();
 },[location.name,location.lat,location.lon,facilities]);
 return <div style={{marginTop:16}}><h4 style={{fontSize:14,marginBottom:9}}>Investigation map — mapped facilities, not flood exposure</h4><div ref={node} role="region" aria-label="Map showing investigation center and mapped facilities" style={{height:350,borderRadius:9,overflow:'hidden',border:'1px solid #dfe7df'}}/><p style={{fontSize:11,color:'#66786d',marginTop:7}}>Green marker: investigation center. Orange markers: mapped facilities (up to 150 displayed). Basemap © OpenStreetMap contributors. Locations are not verified operational or affected.</p></div>
}
