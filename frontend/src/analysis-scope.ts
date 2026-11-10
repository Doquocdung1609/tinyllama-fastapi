// Cache only the fields actually submitted to the selected backend.
export function analysisResponseScope(source:string,request:{question:string;operation:string},ticker:string){
 return JSON.stringify(source==='SEC'?{source,question:request.question,operation:request.operation,ticker}:{source,...request})
}
