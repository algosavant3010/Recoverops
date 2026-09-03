import { ImageResponse } from "next/og";

export const alt = "RecoverOps — Revenue recovery, safely automated";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function Image() {
  return new ImageResponse(<div style={{width:"100%",height:"100%",display:"flex",flexDirection:"column",justifyContent:"space-between",padding:"72px 82px",background:"#07110d",color:"#f1fff7",fontFamily:"Arial"}}><div style={{display:"flex",alignItems:"center",fontSize:30,fontWeight:700}}><span style={{width:48,height:48,marginRight:14,border:"2px solid #55e69d",borderRadius:12,display:"flex",alignItems:"center",justifyContent:"center",color:"#55e69d"}}>R</span>recover<span style={{color:"#55e69d"}}>ops</span></div><div style={{display:"flex",flexDirection:"column"}}><div style={{fontSize:24,color:"#55e69d",letterSpacing:5}}>AUTONOMOUS · AUDITABLE · BOUNDED</div><div style={{display:"flex",flexDirection:"column",fontSize:82,fontWeight:750,letterSpacing:-5,lineHeight:1.04,marginTop:24}}>Recover revenue.<span style={{color:"#55e69d"}}>Never lose control.</span></div></div><div style={{fontSize:24,color:"#8fa79c"}}>The AI diagnoses. Deterministic policy decides.</div></div>, size);
}
