CREATE CONSTRAINT data_center_id_unique IF NOT EXISTS
FOR (n:DataCenter)
REQUIRE n.data_center_id IS UNIQUE;

CREATE CONSTRAINT zone_id_unique IF NOT EXISTS
FOR (n:Zone)
REQUIRE n.zone_id IS UNIQUE;

CREATE CONSTRAINT rack_id_unique IF NOT EXISTS
FOR (n:Rack)
REQUIRE n.rack_id IS UNIQUE;

CREATE CONSTRAINT server_id_unique IF NOT EXISTS
FOR (n:Server)
REQUIRE n.server_id IS UNIQUE;

CREATE CONSTRAINT camera_id_unique IF NOT EXISTS
FOR (n:Camera)
REQUIRE n.camera_id IS UNIQUE;

CREATE CONSTRAINT sensor_id_unique IF NOT EXISTS
FOR (n:Sensor)
REQUIRE n.sensor_id IS UNIQUE;

CREATE CONSTRAINT equipment_id_unique IF NOT EXISTS
FOR (n:Equipment)
REQUIRE n.equipment_id IS UNIQUE;

CREATE CONSTRAINT access_point_id_unique IF NOT EXISTS
FOR (n:AccessPoint)
REQUIRE n.access_point_id IS UNIQUE;

CREATE CONSTRAINT person_id_unique IF NOT EXISTS
FOR (n:Person)
REQUIRE n.person_id IS UNIQUE;

CREATE CONSTRAINT source_ip_unique IF NOT EXISTS
FOR (n:SourceIP)
REQUIRE n.address IS UNIQUE;

CREATE CONSTRAINT event_id_unique IF NOT EXISTS
FOR (n:Event)
REQUIRE n.event_id IS UNIQUE;