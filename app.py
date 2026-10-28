"""
=============================================================================
ParkOS – Smart Parking Computing Platform
Backend Engine: Python Flask + SQLite + Threading Mutex

Demonstrating Computer Architecture and Parallel Processing (CAPP) Concepts:
- Concept 1: Memory & Data Organization (Struct layout & address calculation)
- Concept 2: FCFS Queue (FIFO vehicle buffer & dispatch)
- Concept 3: Atomic Allocation & Critical Section (threading.Lock mutual exclusion)
- Concept 4: Direct-Mapped Cache Simulation (L1 Cache lines, Tag matching, Latency)
=============================================================================
"""

import os
import sqlite3
import threading
import time
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder='.', static_url_path='')

DATABASE_FILE = 'database.db'

# ---------------------------------------------------------------------------
# CAPP Concept 3: Mutual Exclusion (Mutex Lock)
# Thread lock simulating atomic hardware test-and-set to protect critical section
# ---------------------------------------------------------------------------
parking_mutex = threading.Lock()

# ---------------------------------------------------------------------------
# CAPP Concept 2: FCFS Waiting Queue in Memory
# ---------------------------------------------------------------------------
fcfs_waiting_queue = []

# ---------------------------------------------------------------------------
# CAPP Concept 4: Direct-Mapped Cache Simulation in Memory
# 8 Lines (Index 0 to 7)
# ---------------------------------------------------------------------------
CACHE_LINE_COUNT = 8
l1_cache = [{
    "index": i,
    "valid": 0,
    "tag": None,
    "data": None
} for i in range(CACHE_LINE_COUNT)]

cache_stats = {
    "accesses": 0,
    "hits": 0,
    "misses": 0,
    "hit_ratio": 0.0
}

