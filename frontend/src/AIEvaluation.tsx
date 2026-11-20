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

 const [demo,setDemo]=useState<{tp:number;fp:number;fn:number;tn:number;total:number}|null>(null);
 const [threshold,setThreshold]=useState(0.5);
 const [referenceFile,setReferenceFile]=useState<File|null>(null);
 const [predictionFile,setPredictionFile]=useState<File|null>(null);
 const [comparison,setComparison]=useState<{tp:number;fp:number;fn:number;tn:number;total:number;preview:string}|null>(null);
 const [comparisonError,setComparisonError]=useState('');
 const [busy,setBusy]=useState(false);
 function makeDemo(t:number){
  const size=96;let tp=0,fp=0,fn=0,tn=0;
  for(let y=0;y<size;y++)for(let x=0;x<size;x++){
   const river=Math.abs(x-47-11*Math.sin(y/14))<9+2*Math.cos(y/8);
   const lake=((x-28)**2/210+(y-73)**2/130)<1;
   const truth=river||lake;
   const score=Math.max(0,Math.min(1,0.5+(11-Math.abs(x-47-11*Math.sin(y/14)))/24+(lake?0.3:0)+0.09*Math.sin(x*1.3+y*.7)));
   const predicted=score>=t;
   if(truth&&predicted)tp++;else if(predicted)fp++;else if(truth)fn++;else tn++;
  }
  setDemo({tp,fp,fn,tn,total:size*size});
 }
 async function readMask(file:File){
  const url=URL.createObjectURL(file);
  try{
   const image=await createImageBitmap(file);
   if(image.width>4096||image.height>4096)throw Error('Images must be 4096 pixels or smaller per side.');
   const canvas=document.createElement('canvas');canvas.width=image.width;canvas.height=image.height;
   const ctx=canvas.getContext('2d',{willReadFrequently:true});if(!ctx)throw Error('Canvas is unavailable');
   ctx.drawImage(image,0,0);const data=ctx.getImageData(0,0,image.width,image.height).data;image.close();
   return {width:canvas.width,height:canvas.height,data};
  }finally{URL.revokeObjectURL(url);}
 }
 async function compareFiles(){
  if(!referenceFile||!predictionFile)return;
  setBusy(true);setComparisonError('');
  try{
   const [a,b]=await Promise.all([readMask(referenceFile),readMask(predictionFile)]);
   if(a.width!==b.width||a.height!==b.height)throw Error('Both images must have identical width and height.');
   let tp=0,fp=0,fn=0,tn=0;const canvas=document.createElement('canvas');canvas.width=a.width;canvas.height=a.height;
   const ctx=canvas.getContext('2d');if(!ctx)throw Error('Canvas unavailable');
   const out=ctx.createImageData(a.width,a.height);
   for(let i=0;i<a.data.length;i+=4){
    if(a.data[i+3]===0||b.data[i+3]===0){out.data.set([100,100,100,80],i);continue;}
    const truth=(a.data[i]+a.data[i+1]+a.data[i+2])/3>=128;
    const pred=(b.data[i]+b.data[i+1]+b.data[i+2])/3>=128;
    if(truth&&pred){tp++;out.data.set([37,143,90,255],i);}
    else if(pred){fp++;out.data.set([220,98,70,255],i);}
    else if(truth){fn++;out.data.set([235,178,55,255],i);}
    else{tn++;out.data.set([230,236,231,255],i);}
   }
   ctx.putImageData(out,0,0);
   setComparison({tp,fp,fn,tn,total:tp+fp+fn+tn,preview:canvas.toDataURL('image/png')});
  }catch(e){setComparisonError(e instanceof Error?e.message:'Could not compare images');}finally{setBusy(false);}
 }
 const metric=(c:{tp:number;fp:number;fn:number;tn:number},key:string)=>{
  const {tp,fp,fn,tn}=c;
  const pairs:Record<string,[number,number]>={iou:[tp,tp+fp+fn],dice:[2*tp,2*tp+fp+fn],precision:[tp,tp+fp],recall:[tp,tp+fn],specificity:[tn,tn+fp],accuracy:[tp+tn,tp+fp+fn+tn]};
  const [n,d]=pairs[key];return d?format(n/d):'Undefined (zero denominator)';
 };
 const active=comparison??demo;
 return <section style={{display:'grid',gap:20}}>
  <div className="science-notice"><div><strong>Evidence-first AI evaluation</strong><p>{status} This page does not estimate model accuracy from NASA scene search, and never substitutes training-set performance for held-out testing.</p></div></div>
  <article className="intro-card" style={{border:'2px solid #b7d5c1'}}>
   <span className="eyebrow">INTERACTIVE EVALUATION LAB · WORKS IN YOUR BROWSER</span>
   <h2 style={{marginTop:8}}>Run a measurable evaluation now</h2>
   <p style={{marginTop:8}}>Choose a built-in <strong>synthetic demonstration</strong> or compare your own reference and predicted masks. Metrics are calculated from pixels in your browser. This does not deploy or test the U-Net model.</p>
   <div style={{display:'flex',gap:12,flexWrap:'wrap',alignItems:'center',marginTop:16}}>
    <button className="button primary" onClick={()=>{setComparison(null);makeDemo(threshold);}}>Run synthetic example</button>
    <label>Prediction threshold: <strong>{threshold.toFixed(2)}</strong> <input aria-label="Prediction threshold" type="range" min="0.1" max="0.9" step="0.05" value={threshold} onChange={e=>{const t=Number(e.target.value);setThreshold(t);if(demo){setComparison(null);makeDemo(t);}}}/></label>
   </div>
   {demo&&!comparison&&<p style={{marginTop:12,color:'#9a5d22',fontWeight:650}}>SYNTHETIC DEMO ONLY — these scores are not Avenry model accuracy.</p>}
   <div style={{marginTop:20,paddingTop:18,borderTop:'1px solid #dfe7e1'}}>
    <h3>Evaluate your own two mask images</h3>
    <p style={{marginTop:8}}>Upload two equally sized PNG/JPEG images: reference mask and prediction mask. White (brightness ≥ 128) = water; black = non-water; transparent pixels are ignored. Both images must use the same pixel alignment.</p>
    <div style={{display:'flex',gap:14,flexWrap:'wrap',marginTop:12}}>
     <label>Reference / ground truth<br/><input type="file" accept="image/png,image/jpeg,image/webp" onChange={e=>{setReferenceFile(e.target.files?.[0]??null);setComparison(null);}}/></label>
     <label>Predicted water mask<br/><input type="file" accept="image/png,image/jpeg,image/webp" onChange={e=>{setPredictionFile(e.target.files?.[0]??null);setComparison(null);}}/></label>
    </div>
    <button className="button primary" style={{marginTop:12}} disabled={!referenceFile||!predictionFile||busy} onClick={compareFiles}>{busy?'Comparing…':'Evaluate uploaded masks'}</button>
    {comparisonError&&<p role="alert" style={{color:'#a43e31',marginTop:8}}>{comparisonError}</p>}
   </div>
   {active&&<div style={{marginTop:18}}>
    <h3>{comparison?'Your uploaded mask comparison':'Synthetic example results'}</h3>
    <div className="stat-grid" style={{marginTop:12}}>{([['iou','IoU'],['dice','Dice / F1'],['precision','Precision'],['recall','Recall'],['specificity','Specificity'],['accuracy','Pixel accuracy']] as const).map(([k,label])=><div key={k} style={{padding:14,border:'1px solid #dfe7e1',borderRadius:8}}><span className="eyebrow">{label}</span><h2>{metric(active,k)}</h2></div>)}</div>
    <p style={{marginTop:12}}>TP {active.tp.toLocaleString()} · FP {active.fp.toLocaleString()} · FN {active.fn.toLocaleString()} · TN {active.tn.toLocaleString()} · Evaluated pixels {active.total.toLocaleString()}</p>
    {comparison&&<div style={{marginTop:14}}><p>Comparison overlay: green = correct water; red = false positive; yellow = missed water; pale = correct non-water.</p><img alt="Pixel-level classification comparison" src={comparison.preview} style={{width:320,maxWidth:'100%',imageRendering:'pixelated',marginTop:10,borderRadius:8}}/><p><a href={comparison.preview} download="avenry-mask-comparison.png">Download comparison image</a></p></div>}
    <button className="button" style={{marginTop:12}} onClick={()=>{const payload={kind:comparison?'uploaded_masks':'synthetic_demo',threshold:comparison?null:threshold,counts:{tp:active.tp,fp:active.fp,fn:active.fn,tn:active.tn},metrics:Object.fromEntries(['iou','dice','precision','recall','specificity','accuracy'].map(k=>[k,metric(active,k)])),disclaimer:comparison?'User-provided masks; no model or provenance independently verified':'Synthetic example only; NOT measured model performance'};const blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='avenry-evaluation.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}}>Download results JSON</button>
   </div>}
  </article>
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
