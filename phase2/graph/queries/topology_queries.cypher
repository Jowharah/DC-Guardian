// ============================================================
// DC-GUARDIAN
// Reusable Neo4j Topology Queries
// ============================================================


// ------------------------------------------------------------
// 1. Display the complete synthetic infrastructure hierarchy
// ------------------------------------------------------------

MATCH
    (s:Server)
    -[:LOCATED_IN]->
    (r:Rack)
    -[:LOCATED_IN]->
    (z:Zone)
    -[:PART_OF]->
    (dc:DataCenter)

RETURN
    dc.data_center_id AS data_center,
    z.zone_id AS zone,
    z.criticality AS zone_criticality,
    r.rack_id AS rack,
    s.server_id AS server,
    s.criticality AS server_criticality

ORDER BY
    zone,
    rack,
    server;


// ------------------------------------------------------------
// 2. Find the physical location of a specific server
//
// Change the server ID when running manually.
// ------------------------------------------------------------

MATCH
    (s:Server {
        server_id: "SRV-A1-01"
    })
    -[:LOCATED_IN]->
    (r:Rack)
    -[:LOCATED_IN]->
    (z:Zone)
    -[:PART_OF]->
    (dc:DataCenter)

RETURN
    s.server_id AS server,
    s.name AS server_name,
    s.criticality AS server_criticality,
    r.rack_id AS rack,
    z.zone_id AS zone,
    z.name AS zone_name,
    z.criticality AS zone_criticality,
    dc.data_center_id AS data_center;


// ------------------------------------------------------------
// 3. Show person authorization
// ------------------------------------------------------------

MATCH
    (p:Person)
    -[:AUTHORIZED_FOR]->
    (z:Zone)

RETURN
    p.person_id AS person,
    p.role AS role,
    z.zone_id AS authorized_zone

ORDER BY
    person,
    authorized_zone;


// ------------------------------------------------------------
// 4. Check P001 authorization for ZONE-C
//
// Expected result:
// no relationship / false in our current topology.
// ------------------------------------------------------------

MATCH
    (p:Person {
        person_id: "P001"
    }),
    (z:Zone {
        zone_id: "ZONE-C"
    })

RETURN EXISTS {
    MATCH
        (p)-[:AUTHORIZED_FOR]->(z)
} AS authorized;


// ------------------------------------------------------------
// 5. Show cameras and what they monitor
// ------------------------------------------------------------

MATCH
    (c:Camera)
    -[:MONITORS]->
    (target)

RETURN
    c.camera_id AS camera,
    labels(target) AS target_type,

    coalesce(
        target.zone_id,
        target.access_point_id
    ) AS target

ORDER BY
    camera,
    target;


// ------------------------------------------------------------
// 6. Show sensors and monitored infrastructure
// ------------------------------------------------------------

MATCH
    (s:Sensor)
    -[:MONITORS]->
    (target)

RETURN
    s.sensor_id AS sensor,
    s.sensor_type AS sensor_type,
    labels(target) AS target_type,

    coalesce(
        target.zone_id,
        target.equipment_id,
        target.server_id
    ) AS target

ORDER BY
    sensor,
    target;


// ------------------------------------------------------------
// 7. Find all infrastructure in ZONE-A
// ------------------------------------------------------------

MATCH
    (z:Zone {
        zone_id: "ZONE-A"
    })

OPTIONAL MATCH
    (r:Rack)-[:LOCATED_IN]->(z)

OPTIONAL MATCH
    (s:Server)-[:LOCATED_IN]->(r)

RETURN
    z.zone_id AS zone,
    r.rack_id AS rack,
    s.server_id AS server,
    s.criticality AS server_criticality

ORDER BY
    rack,
    server;


// ------------------------------------------------------------
// 8. Current graph node counts
// ------------------------------------------------------------

MATCH (n)

UNWIND labels(n) AS label

RETURN
    label,
    count(*) AS count

ORDER BY label;