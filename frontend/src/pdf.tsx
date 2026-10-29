import {useEffect,useRef,useState} from 'react'
import {getDocument,GlobalWorkerOptions,TextLayer} from 'pdfjs-dist'
import type {PDFDocumentProxy} from 'pdfjs-dist'
import worker from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
import {pdfBytes} from './api'
import type {PageEvidence} from './api'
import {rotatedBox} from './geometry'
GlobalWorkerOptions.workerSrc=worker

export function PdfPage({id,page,zoom,rotation=0,evidence,boxes,onLoaded}:{id:string;page:number;zoom:number;rotation?:number;evidence?:PageEvidence;boxes:{box:number[];kind:string}[];onLoaded:(n:number)=>void}){
 const canvas=useRef<HTMLCanvasElement>(null),layer=useRef<HTMLDivElement>(null)
 const [pdf,setPdf]=useState<PDFDocumentProxy|null>(null),[error,setError]=useState(''),[size,setSize]=useState({width:600,height:800}),[rendered,setRendered]=useState(false)
 useEffect(()=>{let stopped=false;let loading:ReturnType<typeof getDocument>|undefined;setError('');setPdf(null)
  pdfBytes(id).then(data=>{if(stopped)return;loading=getDocument({data:new Uint8Array(data)});return loading.promise}).then(doc=>{if(doc&&!stopped){setPdf(doc);onLoaded(doc.numPages)}}).catch(e=>{if(!stopped)setError(String(e))})
  return()=>{stopped=true;void loading?.destroy()}
 },[id]) // onLoaded is presentation-only, not an input to the PDF fetch.
 useEffect(()=>{if(!pdf||!canvas.current||!layer.current)return;let cancelled=false;let task:ReturnType<Awaited<ReturnType<PDFDocumentProxy['getPage']>>['render']>|undefined;let text:TextLayer|undefined;setRendered(false)
  pdf.getPage(page).then(async pdfPage=>{if(cancelled)return;const viewport=pdfPage.getViewport({scale:zoom,rotation:(pdfPage.rotate+rotation)%360});setSize({width:viewport.width,height:viewport.height});const c=canvas.current!,target=layer.current!;c.width=Math.round(viewport.width);c.height=Math.round(viewport.height);target.replaceChildren();target.style.setProperty('--scale-factor',String(zoom));task=pdfPage.render({canvas:c,viewport});await task.promise;if(cancelled)return;const content=await pdfPage.getTextContent();text=new TextLayer({textContentSource:content,container:target,viewport});await text.render();if(!cancelled)setRendered(true)}).catch(e=>{if(!cancelled)setError(String(e))})
  return()=>{cancelled=true;task?.cancel();text?.cancel()}
 },[pdf,page,zoom,rotation])
 if(error)return <div className="error" role="alert">Không thể mở PDF: {error}</div>
 return <div className="pdf-page" data-testid="pdf-page" data-rendered={rendered} style={{width:size.width,height:size.height}}><canvas ref={canvas} aria-label={`Trang PDF ${page}`}/><div ref={layer} className="textLayer"/>{boxes.map(({box,kind})=>({box:rotatedBox(box,rotation,evidence?.width||size.width/zoom,evidence?.height||size.height/zoom),kind})).map(({box,kind},i)=><div key={i} data-testid="source-highlight" className={'pdf-highlight '+kind} style={{left:box[0]*zoom,top:box[1]*zoom,width:(box[2]-box[0])*zoom,height:(box[3]-box[1])*zoom}}/>)}{evidence&&['OCR','REGION_FUSION'].includes(evidence.method)&&<div className="textLayer" aria-label="Lớp chữ OCR có thể chọn">{evidence.lines.flatMap(l=>l.words).filter(w=>evidence.method==='OCR'||w.source?.includes('OCR')).map(w=>({...w,box:rotatedBox(w.box,rotation,evidence.width,evidence.height)})).map((w,i)=><span key={i} style={{left:w.box[0]*zoom,top:w.box[1]*zoom,fontSize:(w.box[3]-w.box[1])*zoom,width:(w.box[2]-w.box[0])*zoom,height:(w.box[3]-w.box[1])*zoom,overflow:'hidden'}}>{w.text} </span>)}</div>}</div>
}
