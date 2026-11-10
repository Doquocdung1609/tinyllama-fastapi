// Format verified source strings only. Never use binary floats or infer a unit.
export function sourceAmount(raw:string,unit:string,scale:string):string|null{
 const magnitude:Record<string,string>={'1':'','1000':'nghìn ','1000000':'triệu ','1000000000':'tỷ '}
 if(!(scale in magnitude)||!['USD','VND'].includes(unit))return null
 let value=raw.trim(),negative=false
 if(value.startsWith('(')&&value.endsWith(')')){negative=true;value=value.slice(1,-1);if(/^[+-]/.test(value))return null}
 if(!/^[+-]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?$/.test(value))return null
 if(value.startsWith('-'))negative=true
 const positive=value.startsWith('+'),[whole,fraction]=value.replace(/^[+-]/,'').replace(/,/g,'').split('.')
 return `${negative?'-':positive?'+':''}${whole.replace(/\B(?=(\d{3})+(?!\d))/g,'.')}${fraction===undefined?'':','+fraction} ${magnitude[scale]}${unit}`
}

export type DisplaySourceCell={raw_value:string;value?:string;unit:string;multiplier:string;effective_value:string}
export function singleSourceAmount(values:string[]|undefined,unit:string|undefined,cells:DisplaySourceCell[]|undefined){
 if(values?.length!==1||cells?.length!==1||values[0]!==cells[0].effective_value||unit!==cells[0].unit)return null
 return sourceAmount(cells[0].value??cells[0].raw_value,cells[0].unit,cells[0].multiplier)
}
