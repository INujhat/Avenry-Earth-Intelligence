import {useState} from 'react';
import {MessageCircle,Send,X} from 'lucide-react';

type Message={role:'user'|'assistant';text:string};
const suggestions=['What does Sentinel-1 measure?','How does water detection work?','Why is AI analysis unavailable?','Can I use this for flood warnings?'];
function answer(question:string):string{
 const q=question.toLowerCase();
 if(/(hello|^hi\b|hey)/.test(q))return 'Hello! I am the Avenry research guide. Ask me about Sentinel-1, NASA search, water segmentation, or the current project limitations.';
 if(/(sentinel|sar|radar|satellite|vv|vh)/.test(q))return 'Sentinel-1 uses synthetic aperture radar (SAR), which can observe through clouds and at night. Avenry searches NASA ASF for GRD scenes and its research model expects calibrated VV and VH radar backscatter. A NASA search result is metadata, not a processed water mask.';
 if(/(map|location|region|zoom|visual)/.test(q))return 'Select a region in the NASA search panel. The interactive OpenStreetMap basemap moves to that location. After searching NASA, green polygons show footprints of returned satellite scenes. These outlines do not indicate detected flooding.';
 if(/(unavailable|disabled|not working|model|checkpoint|run|analysis)/.test(q))return 'The public site does not currently have the licensed ONNX checkpoint and georeferenced scene assets needed for AI inference. The U-Net and ONNX inference code exists in the repository, but public one-click predictions are not yet operational. I cannot generate a prediction from this chat.';
 if(/(flood|warning|emergency|safe|danger)/.test(q))return 'Avenry is a research prototype, not an emergency alert service. Surface water is not necessarily new flooding. Never use its outputs for evacuation, safety decisions, or claims about flood damage.';
 if(/(download|geotiff|export)/.test(q))return 'NASA search results link to original radar products; downloads may require an Earthdata account. The analysis code supports GeoTIFF water-mask exports, but that feature requires a deployed model and prepared scene assets.';
 if(/(train|unet|ai|detect|segment|predict)/.test(q))return 'Avenry implements a two-channel PyTorch U-Net for pixel-level water segmentation. It clips calibrated radar values to −30…5 dB, normalizes to 0…1, and thresholds output probabilities at 0.5. The model has not been validated for general use on arbitrary NASA scenes.';
 if(/(source|license|data)/.test(q))return 'The live scene search uses NASA ASF metadata. Research training code uses Sen1Floods11, whose official STAC declares proprietary licensing; publishing research assets or derived checkpoints requires rights verification.';
 return 'I can explain Avenry’s NASA imagery search, interactive map, radar preprocessing, U-Net water detection, export workflow, and current limitations. I am a local, source-grounded guide—not a connected generative AI model—and cannot analyze new imagery.';
}
export default function ResearchAssistant(){
 const [open,setOpen]=useState(false),[draft,setDraft]=useState(''),[messages,setMessages]=useState<Message[]>([{role:'assistant',text:'Welcome to Avenry. I can explain the satellite data, interactive map, AI model, and what is currently available.'}]);
 function send(value:string){const q=value.trim().slice(0,500);if(!q)return;setMessages(old=>[...old,{role:'user' as const,text:q},{role:'assistant' as const,text:answer(q)}].slice(-24));setDraft('');}
 return <div style={{position:'fixed',right:22,bottom:20,zIndex:60}}>
  {open&&<section aria-label="Avenry research assistant" style={{width:'min(365px,calc(100vw - 36px))',height:480,maxHeight:'75vh',background:'#fff',border:'1px solid #d7e2d9',borderRadius:14,boxShadow:'0 14px 50px #193b292b',display:'flex',flexDirection:'column',marginBottom:12,overflow:'hidden'}}>
   <header style={{background:'#265d45',color:'white',padding:'14px 16px',display:'flex',justifyContent:'space-between',alignItems:'center'}}><div><strong>Avenry Research Guide</strong><div style={{fontSize:11,opacity:.85}}>Local knowledge assistant · No external AI API</div></div><button onClick={()=>setOpen(false)} aria-label="Close assistant" style={{background:'transparent',color:'white'}}><X size={19}/></button></header>
   <div role="log" aria-live="polite" style={{overflowY:'auto',flex:1,padding:14,display:'flex',flexDirection:'column',gap:10}}>
    {messages.map((m,i)=><div key={i} style={{alignSelf:m.role==='user'?'flex-end':'flex-start',maxWidth:'94%',padding:'10px 12px',borderRadius:10,background:m.role==='user'?'#e4f0e6':'#f3f6f3',fontSize:12,lineHeight:1.6,whiteSpace:'pre-wrap'}}>{m.text}</div>)}
    {messages.length===1&&<div style={{display:'flex',flexWrap:'wrap',gap:6}}>{suggestions.map(s=><button key={s} onClick={()=>send(s)} style={{border:'1px solid #d9e4dc',background:'white',padding:'7px 9px',fontSize:11,borderRadius:8,textAlign:'left'}}>{s}</button>)}</div>}
   </div>
   <form onSubmit={e=>{e.preventDefault();send(draft);}} style={{display:'flex',gap:8,padding:12,borderTop:'1px solid #e4eae4'}}>
    <input aria-label="Ask Avenry" value={draft} onChange={e=>setDraft(e.target.value)} maxLength={500} placeholder="Ask about the satellite analysis…" style={{flex:1,minWidth:0,padding:10,border:'1px solid #dce5dd',borderRadius:7,fontSize:12}}/>
    <button type="submit" aria-label="Send message" disabled={!draft.trim()} style={{background:'#265d45',color:'white',borderRadius:7,padding:10}}><Send size={17}/></button>
   </form>
  </section>}
  <button onClick={()=>setOpen(o=>!o)} aria-expanded={open} aria-label={open?'Close Avenry guide':'Open Avenry guide'} style={{marginLeft:'auto',display:'flex',alignItems:'center',gap:9,background:'#265d45',color:'white',borderRadius:30,padding:'12px 17px',boxShadow:'0 5px 24px #183f2850',fontSize:13,fontWeight:650}}><MessageCircle size={19}/>{open?'Close guide':'Ask Avenry'}</button>
 </div>;
}
