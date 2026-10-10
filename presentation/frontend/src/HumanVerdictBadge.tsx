import type {LatestEvidenceReview} from "./api";

const words=(s:string|null|undefined)=>(s??"not reported").replaceAll("_"," ");

/** Latest human verdict beside a detector result; the detector output is unchanged. */
export default function HumanVerdictBadge({verdict}:{verdict?:LatestEvidenceReview}){
 if(!verdict)return null;
 if(verdict.verdict==="OVERRIDDEN")return <span className="severity humanVerdictBadge humanVerdictOverride" title={`Human override by ${verdict.reviewer}; detector reported ${words(verdict.model_status)}`}>HUMAN: {words(verdict.corrected_status)}</span>;
 if(verdict.verdict==="CONFIRMED")return <span className="severity humanVerdictBadge" title={`Detector result confirmed by ${verdict.reviewer}`}>✓ HUMAN CONFIRMED</span>;
 return <span className="severity humanVerdictBadge" title={`Human review inconclusive (${verdict.reviewer}); detector result still applies`}>HUMAN: INCONCLUSIVE</span>;
}
