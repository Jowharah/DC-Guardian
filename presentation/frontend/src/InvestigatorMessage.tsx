import type {ReactNode} from "react";

const domainRules=[
 {pattern:/^(?:\d+[.)]\s*)?(?:SSH|Cybersecurity)\b/i,kind:"cyber",icon:"⌘"},
 {pattern:/^(?:\d+[.)]\s*)?(?:Face Recognition|Physical Security|Face)\b/i,kind:"physical",icon:"◉"},
 {pattern:/^(?:\d+[.)]\s*)?(?:PPE|Safety)\b/i,kind:"safety",icon:"◆"},
 {pattern:/^(?:\d+[.)]\s*)?(?:Recorded Human.Review|Human Review|Deterministic Review)\b/i,kind:"review",icon:"✓"},
 {pattern:/^(?:\d+[.)]\s*)?(?:Unverified Relationships|Limitations|Uncertainties)\b/i,kind:"uncertain",icon:"⚠"}
] as const;
const emphasis=/(\b(?:HIGH_CONFIDENCE_ANOMALY|EVIDENCE_REVIEW_REQUIRED|NEEDS_FOLLOW_UP|UNAUTHORIZED|NON_COMPLIANT|COMPLIANT|RECOGNIZED|INCONCLUSIVE|HUMAN_REVIEW|NOT_VERIFIED)\b|\b(?:false|true)\b|\b(?:ZONE-[A-Z]|P\d{3})\b|\b(?:SSH-EVT|PPE-IMG|FACE-IMG)-[A-Z0-9-]+\b|\*\*[^*]+\*\*)/gi;
function inline(text:string):ReactNode[]{
 return text.split(emphasis).filter(Boolean).map((part,i)=>{
  if(part.startsWith("**")&&part.endsWith("**"))return <strong key={i}>{part.slice(2,-2)}</strong>;
  if(/^(?:SSH-EVT|PPE-IMG|FACE-IMG)-/.test(part))return <code key={i} className="investigatorEvidenceId">{part}</code>;
  if(/^(?:UNAUTHORIZED|NON_COMPLIANT|NEEDS_FOLLOW_UP|HIGH_CONFIDENCE_ANOMALY|EVIDENCE_REVIEW_REQUIRED|NOT_VERIFIED|false)$/i.test(part))return <strong key={i} className="investigatorHighlightWarning">{part}</strong>;
  if(/^(?:COMPLIANT|RECOGNIZED|true)$/i.test(part))return <strong key={i} className="investigatorHighlightSuccess">{part}</strong>;
  if(/^(?:ZONE-[A-Z]|P\d{3})$/.test(part))return <strong key={i} className="investigatorHighlightInfo">{part}</strong>;
  return part;
 });
}
export default function InvestigatorMessage({text}:{text:string}){
 const lines=text.replace(/\\n/g,"\n").split(/\r?\n/);
 let currentKind="general";
 return <div className="investigatorFormatted">{lines.map((raw,i)=>{
  const line=raw.trim();
  if(!line)return null;
  const markdownHeading=line.match(/^(#{1,4})\s+(.+)$/);
  if(markdownHeading){
   const title=markdownHeading[2].replace(/\*\*/g,"").replace(/:\s*$/,"");
   const rule=domainRules.find(item=>item.pattern.test(title));
   currentKind=rule?.kind??"general";
   return <div key={i} className={`investigatorSectionHeading investigatorTone-${currentKind}`}>
    <span aria-hidden="true">{rule?.icon??"✦"}</span>
    <strong>{inline(title)}</strong>
   </div>;
  }
  const heading=domainRules.find(rule=>rule.pattern.test(line.replace(/\*\*/g,"")));
  if(heading){
   currentKind=heading.kind;
   return <div key={i} className={`investigatorSectionHeading investigatorTone-${heading.kind}`}><span aria-hidden="true">{heading.icon}</span><strong>{inline(line.replace(/\*\*/g,"").replace(/:\s*$/,""))}</strong></div>;
  }
  if(/^(?:Summary|Conclusion|Key findings):?/i.test(line)){
   currentKind="general";
   return <h4 key={i} className="investigatorSummaryHeading">{inline(line)}</h4>;
  }
  const bullet=line.match(/^(?:[-•*]|\d+[.)])\s+(.+)$/);
  if(bullet)return <div key={i} className={`investigatorBullet investigatorTone-${currentKind}`}><span aria-hidden="true">•</span><p>{inline(bullet[1])}</p></div>;
  return <p key={i} className="investigatorParagraph">{inline(line)}</p>;
 })}</div>;
}
