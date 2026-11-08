import {useEffect,useRef,useState} from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

export type Place={name:string;lat:number;lon:number};
type Props={place:Place; footprints?:GeoJSON.FeatureCollection};
const EMPTY:GeoJSON.FeatureCollection={type:'FeatureCollection',features:[]};
export default function LocationExplorer({place,footprints}:Props){
 const node=useRef<HTMLDivElement>(null),map=useRef<maplibregl.Map|null>(null);
 const [error,setError]=useState('');
 useEffect(()=>{
  if(!node.current)return;
  let m:maplibregl.Map;
  try{
   m=new maplibregl.Map({container:node.current,center:[place.lon,place.lat],zoom:9,
    style:{version:8,sources:{osm:{type:'raster',tiles:['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],tileSize:256,attribution:'© OpenStreetMap contributors'}},
    layers:[{id:'osm',type:'raster',source:'osm'}]},attributionControl:{}});
  }catch(e){setError(e instanceof Error?e.message:'WebGL is unavailable');return;}
  map.current=m;
  m.addControl(new maplibregl.NavigationControl(),'top-right');
  m.on('load',()=>{m.addSource('footprints',{type:'geojson',data:footprints||EMPTY});m.addLayer({id:'scene-fill',type:'fill',source:'footprints',paint:{'fill-color':'#1d9469','fill-opacity':0.16}});m.addLayer({id:'scene-outline',type:'line',source:'footprints',paint:{'line-color':'#127452','line-width':2}});});
  return()=>{m.remove();map.current=null;};
 },[]);
 useEffect(()=>{map.current?.flyTo({center:[place.lon,place.lat],zoom:9,essential:true});},[place.lat,place.lon]);
 useEffect(()=>{const m=map.current;if(!m)return;const update=()=>{const source=m.getSource('footprints') as maplibregl.GeoJSONSource|undefined;source?.setData(footprints||EMPTY);};if(m.isStyleLoaded())update();else m.once('load',update);return()=>{m.off('load',update);};},[footprints]);
 return <div style={{position:'relative',height:390,borderRadius:10,overflow:'hidden',border:'1px solid #dfe7df',background:'#dce8df'}}>
  <div ref={node} style={{width:'100%',height:'100%'}} role="region" aria-label={'Interactive map of '+place.name}/>
  {error&&<div role="alert" style={{position:'absolute',top:12,left:12,background:'white',padding:12}}>{error}</div>}
  <div style={{position:'absolute',bottom:30,left:12,background:'rgba(255,255,255,.94)',padding:'8px 11px',borderRadius:6,fontSize:11,pointerEvents:'none'}}>
   <strong>{place.name}</strong> · {place.lat.toFixed(3)}°, {place.lon.toFixed(3)}°<br/>
   Green outlines = NASA scene footprints, not detected flooding
  </div>
 </div>;
}
