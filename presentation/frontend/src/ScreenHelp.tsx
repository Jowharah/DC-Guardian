// Usability study (P03): a short guide to the terms, for first-time users. Collapsed by default.
export default function ScreenHelp(){
 return <details className="screenHelp">
  <summary>How to read this screen</summary>
  <dl>
   <div><dt>Abnormal result</dt><dd>An automatic detector flagged something (for example a failed-login burst or a missing safety vest). It is <b>not yet confirmed by a human</b>.</dd></div>
   <div><dt>Correlated group</dt><dd>Events in the same zone and time window, linked for context. <b>Not proof of cause</b>, and not proof that the same person was involved.</dd></div>
   <div><dt>Rule-based Decision</dt><dd>The severity (LOW, MEDIUM, HIGH), set by <b>fixed, versioned rules</b>. The AI never sets severity.</dd></div>
   <div><dt>Human verdict</dt><dd>Your review of one result: confirm, override or inconclusive. It is stored beside the detector output, which never changes.</dd></div>
   <div><dt>Investigation state</dt><dd>Where a group or result stands: open, in review or resolved.</dd></div>
   <div><dt>AI Investigator and specialists</dt><dd>Optional explanations with cited sources. They never decide, assign severity or take action.</dd></div>
  </dl>
 </details>;
}
