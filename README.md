# ParkOS – Smart Parking Computing Platform
**B.Tech CSE Project for Computer Architecture & Parallel Processing (CAPP)**

![ParkOS Dashboard Mockup](css/styles.css)

---

## 1. Project Overview
**ParkOS** is a smart parking platform that demonstrates how core **Computer Architecture and Parallel Processing (CAPP)** principles can be applied to solve real-world problems:
- Preventing **double-allocation race conditions** during simultaneous booking attempts.
- Eliminating vehicle starvation during peak congestion using an **FCFS waiting queue**.
- Accelerating high-frequency slot status lookups using an educational **Direct-Mapped Cache simulation**.
- Organizing physical parking bays as **contiguous memory words** with offset pointer arithmetic.

The application features a modern **Teal-Blue and Dark Navy** dashboard with full responsive layout, interactive parking map with 24 individual slots, booking history, analytics charts, and a dedicated **Live CAPP Demonstration Console**.

---

## 2. Key CAPP Concepts Implemented

### Concept 1: Memory & Data Organization
- Parking slots are modeled as a contiguous array in memory starting at base address `0x1000`.
- Each slot record is represented as a 32-byte C-style data structure (`0x20` bytes):
  ```c
  struct ParkSlot {
      char id[4];          // Offset 0x00: Slot Identifier (e.g., "A01")
      uint8_t zone;        // Offset 0x04: Campus Zone (A, B, C)
      uint8_t floor;       // Offset 0x05: Level (0, 1, 2)
      uint8_t type;        // Offset 0x06: 0=Car, 1=Bike, 2=EV
      uint8_t status;      // Offset 0x07: 0=Available, 1=Occupied, 2=Reserved
      char vehicleNo[12];  // Offset 0x08: License Plate
      uint64_t timestamp;  // Offset 0x14: Epoch timestamp
      uint8_t pad[4];      // Total Size = 32 Bytes (Aligned to 32-byte cache line)
  };
  ```
- Fast random access is performed via pointer arithmetic:
  $$\text{Memory Address} = \text{Base Address} + (\text{Slot Index} \times 32)$$
  - Slot A01 (Index 0): `0x1000`
  - Slot A02 (Index 1): `0x1020`
  - Slot A03 (Index 2): `0x1040`

### Concept 2: First-Come, First-Served (FCFS) Queue
- When parking slots are completely occupied, incoming vehicles are not dropped.
- Requests enter a FIFO waiting queue buffer.
- Head pointer points to the earliest arriving vehicle; tail pointer enqueues new requests.
- When an occupied slot is released, the FCFS dispatcher dequeues the head vehicle and immediately allocates the freed slot, preventing vehicle starvation.

### Concept 3: Atomic Allocation & Critical Section Simulation
- **The Problem (Race Condition):** Two concurrent worker threads (Thread A and Thread B) attempt to book Slot `A05` at the same time. Thread A reads `status == AVAILABLE`, but context switches before committing; Thread B also reads `AVAILABLE` and commits; Thread A resumes and overwrites, causing an unsafe double-booking!
- **The Solution (Mutual Exclusion / Mutex):** ParkOS implements a Mutex Lock (simulating atomic Test-and-Set / Compare-and-Swap in hardware, and `threading.Lock()` / database transactions in backend). The slot verification and status write are serialized inside a protected **Critical Section**. Thread A acquires the lock; Thread B is blocked or redirected safely.

### Concept 4: Direct-Mapped Cache Simulation
- Simulates an **L1 Cache with 8 Cache Lines** (`Line 0` to `Line 7`).
- Mapping function:
  $$\text{Cache Line Index} = (\text{Slot ID Hash}) \pmod 8$$
- **Cache Hit:** If `Valid == 1` and `Tag == Requested_ID`, data is served instantly (simulated latency: **1.2 ns**).
- **Cache Miss:** If `Valid == 0` or tag does not match, data is fetched from slower main memory / database (simulated latency: **45.0 ns**), and the cache line is loaded.
- **Cache Invalidation:** When a slot status changes upon booking or release, the cache line is invalidated (`Valid = 0`) to guarantee cache coherence and prevent stale reads.

---

## 3. Project Directory Structure

