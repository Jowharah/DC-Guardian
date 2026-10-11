import type {PairUncertaintyEstimate} from "./api";

const FACTOR_NAMES:Record<string,string>={TimeGap:"Time gap",Topology:"Location",DomainMechanism:"Known mechanism",EvidenceStrength:"Evidence strength"};

/** Research estimate P(Related) beside a correlation pair. Display only: the
 *  deterministic rule decides correlation; this never changes it. */
export default function PairUncertainty({estimate}:{estimate?:PairUncertaintyEstimate}){
 if(!estimate)return null;
 if(estimate.status==="NOT_SCORED")return <div className="decisionReviewNotice"><p className="muted"><b>Research estimate:</b> not scored — {estimate.reason}</p></div>;
 const p=estimate.probability_related??0;
 return <div className="decisionReviewNotice" role="note">
  <p><b>Research estimate · P(same incident) {(p*100).toFixed(0)}%</b> <span className="muted">(Bayesian model {estimate.knowledge_base_version}; prior {((estimate.prior??0)*100).toFixed(0)}%, model threshold {((estimate.decision_threshold??0)*100).toFixed(0)}%)</span></p>
  <ul>{(estimate.factors??[]).map(f=><li key={f.factor}>{FACTOR_NAMES[f.factor]??f.factor}: {f.observed.replaceAll("_"," ").toLowerCase()} — {f.likelihood_ratio>1?"supports":"opposes"} (×{f.likelihood_ratio})</li>)}</ul>
  {(estimate.marginalized_factors??[]).length>0&&<p className="muted">Not observable for these events, left out of the estimate: {estimate.marginalized_factors!.map(f=>FACTOR_NAMES[f]??f).join(", ")}.</p>}
  <p className="muted">{estimate.note}</p>
 </div>;
}
