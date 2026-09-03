import Link from "next/link";
import { ArrowLeft, Radar } from "lucide-react";

export default function NotFound() {
  return <main style={{minHeight:"100vh",display:"grid",placeItems:"center",background:"#07110d",color:"#f1fff7",textAlign:"center",padding:24}}><div><Radar size={44} color="#55e69d" style={{margin:"0 auto 24px"}}/><span style={{font:"10px var(--font-mono)",letterSpacing:".15em",color:"#55e69d"}}>404 / SIGNAL LOST</span><h1 style={{fontSize:46,margin:"15px 0"}}>This trace does not exist.</h1><p style={{color:"#8fa79c",marginBottom:28}}>Return to the command center and run a verified recovery scenario.</p><Link href="/" style={{display:"inline-flex",alignItems:"center",gap:8,padding:"12px 16px",background:"#55e69d",color:"#052315",borderRadius:7,fontSize:12,fontWeight:700}}><ArrowLeft size={15}/> Command center</Link></div></main>;
}