```
Capp_Project/
├── index.html             # Main Single Page App (Dashboard, Map, Demo, Viva guide)
├── run_parkos.bat         # 1-click Windows launcher
├── app.py                 # Python Flask backend server + SQLite + Mutex Lock
├── database.db            # SQLite database (auto-generated on backend run)
├── README.md              # Full documentation, concepts, and viva guide
├── css/
│   └── styles.css         # Teal-blue & dark navy modern UI styling
└── js/
    ├── data.js            # Initial realistic parking slots, vehicles, and bookings
    ├── capp-engine.js     # CAPP Algorithms (Memory, FCFS Queue, Mutex, Cache)
    └── app.js             # UI Controller, DOM manipulation, charts, modals
```

---

## 4. How to Run the Application

### Option A: 1-Click Launch (Recommended for Windows)
Double-click `run_parkos.bat` in the project root folder.
- If Python and Flask are installed, it automatically starts the Flask server and launches `http://127.0.0.1:5000` in your browser.
- If Python is not installed or configured, it automatically launches `index.html` directly in your browser with full client-side emulation!

### Option B: Python Flask + SQLite Backend
1. Open PowerShell or Command Prompt in `Capp_Project/`:
   ```bash
   pip install flask
   python app.py
   ```
2. Open your browser and navigate to:
   ```
   http://127.0.0.1:5000
   ```

### Option C: Standalone Zero-Dependency Browser Run
Double-click `index.html` directly or open it with Google Chrome, Microsoft Edge, or Mozilla Firefox.
All features—including the interactive parking map, 6 CAPP live demos, canvas charts, and LocalStorage persistence—work 100% out of the box without requiring any installation or command-line setup.

---

## 5. Live Demonstration Guide (For Evaluator & Viva)

Navigate to the **"Live CAPP Demo"** tab in the sidebar:

1. **Button 1 – Book a Slot:**
   - Demonstrates random plate generation and $O(1)$ memory slot scan and atomic allocation.
2. **Button 2 – FCFS Queue:**
   - Enqueues three vehicles into the waiting buffer and processes them one by one in FIFO order.
3. **Button 3 – Concurrent Request Simulation:**
   - Demonstrates an unprotected race condition between Core-0 and Core-1 resulting in a double-booking bug.
   - Immediately runs the protected Mutex version showing atomic isolation and safe allocation.
4. **Button 4 – Cache Hit / Miss:**
   - Queries Slot A01 (Miss: 45ns), queries A01 again (Hit: 1.2ns), queries B02, and observes the hit ratio percentage rise.
5. **Button 5 – Release Slot:**
   - Frees an occupied slot in memory, marks cache line invalid, and auto-dispatches any waiting vehicle from the FCFS queue.
6. **Button 6 – Reset Demo:**
   - Restores the system to factory demo state.

---

## 6. Viva Voce Questions & Answers

**Q1: Why is mutual exclusion critical in a parking system?**
*Answer:* In parallel computing environments, multiple client requests run on separate threads. If two threads read the same available slot simultaneously, both see it as free and commit their booking, resulting in double allocation. A mutex serializes the check-and-allocate logic into a critical section.

**Q2: How does the Direct-Mapped Cache work in your project?**
*Answer:* Each slot ID is hashed and mapped to one of 8 cache lines using modulo arithmetic ($\text{Index} = \text{Hash} \pmod 8$). Each line stores a Valid bit, Tag, and Slot Data. If the tag matches and the valid bit is 1, a cache hit occurs at 1.2ns latency. If not, a cache miss triggers a 45ns memory read and updates the cache line.

**Q3: How does the FCFS queue solve the starvation problem?**
*Answer:* Starvation happens when lower-priority requests are indefinitely postponed by newer incoming requests. FCFS uses strict arrival timestamp ordering so every waiting vehicle is guaranteed service as soon as slots are vacated.

**Q4: How does memory address calculation work for slots?**
*Answer:* Physical memory layout is simulated with continuous 32-byte structs aligned to cache boundaries. The CPU computes $\text{Address} = \text{Base} + (\text{Index} \times 32)$ using bit shifting ($\text{Index} \ll 5$), enabling constant-time $O(1)$ address resolution.

---

## 7. License & Credits
Developed for **B.Tech Computer Science & Engineering (CAPP Course Project)**.
Designed with HTML5, CSS3, JavaScript (ES6+), Python Flask, and SQLite.
