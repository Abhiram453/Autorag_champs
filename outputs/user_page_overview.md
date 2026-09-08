# Aura Automotive - User Page Layout Breakdown (`Diagnostic Hub`)

The **User Page** (or **Diagnostic Hub**) is the primary workspace designed for service center technicians, mechanics, and diagnostic analysts. It replaces static paper repair manuals with a dynamic, AI-grounded split-screen interface.

---

## 🎨 Interactive Live HTML Mockup

You can open the generated live HTML mockup in your browser to view the interface:
📄 [outputs/user_page_mockup.html](file:///d:/RAG/Autorag_champs/outputs/user_page_mockup.html)

---

## 📐 Layout Architecture

The User Page is structured into 4 primary functional areas:

```
+-----------------------------------------------------------------------------------+
| Top Navigation & VIN Search Bar                                                   |
| [ Enter VIN / Model ... ]   |   [ 2023 SUV Model X | VIN: 1G1RC6... | AWD Hybrid ] |
+------------------------------------+----------------------------------------------+
| Left Panel: AI Assistant Chat      | Right Panel: Interactive Instruction Viewer  |
|                                    |                                              |
| - Vehicle DTC Report (e.g. P0300)  | - Header: Task Name & Est. Time (45 min)    |
| - Interactive Q&A conversation     | - Step 1: Disconnect Battery (+Safety Alert) |
| - Tech Spec Tables (e.g. 0.4-0.6Ω) | - Step 2: Remove Engine Cover (+Diagram)     |
| - "Ask a technical question..."    | - Step 3: Disconnect Harness (+Connector ID) |
|                                    |                                              |
+------------------------------------+----------------------------------------------+
| Bottom Action Bar                                                                 |
| Diagnostic Session: SESSION-8A9F  | [Report Unclear] [Outdated Guide] [Complete] |
+-----------------------------------------------------------------------------------+
```

---

## 🔍 Key Component Breakdown

### 1. Top Header & Vehicle Context Bar
- **VIN Search Input**: Allows typing or scanning a vehicle's VIN or model number (e.g. `1G1RC6E4XGU123456`).
- **Vehicle Context Pill**: Automatically displays vehicle metadata loaded from the database (`2023 SUV Model X`, `AWD Hybrid`, Model Year).

### 2. Left Panel: AI Diagnostic Assistant (Chat)
- **Automatic Code Detection**: As soon as a VIN is loaded, the assistant identifies active Diagnostic Trouble Codes (e.g. **DTC P0300 - Random/Multiple Cylinder Misfire Detected**).
- **RAG-Grounded Answers**: Retrieves specific specs from the knowledge base (e.g. *Primary Resistance: 0.4 - 0.6 Ω*, *Secondary Resistance: 5.0 - 7.0 kΩ*).
- **Wiring Harness Bulletins**: Highlights specific known issues for the vehicle's VIN range (e.g. *Inspect connector C102 for corrosion*).
- **Chat Input Bar**: Technicians can ask follow-up questions in natural language (*"What is the torque spec for the coil hold-down bolt?"*).

### 3. Right Panel: Interactive Step-by-Step Instruction Viewer
- **Procedure Header**: Displays procedure title (*Ignition Coil Replacement - Bank 1*) and estimated repair duration (*Est. Time: 45 min*).
- **Step-by-Step Cards**:
  - **Step 1**: Safety precaution with highlighted alert box (*"⚠️ Wait 5 minutes after disconnect to allow capacitors to discharge"*).
  - **Step 2**: Visual diagram snippet (*Engine Bay 10mm bolt locations*).
  - **Step 3**: Active step highlights with target location (*Bank 1 Right Bank/Passenger Side*) and exact **Connector ID (`C102`)**.

### 4. Bottom Action Bar
- **Session Tracking**: Session ID (`SESSION-8A9F`) records the complete diagnostic log for audit compliance.
- **Feedback & Completion Buttons**:
  - `Report Unclear`: Flag confusing instructions for engineering review.
  - `Outdated Guide`: Report outdated torque specs or procedures.
  - `Complete Job`: Close out the diagnostic session and log completion to the Command Center metrics.
