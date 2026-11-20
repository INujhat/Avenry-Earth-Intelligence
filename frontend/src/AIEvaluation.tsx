import {useEffect,useState} from 'react';
import {api,type System} from './api';

type Evaluation={scope?:string;event_count?:number;scene_count?:number;threshold?:number;micro_metrics?:Record<string,number|null>;macro_event_metrics?:Record<string,number|null>;event_bootstrap_95pct_ci?:Record<string,[number,number]|null>;manifest_sha256?:string;limitations?:string[]};
const format=(v:number|null|undefined)=>v==null?'Not defined':(100*v).toFixed(1)+'%';
export default function AIEvaluation(){
 const [system,setSystem]=useState<System|null>(null);
 const [report,setReport]=useState<Evaluation|null>(null);
 const [status,setStatus]=useState('Checking deployed evaluation evidence…');
 useEffect(()=>{let live=true;(async()=>{
  try{const s=await api<System>('/system');if(live)setSystem(s);}catch{/* Model service may be unavailable */}
  try{const response=await fetch('/evaluation/report.json',{cache:'no-store'});if(!response.ok)throw Error('No published held-out report');const data=await response.json() as Evaluation;
   if(data.scope!=='held_out_test_events'||!data.event_count||!data.manifest_sha256||!data.micro_metrics)throw Error('Report lacks required evaluation provenance');
   if(live){setReport(data);setStatus('Held-out evaluation report available');}
  }catch{if(live)setStatus('No independently auditable held-out evaluation report is published on this deployment.');}
 })();return()=>{live=false;};},[]);
 return <section style={{display:'grid',gap:20}}>
  <div className="science-notice"><div><strong>Evidence-first AI evaluation</strong><p>{status} This page does not estimate model accuracy from NASA scene search, and never substitutes training-set performance for held-out testing.</p></div></div>
  <div className="stat-grid">
   <div className="intro-card"><span className="eyebrow">MODEL DEPLOYMENT</span><h2>{system?.model_ready?'Model assets reported ready':'Not verified live'}</h2><p>{system?.model_ready?'The runtime reports a model; independent held-out results are shown only when a valid evaluation report exists.':'The public runtime does not currently report a verified deployable model.'}</p></div>
   <div className="intro-card"><span className="eyebrow">HELD-OUT EVENTS</span><h2>{report?.event_count??'—'}</h2><p>Entire geographic events excluded from training and validation.</p></div>
   <div className="intro-card"><span className="eyebrow">HELD-OUT SCENES</span><h2>{report?.scene_count??'—'}</h2><p>Scenes with actual reference labels and valid-pixel masks.</p></div>
   <div className="intro-card"><span className="eyebrow">TEST IoU</span><h2>{format(report?.micro_metrics?.iou)}</h2><p>Intersection over union across labeled held-out test pixels.</p></div>
  </div>
  <article className="intro-card"><h2>Evaluation scorecard</h2><p>Scores are displayed only when a traceable report has been published.</p><div style={{overflowX:'auto',marginTop:16}}><table style={{width:'100%',textAlign:'left',borderCollapse:'collapse'}}><thead><tr><th style={{padding:10}}>Metric</th><th>Pixel pooled</th><th>Event averaged</th><th>95% event bootstrap interval</th></tr></thead><tbody>{([['iou','IoU'],['dice_f1','Dice / F1'],['precision','Precision'],['recall','Recall'],['specificity','Specificity'],['balanced_accuracy','Balanced accuracy']] as const).map(([key,label])=><tr key={key} style={{borderTop:'1px solid #dfe7e1'}}><td style={{padding:10}}>{label}</td><td>{format(report?.micro_metrics?.[key])}</td><td>{format(report?.macro_event_metrics?.[key])}</td><td>{report?.event_bootstrap_95pct_ci?.[key]?.map(format).join(' – ')??'Not available'}</td></tr>)}</tbody></table></div></article>
  <article className="intro-card"><h2>How to produce a real evaluation</h2><p>Prepare held-out scene probability arrays, binary ground-truth labels and valid-pixel masks. Assign every scene to an event that was excluded from training and validation. Run the reproducible Python evaluator and publish its JSON report only after reviewing provenance and test integrity.</p><p style={{marginTop:12}}><code>python -m ml.evaluation evaluation-manifest.json --output frontend/public/evaluation/report.json</code></p><p style={{marginTop:12}}>No report is automatically fabricated or deployed. The evaluator supports per-scene and per-event metrics, confusion matrices, thresholding, Brier scores and event-level bootstrap intervals.</p>{report?.manifest_sha256&&<p style={{marginTop:12,overflowWrap:'anywhere'}}>Manifest SHA-256: <code>{report.manifest_sha256}</code></p>}</article>
  <div className="science-notice"><div><strong>Interpretation matters</strong><p>Segmentation scores measure agreement with reference water labels, not whether a new flood occurred or whether people or buildings were harmed. A small number of events cannot establish global performance.</p></div></div>
 </section>;
}
