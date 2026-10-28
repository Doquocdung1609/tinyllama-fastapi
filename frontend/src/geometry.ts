// Display-only transform of measured source rectangles; no inferred coordinates.
export function rotatedBox(box:number[],angle:number,width:number,height:number){
 const [x0,y0,x1,y1]=box
 if(angle===90)return [height-y1,x0,height-y0,x1]
 if(angle===180)return [width-x1,height-y1,width-x0,height-y0]
 if(angle===270)return [y0,width-x1,y1,width-x0]
 return box
}