# ---------------------------------------------------------------------------
# Database Initialization & Helpers
# ---------------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes SQLite schema and populates default 24 slots."""
    conn = get_db()
    cursor = conn.cursor()

    # Parking Slots Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS slots (
            id TEXT PRIMARY KEY,
            zone TEXT NOT NULL,
            floor INTEGER NOT NULL,
            type TEXT NOT NULL,
            status TEXT NOT NULL,  -- 'available', 'occupied', 'reserved'
            vehicle_no TEXT,
            owner TEXT,
            booked_at TEXT,
            mem_address TEXT NOT NULL
        )
    ''')

    # Bookings History Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id TEXT PRIMARY KEY,
            vehicle_no TEXT NOT NULL,
            slot_id TEXT NOT NULL,
            type TEXT NOT NULL,
            owner TEXT,
            time TEXT NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL,  -- 'Parked', 'Completed'
            fee INTEGER NOT NULL
        )
    ''')

    # Vehicles Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vehicles (
            plate TEXT PRIMARY KEY,
            model TEXT NOT NULL,
            type TEXT NOT NULL,
            owner TEXT NOT NULL,
            phone TEXT
        )
    ''')

    conn.commit()

    # Seed initial data if empty
    cursor.execute('SELECT COUNT(*) FROM slots')
    if cursor.fetchone()[0] == 0:
        seed_default_data(conn)
    conn.close()

def seed_default_data(conn):
    cursor = conn.cursor()
    cursor.execute('DELETE FROM slots')
    cursor.execute('DELETE FROM bookings')
    cursor.execute('DELETE FROM vehicles')

    # Seed 24 Slots (Zones A, B, C)
    # Base memory address 0x1000 with 32-byte (0x20) offsets
    base_addr = 0x1000
    struct_size = 0x20

    default_slots = [
        # Zone A
        ('A01', 'A', 0, 'Four-Wheeler', 'occupied', 'HR26AB1234', 'Aarav Sharma', '09:15 AM'),
        ('A02', 'A', 0, 'Four-Wheeler', 'available', None, None, None),
        ('A03', 'A', 0, 'Four-Wheeler', 'reserved', 'DL3CBB8899', 'Dr. V. Raman', '08:30 AM'),
        ('A04', 'A', 0, 'Four-Wheeler', 'available', None, None, None),
        ('A05', 'A', 0, 'Four-Wheeler', 'available', None, None, None),
        ('A06', 'A', 0, 'Four-Wheeler', 'occupied', 'KA01MN2468', 'Rohit Verma', '10:20 AM'),
        ('A07', 'A', 0, 'Four-Wheeler', 'available', None, None, None),
        ('A08', 'A', 0, 'Four-Wheeler', 'available', None, None, None),
        # Zone B
        ('B01', 'B', 1, 'Two-Wheeler', 'available', None, None, None),
        ('B02', 'B', 1, 'Two-Wheeler', 'occupied', 'DL8CAF5678', 'Priya Nair', '09:32 AM'),
        ('B03', 'B', 1, 'Two-Wheeler', 'available', None, None, None),
        ('B04', 'B', 1, 'Two-Wheeler', 'available', None, None, None),
        ('B05', 'B', 1, 'Four-Wheeler', 'available', None, None, None),
        ('B06', 'B', 1, 'Four-Wheeler', 'occupied', 'MH12KL7890', 'Ananya Deshmukh', '10:22 AM'),
        ('B07', 'B', 1, 'Four-Wheeler', 'available', None, None, None),
        ('B08', 'B', 1, 'Four-Wheeler', 'available', None, None, None),
        # Zone C
        ('C01', 'C', 2, 'EV-Charging', 'occupied', 'UP16ET9087', 'Vikram Singh', '10:05 AM'),
        ('C02', 'C', 2, 'EV-Charging', 'available', None, None, None),
        ('C03', 'C', 2, 'EV-Charging', 'available', None, None, None),
        ('C04', 'C', 2, 'EV-Charging', 'reserved', 'MH02EV5544', 'Dean Academics', '08:00 AM'),
        ('C05', 'C', 2, 'Four-Wheeler', 'available', None, None, None),
        ('C06', 'C', 2, 'Four-Wheeler', 'available', None, None, None),
        ('C07', 'C', 2, 'Four-Wheeler', 'available', None, None, None),
        ('C08', 'C', 2, 'Four-Wheeler', 'available', None, None, None),
    ]

    for idx, (sid, zone, flr, stype, status, vno, owner, btime) in enumerate(default_slots):
        mem_hex = f"0x{(base_addr + idx * struct_size):04X}"
        cursor.execute('''
            INSERT INTO slots (id, zone, floor, type, status, vehicle_no, owner, booked_at, mem_address)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (sid, zone, flr, stype, status, vno, owner, btime, mem_hex))

    # Initial Bookings
    initial_bookings = [
        ('BK-1001', 'HR26AB1234', 'A01', 'Four-Wheeler', 'Aarav Sharma', '09:15 AM', '2026-10-28', 'Parked', 50),
        ('BK-1002', 'DL8CAF5678', 'B02', 'Two-Wheeler', 'Priya Nair', '09:32 AM', '2026-10-28', 'Parked', 20),
        ('BK-1003', 'UP16ET9087', 'C01', 'EV-Charging', 'Vikram Singh', '10:05 AM', '2026-10-28', 'Parked', 100),
        ('BK-1004', 'KA01MN2468', 'A06', 'Four-Wheeler', 'Rohit Verma', '10:20 AM', '2026-10-28', 'Parked', 50),
        ('BK-1005', 'MH12KL7890', 'B06', 'Four-Wheeler', 'Ananya Deshmukh', '10:22 AM', '2026-10-28', 'Parked', 50),
    ]
    for b in initial_bookings:
        cursor.execute('''
            INSERT INTO bookings (id, vehicle_no, slot_id, type, owner, time, date, status, fee)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', b)

    # Initial Vehicles
    initial_veh = [
        ('HR26AB1234', 'Hyundai Creta', 'Four-Wheeler', 'Aarav Sharma', '+91 98765 43210'),
        ('DL8CAF5678', 'Royal Enfield Classic', 'Two-Wheeler', 'Priya Nair', '+91 98111 22334'),
        ('UP16ET9087', 'Tata Nexon EV', 'EV-Charging', 'Vikram Singh', '+91 98450 99887'),
        ('KA01MN2468', 'Honda City', 'Four-Wheeler', 'Rohit Verma', '+91 99887 66554'),
        ('MH12KL7890', 'Maruti Suzuki Swift', 'Four-Wheeler', 'Ananya Deshmukh', '+91 97654 32109'),
        ('DL3CBB8899', 'Toyota Camry Hybrid', 'Four-Wheeler', 'Dr. V. Raman', '+91 98100 11223'),
        ('MH02EV5544', 'MG ZS EV', 'EV-Charging', 'Dean Academics', '+91 98200 44556')
    ]
    for v in initial_veh:
        cursor.execute('''
            INSERT INTO vehicles (plate, model, type, owner, phone)
            VALUES (?, ?, ?, ?, ?)
        ''', v)

    conn.commit()

# ---------------------------------------------------------------------------
# Static Route (Serves Frontend)
# ---------------------------------------------------------------------------
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

# ---------------------------------------------------------------------------
# REST API Endpoints
# ---------------------------------------------------------------------------

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        "status": "UP",
        "system": "ParkOS – Smart Parking Computing Platform",
        "capp_features": ["Memory Mapping (32B)", "FCFS Queue (FIFO)", "Atomic Mutex Lock", "Direct-Mapped L1 Cache"],
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/slots', methods=['GET'])
def get_slots():
    conn = get_db()
    rows = conn.execute('SELECT * FROM slots ORDER BY id ASC').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# ---------------------------------------------------------------------------
# CAPP Concept 3: Atomic Slot Booking with Mutex Lock
# ---------------------------------------------------------------------------
@app.route('/api/book', methods=['POST'])
def book_slot():
    data = request.json or {}
    vehicle_no = (data.get('vehicle_no') or '').strip().upper()
    owner = data.get('owner') or 'Campus Driver'
    vtype = data.get('type') or 'Four-Wheeler'
    slot_id = data.get('slot_id')

    if not vehicle_no:
        return jsonify({"success": False, "message": "Vehicle number is required."}), 400

    conn = get_db()
    cursor = conn.cursor()

    # Check duplicate active booking for this vehicle!
    cursor.execute("SELECT id FROM slots WHERE vehicle_no = ? AND status = 'occupied'", (vehicle_no,))
    if cursor.fetchone():
        conn.close()
        return jsonify({
            "success": False, 
            "message": f"Vehicle {vehicle_no} is already parked. Duplicate allocation rejected."
        }), 409

    # --- CRITICAL SECTION PROTECTED BY MUTEX LOCK ---
    with parking_mutex:
        target_slot = None

        if slot_id and slot_id != 'auto':
            cursor.execute("SELECT * FROM slots WHERE id = ?", (slot_id,))
            target_slot = cursor.fetchone()
            if not target_slot or target_slot['status'] != 'available':
                conn.close()
                return jsonify({"success": False, "message": f"Slot {slot_id} is not available."}), 400
        else:
            # Auto Allocate: First available matching vehicle type
            cursor.execute("SELECT * FROM slots WHERE status = 'available' AND type = ? LIMIT 1", (vtype,))
            target_slot = cursor.fetchone()
            if not target_slot:
                # Any standard available slot
                cursor.execute("SELECT * FROM slots WHERE status = 'available' LIMIT 1")
                target_slot = cursor.fetchone()

        if not target_slot:
            # Enqueue into FCFS Queue
            fcfs_node = {
                "id": f"Q-{int(time.time() * 1000) % 10000}",
                "vehicle_no": vehicle_no,
                "type": vtype,
                "owner": owner,
                "enqueued_at": datetime.now().strftime("%H:%M:%S")
            }
            fcfs_waiting_queue.append(fcfs_node)
            conn.close()
            return jsonify({
                "success": False,
                "enqueued": True,
                "queue_position": len(fcfs_waiting_queue),
                "message": f"No available slots. Vehicle {vehicle_no} enqueued in FCFS buffer."
            }), 202

        # Atomic Assignment
        sid = target_slot['id']
        btime = datetime.now().strftime("%I:%M %p")
        bdate = datetime.now().strftime("%Y-%m-%d")
        bkid = f"BK-{int(time.time()) % 10000:04d}"

        cursor.execute('''
            UPDATE slots 
            SET status = 'occupied', vehicle_no = ?, owner = ?, booked_at = ?
            WHERE id = ?
        ''', (vehicle_no, owner, btime, sid))

        fee = 20 if vtype == 'Two-Wheeler' else (100 if vtype == 'EV-Charging' else 50)
        cursor.execute('''
            INSERT INTO bookings (id, vehicle_no, slot_id, type, owner, time, date, status, fee)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'Parked', ?)
        ''', (bkid, vehicle_no, sid, vtype, owner, btime, bdate, fee))

        conn.commit()

        # Invalidate Cache
        invalidate_cache(sid)

    conn.close()
    return jsonify({
        "success": True,
        "slot_id": sid,
        "booking_id": bkid,
        "message": f"Slot {sid} atomically allocated to {vehicle_no}!"
    })

# ---------------------------------------------------------------------------
# Release Slot + FCFS Queue Auto-Dispatch
# ---------------------------------------------------------------------------
@app.route('/api/release', methods=['POST'])
def release_slot():
    data = request.json or {}
    slot_id = data.get('slot_id')

    if not slot_id:
        return jsonify({"success": False, "message": "slot_id is required."}), 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM slots WHERE id = ?", (slot_id,))
    slot = cursor.fetchone()
    if not slot or slot['status'] == 'available':
        conn.close()
        return jsonify({"success": False, "message": "Slot is already empty or does not exist."}), 400

    # Mark active booking as Completed
    cursor.execute("UPDATE bookings SET status = 'Completed' WHERE slot_id = ? AND status = 'Parked'", (slot_id,))

    # Free the slot
    cursor.execute('''
        UPDATE slots
        SET status = 'available', vehicle_no = NULL, owner = NULL, booked_at = NULL
        WHERE id = ?
    ''', (slot_id,))
    conn.commit()

    # Invalidate Cache
    invalidate_cache(slot_id)

    # Check FCFS Waiting Queue!
    dispatched = None
    if fcfs_waiting_queue:
        next_veh = fcfs_waiting_queue.pop(0)  # FIFO Dequeue
        btime = datetime.now().strftime("%I:%M %p")
        bdate = datetime.now().strftime("%Y-%m-%d")
        bkid = f"BK-{int(time.time()) % 10000:04d}"

        cursor.execute('''
            UPDATE slots
            SET status = 'occupied', vehicle_no = ?, owner = ?, booked_at = ?
            WHERE id = ?
        ''', (next_veh['vehicle_no'], next_veh['owner'], btime, slot_id))

        cursor.execute('''
            INSERT INTO bookings (id, vehicle_no, slot_id, type, owner, time, date, status, fee)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'Parked', 50)
        ''', (bkid, next_veh['vehicle_no'], slot_id, next_veh['type'], next_veh['owner'], btime, bdate))
        conn.commit()
        dispatched = next_veh

    conn.close()
    return jsonify({
        "success": True,
        "slot_id": slot_id,
        "dispatched_from_queue": dispatched,
        "message": f"Slot {slot_id} freed." + (f" Auto-allocated to waiting vehicle {dispatched['vehicle_no']}!" if dispatched else "")
    })

# ---------------------------------------------------------------------------
# CAPP Concept 4: Direct Mapped Cache Lookup Simulator
# ---------------------------------------------------------------------------
def invalidate_cache(slot_id):
    h = sum(ord(c) for c in slot_id) % CACHE_LINE_COUNT
    if l1_cache[h]["tag"] == slot_id and l1_cache[h]["valid"] == 1:
        l1_cache[h]["valid"] = 0

@app.route('/api/cache/access/<slot_id>', methods=['GET'])
def access_cache(slot_id):
    cache_stats["accesses"] += 1
    h = sum(ord(c) for c in slot_id) % CACHE_LINE_COUNT
    line = l1_cache[h]

    if line["valid"] == 1 and line["tag"] == slot_id:
        cache_stats["hits"] += 1
        cache_stats["hit_ratio"] = round((cache_stats["hits"] / cache_stats["accesses"]) * 100, 1)
        return jsonify({
            "status": "HIT",
            "line_index": h,
            "tag": slot_id,
            "latency_ns": 1.2,
            "data": line["data"],
            "stats": cache_stats
        })
    else:
        cache_stats["misses"] += 1
        cache_stats["hit_ratio"] = round((cache_stats["hits"] / cache_stats["accesses"]) * 100, 1)

        # Fetch from DB / RAM
        conn = get_db()
        row = conn.execute("SELECT * FROM slots WHERE id = ?", (slot_id,)).fetchone()
        conn.close()

        slot_data = dict(row) if row else None
        line["valid"] = 1
        line["tag"] = slot_id
        line["data"] = slot_data

        return jsonify({
            "status": "MISS",
            "line_index": h,
            "tag": slot_id,
            "latency_ns": 45.0,
            "data": slot_data,
            "stats": cache_stats
        })

@app.route('/api/cache', methods=['GET'])
def get_cache_state():
    return jsonify({
        "lines": l1_cache,
        "stats": cache_stats
    })

# ---------------------------------------------------------------------------
# CAPP Concept 3: Race Condition Simulator Endpoint
# ---------------------------------------------------------------------------
@app.route('/api/simulate/race', methods=['POST'])
def simulate_race():
    """Demonstrates simultaneous booking of Slot A05 with vs without mutex."""
    data = request.json or {}
    use_mutex = data.get('use_mutex', True)

    conn = get_db()
    # Reset slot A05
    conn.execute("UPDATE slots SET status = 'available', vehicle_no = NULL WHERE id = 'A05'")
    conn.commit()

    results = []

    def worker(worker_name, plate):
        c = get_db()
        if use_mutex:
            with parking_mutex:
                row = c.execute("SELECT status FROM slots WHERE id = 'A05'").fetchone()
                if row and row['status'] == 'available':
                    time.sleep(0.04)  # Simulate processing delay
                    c.execute("UPDATE slots SET status = 'occupied', vehicle_no = ? WHERE id = 'A05'", (plate,))
                    c.commit()
                    results.append({"worker": worker_name, "status": "SUCCESS", "plate": plate})
                else:
                    results.append({"worker": worker_name, "status": "REJECTED_BLOCKED", "plate": plate})
        else:
            # Unprotected race condition!
            row = c.execute("SELECT status FROM slots WHERE id = 'A05'").fetchone()
            if row and row['status'] == 'available':
                time.sleep(0.04)  # Interleaved context switch!
                c.execute("UPDATE slots SET status = 'occupied', vehicle_no = ? WHERE id = 'A05'", (plate,))
                c.commit()
                results.append({"worker": worker_name, "status": "OVERWROTE_SLOT", "plate": plate})
        c.close()

    t1 = threading.Thread(target=worker, args=("Thread-Core-0", "HR-CAR-1111"))
    t2 = threading.Thread(target=worker, args=("Thread-Core-1", "DL-CAR-2222"))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    conn.close()
    return jsonify({
        "use_mutex": use_mutex,
        "outcome": results,
        "conclusion": "Mutex preserved critical section" if use_mutex else "Race condition occurred: double-allocation bug!"
    })

# ---------------------------------------------------------------------------
# Reset API
# ---------------------------------------------------------------------------
@app.route('/api/reset', methods=['POST'])
def reset_demo():
    conn = get_db()
    seed_default_data(conn)
    conn.close()

    global fcfs_waiting_queue, l1_cache, cache_stats
    fcfs_waiting_queue = []
    l1_cache = [{"index": i, "valid": 0, "tag": None, "data": None} for i in range(CACHE_LINE_COUNT)]
    cache_stats = {"accesses": 0, "hits": 0, "misses": 0, "hit_ratio": 0.0}

    return jsonify({"success": True, "message": "Database and CAPP registers reset to defaults."})

# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    print(f"""
    ===================================================================
    ParkOS – Smart Parking Computing Platform
    Backend Server Listening on: http://127.0.0.1:{port}
    
    Academic CAPP Modules:
    - Base Memory Address: 0x1000 (32-byte Slot struct)
    - FCFS Non-Preemptive Queue: Active
    - Atomic Allocation Critical Section: Protected by Mutex Lock
    - L1 Direct-Mapped Cache: 8 Lines Enabled
    ===================================================================
    """)
    app.run(host='0.0.0.0', port=port, debug=True)
