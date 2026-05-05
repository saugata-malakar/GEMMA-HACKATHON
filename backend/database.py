"""
RAKSHA AI — Database Layer
SQLite-based persistence with async support. Zero-dependency offline storage.
"""

import aiosqlite
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from models import (
    Incident, Responder, TriageEntry, Alert,
    IncidentStatus, ResponderStatus
)

DATABASE_URL = os.getenv("DATABASE_URL", "./raksha.db")


# ─── Schema ───────────────────────────────────────────────────────────────────

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS incidents (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    type TEXT NOT NULL,
    severity REAL DEFAULT 0,
    status TEXT DEFAULT 'reported',
    coordinates TEXT NOT NULL,
    affected_count INTEGER,
    description TEXT NOT NULL,
    images TEXT DEFAULT '[]',
    ai_assessment TEXT,
    responders_assigned TEXT DEFAULT '[]',
    language TEXT DEFAULT 'en',
    reported_by TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS responders (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    team TEXT NOT NULL,
    phone TEXT,
    current_location TEXT,
    status TEXT DEFAULT 'available',
    skills TEXT DEFAULT '[]',
    equipment TEXT DEFAULT '[]',
    incidents_assigned TEXT DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS triage_entries (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    incident_id TEXT,
    patient_id TEXT NOT NULL,
    age_estimate TEXT,
    gender TEXT,
    symptoms TEXT DEFAULT '[]',
    vitals TEXT DEFAULT '{}',
    triage_color TEXT NOT NULL,
    ai_notes TEXT,
    responder_id TEXT,
    location TEXT
);

CREATE TABLE IF NOT EXISTS alerts (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    severity TEXT NOT NULL,
    affected_zones TEXT DEFAULT '[]',
    coordinates TEXT,
    radius_km REAL,
    languages TEXT DEFAULT '["en"]',
    translations TEXT DEFAULT '{}',
    incident_id TEXT,
    created_by TEXT
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id TEXT PRIMARY KEY,
    incident_id TEXT,
    language TEXT DEFAULT 'en',
    history TEXT DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sync_queue (
    id TEXT PRIMARY KEY,
    table_name TEXT NOT NULL,
    record_id TEXT NOT NULL,
    operation TEXT NOT NULL,
    data TEXT NOT NULL,
    created_at TEXT NOT NULL,
    synced INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);
CREATE INDEX IF NOT EXISTS idx_incidents_timestamp ON incidents(timestamp);
CREATE INDEX IF NOT EXISTS idx_responders_status ON responders(status);
CREATE INDEX IF NOT EXISTS idx_triage_incident ON triage_entries(incident_id);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
"""


# ─── Database Manager ─────────────────────────────────────────────────────────

class Database:
    def __init__(self, db_path: str = DATABASE_URL):
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Initialize database connection and create schema."""
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        # Enable WAL mode for better concurrent performance
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")
        # Create schema
        await self._conn.executescript(SCHEMA_SQL)
        await self._conn.commit()
        # Seed demo data on first run
        await self._seed_demo_data()

    async def disconnect(self):
        if self._conn:
            await self._conn.close()

    @property
    def conn(self) -> aiosqlite.Connection:
        if not self._conn:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._conn

    # ── Incidents ─────────────────────────────────────────────────────────────

    async def create_incident(self, incident: Incident) -> Incident:
        await self.conn.execute(
            """INSERT INTO incidents
               (id, timestamp, type, severity, status, coordinates, affected_count,
                description, images, ai_assessment, responders_assigned, language,
                reported_by, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                incident.id,
                incident.timestamp.isoformat(),
                incident.type.value,
                incident.severity,
                incident.status.value,
                incident.coordinates.json(),
                incident.affected_count,
                incident.description,
                json.dumps(incident.images),
                incident.ai_assessment.json() if incident.ai_assessment else None,
                json.dumps(incident.responders_assigned),
                incident.language,
                incident.reported_by,
                incident.updated_at.isoformat() if incident.updated_at else None,
            )
        )
        await self.conn.commit()
        await self._queue_sync("incidents", incident.id, "INSERT", incident.dict())
        return incident

    async def get_incident(self, incident_id: str) -> Optional[Incident]:
        async with self.conn.execute(
            "SELECT * FROM incidents WHERE id = ?", (incident_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return self._row_to_incident(dict(row))
        return None

    async def list_incidents(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Incident]:
        query = "SELECT * FROM incidents"
        params = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        async with self.conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_incident(dict(row)) for row in rows]

    async def update_incident(self, incident_id: str, updates: Dict[str, Any]) -> Optional[Incident]:
        updates["updated_at"] = datetime.utcnow().isoformat()
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [incident_id]
        await self.conn.execute(
            f"UPDATE incidents SET {set_clause} WHERE id = ?", values
        )
        await self.conn.commit()
        return await self.get_incident(incident_id)

    async def get_incident_count(self, status: Optional[str] = None) -> int:
        query = "SELECT COUNT(*) FROM incidents"
        params = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        async with self.conn.execute(query, params) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    def _row_to_incident(self, row: dict) -> Incident:
        row["coordinates"] = json.loads(row["coordinates"])
        row["images"] = json.loads(row.get("images", "[]"))
        row["responders_assigned"] = json.loads(row.get("responders_assigned", "[]"))
        if row.get("ai_assessment"):
            row["ai_assessment"] = json.loads(row["ai_assessment"])
        return Incident(**row)

    # ── Responders ────────────────────────────────────────────────────────────

    async def create_responder(self, responder: Responder) -> Responder:
        await self.conn.execute(
            """INSERT INTO responders
               (id, name, role, team, phone, current_location, status,
                skills, equipment, incidents_assigned, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                responder.id,
                responder.name,
                responder.role.value,
                responder.team,
                responder.phone,
                responder.current_location.json() if responder.current_location else None,
                responder.status.value,
                json.dumps(responder.skills),
                json.dumps(responder.equipment),
                json.dumps(responder.incidents_assigned),
                responder.created_at.isoformat(),
            )
        )
        await self.conn.commit()
        return responder

    async def get_responder(self, responder_id: str) -> Optional[Responder]:
        async with self.conn.execute(
            "SELECT * FROM responders WHERE id = ?", (responder_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return self._row_to_responder(dict(row))
        return None

    async def list_responders(
        self,
        status: Optional[str] = None,
        role: Optional[str] = None
    ) -> List[Responder]:
        query = "SELECT * FROM responders WHERE 1=1"
        params = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if role:
            query += " AND role = ?"
            params.append(role)
        query += " ORDER BY name"

        async with self.conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_responder(dict(row)) for row in rows]

    async def update_responder(self, responder_id: str, updates: Dict[str, Any]) -> Optional[Responder]:
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [responder_id]
        await self.conn.execute(
            f"UPDATE responders SET {set_clause} WHERE id = ?", values
        )
        await self.conn.commit()
        return await self.get_responder(responder_id)

    async def get_available_responders_count(self) -> int:
        async with self.conn.execute(
            "SELECT COUNT(*) FROM responders WHERE status = 'available'"
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    def _row_to_responder(self, row: dict) -> Responder:
        row["skills"] = json.loads(row.get("skills", "[]"))
        row["equipment"] = json.loads(row.get("equipment", "[]"))
        row["incidents_assigned"] = json.loads(row.get("incidents_assigned", "[]"))
        if row.get("current_location"):
            row["current_location"] = json.loads(row["current_location"])
        return Responder(**row)

    # ── Triage ────────────────────────────────────────────────────────────────

    async def create_triage_entry(self, entry: TriageEntry) -> TriageEntry:
        await self.conn.execute(
            """INSERT INTO triage_entries
               (id, timestamp, incident_id, patient_id, age_estimate, gender,
                symptoms, vitals, triage_color, ai_notes, responder_id, location)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                entry.id,
                entry.timestamp.isoformat(),
                entry.incident_id,
                entry.patient_id,
                entry.age_estimate,
                entry.gender,
                json.dumps(entry.symptoms),
                json.dumps(entry.vitals),
                entry.triage_color.value,
                entry.ai_notes,
                entry.responder_id,
                entry.location.json() if entry.location else None,
            )
        )
        await self.conn.commit()
        return entry

    async def list_triage_entries(
        self, incident_id: Optional[str] = None
    ) -> List[TriageEntry]:
        query = "SELECT * FROM triage_entries"
        params = []
        if incident_id:
            query += " WHERE incident_id = ?"
            params.append(incident_id)
        query += " ORDER BY timestamp DESC"

        async with self.conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_triage(dict(row)) for row in rows]

    def _row_to_triage(self, row: dict) -> TriageEntry:
        row["symptoms"] = json.loads(row.get("symptoms", "[]"))
        row["vitals"] = json.loads(row.get("vitals", "{}"))
        if row.get("location"):
            row["location"] = json.loads(row["location"])
        return TriageEntry(**row)

    # ── Alerts ────────────────────────────────────────────────────────────────

    async def create_alert(self, alert: Alert) -> Alert:
        await self.conn.execute(
            """INSERT INTO alerts
               (id, timestamp, title, message, severity, affected_zones,
                coordinates, radius_km, languages, translations, incident_id, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                alert.id,
                alert.timestamp.isoformat(),
                alert.title,
                alert.message,
                alert.severity.value,
                json.dumps(alert.affected_zones),
                alert.coordinates.json() if alert.coordinates else None,
                alert.radius_km,
                json.dumps(alert.languages),
                json.dumps(alert.translations),
                alert.incident_id,
                alert.created_by,
            )
        )
        await self.conn.commit()
        return alert

    async def list_alerts(self, limit: int = 20) -> List[Alert]:
        async with self.conn.execute(
            "SELECT * FROM alerts ORDER BY timestamp DESC LIMIT ?", (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_alert(dict(row)) for row in rows]

    def _row_to_alert(self, row: dict) -> Alert:
        row["affected_zones"] = json.loads(row.get("affected_zones", "[]"))
        row["languages"] = json.loads(row.get("languages", '["en"]'))
        row["translations"] = json.loads(row.get("translations", "{}"))
        if row.get("coordinates"):
            row["coordinates"] = json.loads(row["coordinates"])
        return Alert(**row)

    # ── Chat Sessions ─────────────────────────────────────────────────────────

    async def save_chat_session(
        self, session_id: str, history: list, language: str = "en",
        incident_id: Optional[str] = None
    ):
        now = datetime.utcnow().isoformat()
        await self.conn.execute(
            """INSERT INTO chat_sessions (session_id, incident_id, language, history, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(session_id) DO UPDATE SET history=excluded.history, updated_at=excluded.updated_at""",
            (session_id, incident_id, language, json.dumps(history), now, now)
        )
        await self.conn.commit()

    async def get_chat_session(self, session_id: str) -> Optional[Dict]:
        async with self.conn.execute(
            "SELECT * FROM chat_sessions WHERE session_id = ?", (session_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                r = dict(row)
                r["history"] = json.loads(r.get("history", "[]"))
                return r
        return None

    # ── Sync Queue ────────────────────────────────────────────────────────────

    async def _queue_sync(
        self, table_name: str, record_id: str,
        operation: str, data: dict
    ):
        """Queue a record for cloud sync when connectivity is restored."""
        import uuid
        await self.conn.execute(
            """INSERT INTO sync_queue (id, table_name, record_id, operation, data, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                str(uuid.uuid4()), table_name, record_id,
                operation, json.dumps(data, default=str),
                datetime.utcnow().isoformat()
            )
        )
        await self.conn.commit()

    async def get_pending_sync_items(self) -> List[Dict]:
        async with self.conn.execute(
            "SELECT * FROM sync_queue WHERE synced = 0 ORDER BY created_at LIMIT 100"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # ── Seed Data ─────────────────────────────────────────────────────────────

    async def _seed_demo_data(self):
        """Seed the database with realistic demo data on first launch."""
        # Check if already seeded
        async with self.conn.execute("SELECT COUNT(*) FROM responders") as cursor:
            count = (await cursor.fetchone())[0]
            if count > 0:
                return

        import uuid
        now = datetime.utcnow().isoformat()

        demo_responders = [
            ("NDRF Alpha Team", "ndrf", "Team Alpha", "+91-9876543210",
             '{"lat": 20.5937, "lng": 78.9629}', "available",
             '["search_rescue","rope_rescue","confined_space"]',
             '["hydraulic_spreaders","thermal_camera","gas_detector"]'),
            ("Dr. Priya Sharma", "medical", "Medical Unit 1", "+91-9876543211",
             '{"lat": 20.6037, "lng": 78.9729}', "available",
             '["emergency_medicine","triage","trauma"]',
             '["defibrillator","trauma_kit","oxygen"]'),
            ("Fire Brigade Unit 3", "firefighter", "Fire Unit 3", "+91-9876543212",
             '{"lat": 20.5837, "lng": 78.9529}', "available",
             '["fire_suppression","hazmat","rescue"]',
             '["fire_truck","hazmat_suit","thermal_scanner"]'),
            ("Volunteer Coordination", "volunteer", "District Volunteers", "+91-9876543213",
             '{"lat": 20.5937, "lng": 79.0000}', "available",
             '["first_aid","crowd_control","logistics"]',
             '["first_aid_kit","radio","megaphone"]'),
            ("NDRF Bravo Team", "ndrf", "Team Bravo", "+91-9876543214",
             '{"lat": 20.6200, "lng": 78.9400}', "dispatched",
             '["flood_rescue","boat_ops","swift_water"]',
             '["inflatable_boat","life_jackets","ropes"]'),
        ]

        for r in demo_responders:
            rid = str(uuid.uuid4())
            await self.conn.execute(
                """INSERT INTO responders
                   (id, name, role, team, phone, current_location, status,
                    skills, equipment, incidents_assigned, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '[]', ?)""",
                (rid, *r, now)
            )

        await self.conn.commit()


# ─── Singleton Instance ───────────────────────────────────────────────────────

db = Database()
