// ============================================================
// DC-GUARDIAN
// Reusable SSH / Cybersecurity Graph Queries
// ============================================================


// ------------------------------------------------------------
// 1. List SSH events
// ------------------------------------------------------------

MATCH (e:Event {
    domain: "CYBERSECURITY",
    event_type: "SSH_BEHAVIOR_ASSESSMENT"
})

RETURN
    e.event_id AS event_id,
    e.timestamp AS timestamp,
    e.state AS state,
    e.confidence AS confidence,
    e.detector_votes AS detector_votes,
    e.detector_combination AS detector_combination,
    e.scenario_id AS scenario_id

ORDER BY e.timestamp;


// ------------------------------------------------------------
// 2. SSH event -> Source IP
// ------------------------------------------------------------

MATCH
    (e:Event)
    -[:ORIGINATED_FROM]->
    (ip:SourceIP)

WHERE
    e.event_type =
        "SSH_BEHAVIOR_ASSESSMENT"

RETURN
    e.event_id AS event_id,
    e.state AS state,
    ip.address AS source_ip;


// ------------------------------------------------------------
// 3. SSH event -> target server
// ------------------------------------------------------------

MATCH
    (e:Event)
    -[:TARGETS]->
    (s:Server)

WHERE
    e.event_type =
        "SSH_BEHAVIOR_ASSESSMENT"

RETURN
    e.event_id AS event_id,
    e.state AS state,
    s.server_id AS target_server,
    s.name AS server_name,
    s.criticality AS server_criticality;


// ------------------------------------------------------------
// 4. Full cyber -> physical context
// ------------------------------------------------------------

MATCH
    (e:Event)
    -[:TARGETS]->
    (s:Server)
    -[:LOCATED_IN]->
    (r:Rack)
    -[:LOCATED_IN]->
    (z:Zone)
    -[:PART_OF]->
    (dc:DataCenter)

MATCH
    (e)-[:ORIGINATED_FROM]->
    (ip:SourceIP)

WHERE
    e.event_type =
        "SSH_BEHAVIOR_ASSESSMENT"

RETURN
    e.event_id AS event_id,
    e.timestamp AS timestamp,
    e.state AS ssh_assessment,
    e.confidence AS confidence,

    ip.address AS source_ip,

    s.server_id AS target_server,
    s.criticality AS server_criticality,

    r.rack_id AS rack,

    z.zone_id AS zone,
    z.criticality AS zone_criticality,

    dc.data_center_id AS data_center

ORDER BY e.timestamp;


// ------------------------------------------------------------
// 5. High-confidence SSH anomalies and affected assets
// ------------------------------------------------------------

MATCH
    (e:Event {
        state: "HIGH_CONFIDENCE_ANOMALY"
    })
    -[:TARGETS]->
    (s:Server)
    -[:LOCATED_IN]->
    (r:Rack)
    -[:LOCATED_IN]->
    (z:Zone)

WHERE
    e.domain = "CYBERSECURITY"

RETURN
    e.event_id AS event_id,
    e.timestamp AS timestamp,
    e.detector_votes AS detector_votes,
    e.detector_combination AS detectors,

    s.server_id AS server,
    s.criticality AS server_criticality,

    r.rack_id AS rack,

    z.zone_id AS zone,
    z.criticality AS zone_criticality;


// ------------------------------------------------------------
// 6. Inspect synthetic scenario provenance
// ------------------------------------------------------------

MATCH (e:Event)

WHERE
    e.synthetic_mapping = true

RETURN
    e.event_id AS mapped_event,
    e.scenario_id AS scenario_id,
    e.mapping_type AS mapping_type,
    e.original_event_id AS original_event,
    e.original_timestamp AS original_timestamp,
    e.timestamp AS scenario_timestamp

ORDER BY e.timestamp;


// ------------------------------------------------------------
// 7. Find events affecting ZONE-A
// ------------------------------------------------------------

MATCH
    (e:Event)
    -[:TARGETS]->
    (s:Server)
    -[:LOCATED_IN]->
    (r:Rack)
    -[:LOCATED_IN]->
    (z:Zone {
        zone_id: "ZONE-A"
    })

RETURN
    e.event_id AS event_id,
    e.domain AS domain,
    e.event_type AS event_type,
    e.state AS state,
    e.timestamp AS timestamp,
    s.server_id AS asset,
    r.rack_id AS rack,
    z.zone_id AS zone

ORDER BY e.timestamp;