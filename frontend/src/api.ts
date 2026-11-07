export type Scene = {id:string; name:string; event:string; split:string; bounds:[number,number,number,number]; s1_date:string|null; s2_date:string|null; crs:string; width:number; height:number; source:string; license_status:string; dataset_version:string; valid_pixels:number; assets:Record<string,string>};
export type Job = {id:string; scene_id:string; status:'queued'|'running'|'completed'|'failed'; created_at:string; error:string|null; model_version:string};
export type Result = {analysis_id:string; scene_id:string; detected_water_km2:number; evaluation_scope:string; model_version:string; dataset_version:string; runtime_seconds:number; metrics:Record<string,number|null>; limitations:string[]; overlay:string; downloads:Record<string,string>};
export type System = {model_ready:boolean; model:{version:string; evaluation_scope:string; warning:string; architecture:string; epochs:number; seed:number}|null; hls_inference_enabled:boolean};
export const BROWSER_MODE=import.meta.env.VITE_RUNTIME_MODE==='browser';
export async function api<T>(path:string, init?:RequestInit):Promise<T> {
  if(BROWSER_MODE){const {browserApi}=await import('./browserApi');return browserApi<T>(path,init);}
  const response=await fetch('/api/v1'+path,init);
  if(!response.ok){let message=`Request failed (${response.status})`; try{message=(await response.json()).error.message;}catch{/* keep HTTP error */} throw new Error(message);}
  return response.json();
}
