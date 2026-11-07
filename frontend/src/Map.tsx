import {useEffect,useRef,useState} from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import type {Scene} from './api';

type Props={scene:Scene; layer:'optical'|'radar'; prediction?:string; showPrediction:boolean; showLabels:boolean; opacity:number};
export default function SceneMap({scene,layer,prediction,showPrediction,showLabels,opacity}:Props){
 const container=useRef<HTMLDivElement>(null), map=useRef<maplibregl.Map|null>(null);
 const [coords,setCoords]=useState('Move across the map to inspect coordinates');
 const [error,setError]=useState('');
 useEffect(()=>{
  if(!container.current)return;
  let instance:maplibregl.Map;
  try{
   instance=new maplibregl.Map({container:container.current,style:{version:8,sources:{},layers:[{id:'background',type:'background',paint:{'background-color':'#101b1d'}}]},center:[0,0],zoom:1,attributionControl:false});
  }catch(e){setError(`Interactive map unavailable: ${e instanceof Error?e.message:'WebGL required'}`);return;}
  map.current=instance;
  instance.addControl(new maplibregl.NavigationControl({showCompass:false}),'top-right');
  instance.addControl(new maplibregl.ScaleControl({unit:'metric'}),'bottom-left');
  instance.addControl(new maplibregl.AttributionControl({compact:false,customAttribution:'Imagery & labels: Cloud to Street · Sen1Floods11'}));
  instance.on('mousemove',e=>setCoords(`${Math.abs(e.lngLat.lat).toFixed(5)}° ${e.lngLat.lat>=0?'N':'S'}  /  ${Math.abs(e.lngLat.lng).toFixed(5)}° ${e.lngLat.lng>=0?'E':'W'}`));
  return()=>{instance.remove();map.current=null;};
 },[]);
 useEffect(()=>{
  const m=map.current;if(!m)return;
  const [w,s,e,n]=scene.bounds;
  const coordinates:[[number,number],[number,number],[number,number],[number,number]]=[[w,n],[e,n],[e,s],[w,s]];
  const render=()=>{
   ['boundary','label','prediction','imagery'].forEach(id=>{if(m.getLayer(id))m.removeLayer(id);if(m.getSource(id))m.removeSource(id);});
   m.addSource('imagery',{type:'image',url:scene.assets[layer],coordinates});
   m.addLayer({id:'imagery',type:'raster',source:'imagery',paint:{'raster-fade-duration':0}});
   if(prediction){m.addSource('prediction',{type:'image',url:prediction,coordinates});m.addLayer({id:'prediction',type:'raster',source:'prediction',layout:{visibility:showPrediction?'visible':'none'},paint:{'raster-opacity':opacity,'raster-fade-duration':0}});}
   m.addSource('label',{type:'image',url:scene.assets.label,coordinates});m.addLayer({id:'label',type:'raster',source:'label',layout:{visibility:showLabels?'visible':'none'},paint:{'raster-opacity':opacity,'raster-fade-duration':0}});
   m.addSource('boundary',{type:'geojson',data:{type:'Feature',properties:{},geometry:{type:'Polygon',coordinates:[[[w,s],[e,s],[e,n],[w,n],[w,s]]]}}});
   m.addLayer({id:'boundary',type:'line',source:'boundary',paint:{'line-color':'#b1e3bc','line-width':1.5,'line-dasharray':[4,3]}});
   m.fitBounds([[w,s],[e,n]],{padding:65,duration:500});
  };
  if(m.isStyleLoaded())render();else m.once('load',render);
  return()=>{m.off('load',render);};
 },[scene.id,layer,prediction]);
 useEffect(()=>{const m=map.current;if(!m)return; for(const [id,show] of [['prediction',showPrediction],['label',showLabels]] as const){if(m.getLayer(id)){m.setLayoutProperty(id,'visibility',show?'visible':'none');m.setPaintProperty(id,'raster-opacity',opacity);}}},[showPrediction,showLabels,opacity]);
 return <div className="map-frame"><div ref={container} className="map-canvas"/>{error&&<div className="map-error">{error}<img src={scene.assets[layer]} alt="Satellite scene preview"/></div>}<div className="map-badge"><span className="live-dot"/> GEOREFERENCED · EPSG:4326</div><div className="map-coords">{coords}</div><div className="map-legend"><span><i className="legend-water"/>Predicted water</span><span><i className="legend-label"/>Reference label</span></div></div>;
}
