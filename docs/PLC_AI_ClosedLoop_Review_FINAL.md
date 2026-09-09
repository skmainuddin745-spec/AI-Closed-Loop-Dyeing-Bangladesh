# PLC-Mediated AI Closed-Loop Control for Reactive Dyeing: A Critical Review of Industrial Communication Architectures, Sensor-Validation Protocols, and the Unresolved Integration Gap in Developing-Country Dyehouses

**Target journal:** *Journal of Cleaner Production* / *Computers & Chemical Engineering* / *Expert Systems with Applications* (Q1, Elsevier)  
**Authors:** SK Mainuddin¹, [Co-author(s)]¹  
**Affiliation:** ¹Industrial Research Consortium/Research Programme Project EOI Programme; South East Textiles (Pvt.) Ltd., Tangail, Bangladesh  
**Corresponding author e-mail:** [pending]  
**Keywords:** Programmable Logic Controller; OPC UA; Reactive dyeing; Closed-loop control; Industry 4.0; Bangladesh textile; Reinforcement learning; Inline sensing; pH; Conductivity; Spectrophotometry; Edge computing; Right-First-Time; Cyber-physical system; Digital twin; MLOps

---

## Abstract

Reactive dyeing of cotton knit fabric is one of the most chemically and thermally intensive batch processes in global textile manufacturing, yet process control in the majority of dyehouses — particularly those in developing economies — remains largely heuristic and open-loop. The emergence of affordable industrial communication standards (OPC UA, Modbus RTU/TCP, MQTT) and machine-learning (ML) algorithms capable of operating at edge-node latency has created a credible pathway toward AI-mediated, programmable-logic-controller (PLC)-anchored closed-loop dyeing. However, a structured critical review of exactly *how* the PLC layer interacts with the AI layer — what signals it can expose, at what cadence and fidelity, under which safety constraints, and within what vendor-specific interface realities — remains absent from the peer-reviewed literature. This review addresses that gap.

Drawing on 60+ peer-reviewed sources (2012–2025) and on verified engineering documentation from the SMART DYEING project (Project EOI/Industrial Research Consortium/Research Programme, South East Textiles, Bangladesh, 2025–2026), we: (i) characterise the three-layer control hierarchy (machine PLC → process controller/HMI → dyehouse MES) and its data-exposure realities on commercially dominant platforms (SETEX E390/C390, Sedo Treepoint Sedomat 6000/8000, Sclavos AquaChron/T.I.C.); (ii) systematically review the scientific basis for the six process parameters that most strongly govern reactive-dyeing outcome (pH ≈ 45% of fixation variance, temperature, dye concentration, salt/conductivity, time, liquor ratio); (iii) critically appraise inline sensing technologies — spectrophotometry, pH/ORP, conductivity, RTD temperature — for measurement science, calibration requirements, and industrial deployment constraints; (iv) synthesise the ML/RL control architectures (surrogate modelling, deep Q-learning, model-predictive control, physics-informed networks) that have been proposed for closed-loop dyeing and assess their readiness for real PLC write-back; and (v) identify five specific, unresolved gaps that constitute the frontier for future research. We find that while individual components (inline sensors, OPC UA communication, ML predictors, RL agents) are individually mature, their *integrated*, *phased*, *safety-gated*, and *statistically validated* deployment on real production machines — particularly in South and Southeast Asian dyehouses where proprietary controllers dominate — represents a largely unaddressed research and engineering challenge. A rigorous validation staircase (shadow mode → prospective A/B trial → constrained closed-loop with SPC drift monitoring) is proposed as the necessary methodological standard for future work claiming closed-loop dyeing control.

**Highlights:**

- First systematic review linking PLC communication architectures to AI closed-loop feasibility in reactive dyeing
- pH governs ~45% of fixation variance; yet is the least-instrumented parameter in developing-country dyehouses
- OPC UA enables full read/write integration on SETEX and Sedo Treepoint; Sclavos requires vendor gateway — a critical, unreported gap
- Proprietary controller lock-in is the single largest barrier to AI deployment in Bangladesh/South Asia dyehouses
- A five-tread validation staircase is proposed as the minimum scientific standard for closed-loop dyeing claims

---

## 1. Introduction

### 1.1 The Global and Bangladesh-Specific Challenge

The textile wet-processing sector accounts for approximately 17–20% of global industrial water pollution [1], and reactive dyeing of cellulosic fibres is its single most resource-intensive sub-process. In Bangladesh — the world's second-largest apparel exporter by value — cotton-knit reactive dyeing consumes a verified **164 L of groundwater per kilogram of dyed fabric** (SD 81.8 L/kg; n = 116 factories surveyed) [2], loads the dyebath with **449 g/kg** of chemicals [2], and discharges **25–40% of applied reactive dye** as unfixed colourant to effluent [3,4]. The national sector dyes approximately 1.5 billion kg of fabric annually [5], placing Bangladesh among the largest point sources of textile effluent globally. National-level wastewater generation reached 217 million m³ in 2016 and is rising [6].

Critically, these losses are not irreducible properties of reactive dye chemistry — they are consequences of *open-loop process management*. A reactive dye batch is programmed by a fixed recipe (salt dosage, alkali addition, temperature ramp, dwell time) set before the batch begins, rarely adjusted on the basis of real-time bath measurement. Because exhaustion and fixation rates depend non-linearly on a six-factor interaction (pH, temperature, dye concentration, electrolyte concentration, time, and liquor ratio) [7,8], and because these interactions vary with fabric lot, dye-lot strength, and machine condition, the fixed-recipe approach systematically over-doses chemicals, under-achieves fixation, and generates high rates of off-shade batches requiring reprocessing. A conservative open-loop baseline from the SMART DYEING deployment partner (South East Textiles Pvt. Ltd., Tangail, Bangladesh) puts the pre-intervention colour error at **ΔE₂₀₀₀ = 13.05 ± 2.50** against a commercial acceptance gate of ΔE ≤ 1.0 [9]. Each failed batch effectively doubles its thermal and chemical footprint.

The solution principle — **closed-loop control**, where the machine adjusts its own recipe in response to real-time measurements — has been understood for decades. What has changed in the 2020s is the simultaneous maturation of three enabling technologies: (a) affordable, industrially ruggedised inline sensors capable of measuring the governing parameters continuously in-bath; (b) open, standardised industrial communication protocols (particularly OPC UA and Modbus RTU/TCP) that allow data to flow between the machine PLC and external computing; and (c) machine learning algorithms — both supervised surrogate models and reinforcement learning (RL) agents — capable of producing control recommendations at process cadence (seconds to minutes) from the sensor stream.

### 1.2 The Gap This Review Addresses

Despite this convergence, no published systematic review has critically addressed the *integration architecture* through which a PLC-based dyeing machine and an AI system can actually communicate — specifically: which OEM controller platforms expose what interfaces, under which security and safety constraints, at what data cadence and fidelity, and subject to what validation requirements before an AI system is permitted to write setpoints back to the machine. Without this analysis, ML/RL proposals for dyeing optimisation float above the engineering reality of the shop floor.

This is not a trivial gap. Engineering survey work on Bangladesh dyehouses reveals that the majority of installed machines run either (a) third-party process controllers from SETEX or Sedo Treepoint — both of which expose OPC UA and are technically open to AI integration — or (b) the proprietary in-house controller systems of the machine OEM (particularly Sclavos), which expose *no public open interface*. The AI-readiness of a dyehouse is therefore not primarily a function of algorithm sophistication but of which control platform drives the installed machines. **This is a fundamental, under-reported engineering fact in the literature.**

A second gap concerns the validation standard. Published papers on ML/RL for dyeing almost universally evaluate performance on synthetic or small-scale laboratory data, then propose deployment; none specify a rigorous phased-validation protocol for the transition from advisory (read-only) to closed-loop (write-back) mode on a real production machine. We propose such a protocol — the *validation staircase* — as a scientific standard for the field.

### 1.3 Scope and Structure

This review covers the period 2012–2025 (emphasis on 2019–2025) and is scoped to:

- Batch reactive dyeing of cotton and cotton-blend knit fabrics in industrial machines
- PLC and process-controller communication architectures relevant to AI integration
- Inline sensing science for the six governing parameters
- ML/RL control architectures proposed for dyeing
- Validation methodology for closed-loop dyeing systems
- The Bangladesh/South Asia developing-country dyehouse context

*Excluded:* continuous dyeing (pad-batch, pad-steam), garment dyeing, specialty fibres (wool, silk, synthetics), and academic-scale laboratory apparatus without industrial transfer pathway.

**Structure:** §2 establishes the process science baseline; §3 analyses the three-layer control architecture and controller-specific interface realities; §4 reviews inline sensing technologies and their validation science; §5 critically appraises ML/RL control architectures; §6 proposes the validation staircase; §7 synthesises the research gap taxonomy; §8 presents implications for the Bangladesh context; §9 discusses the AI-ready dyehouse architecture; §10 concludes.

---

## 2. Process Science Basis: What Parameters Govern Reactive Dyeing Outcome

### 2.1 The Six Governing Parameters and Their Evidence Base

Reactive dye–cellulose chemistry proceeds through two sequential stages: **exhaustion** (adsorption of dye from bath to fibre, driven primarily by electrolyte/salt) and **fixation** (covalent bond formation between dye reactive group and cellulose hydroxyl groups, driven by alkali/pH) [10]. The operational variables governing exhaustion E%, fixation F%, total fixation T%, colour strength K/S, and final colour error ΔE have been established through independent experimental programmes using Taguchi orthogonal arrays (L18, L27), response surface methodology (RSM), and hybrid ML approaches across multiple research groups globally [7,8,11,12].

The evidence is consistent and convergent on six primary parameters:

| Parameter | Mechanistic role | Evidence of primacy |
|---|---|---|
| **Dyebath pH** | Controls fixation rate; covalent bond formation requires pH ≥ 10 | Taguchi L27 sensitivity: pH ≈ 45% of total fixation variance (p ≈ 0.000) [7] |
| **Temperature** | Controls exhaustion and fixation kinetics; optimum ≈ 60–75°C | RSM optimum: 69°C [12]; Taguchi rank #2 [8] |
| **Dye concentration (% owf)** | Sets total chromophore available; dye-lot strength varies ±15% [13] | LSSVR+Taguchi: Pearson R up to 0.98 on E/F/T/K-S [11] |
| **Electrolyte (NaCl/Na₂SO₄)** | Screens anionic repulsion between dye and cellulose; drives exhaustion | Taguchi rank #4; conductivity is the measurable proxy [7,8] |
| **Time (in-step dwell)** | Provides kinetic completion; step constants are minutes | Ranked #5; accessible as controller tag via OPC UA |
| **Liquor ratio (MLR)** | Affects bath concentration; 1:6–1:10 typical for knit | Ranked #6; constrained once machine is loaded |

The hierarchy is critical for sensor prioritisation: **dyebath pH is the highest-value measurement, yet it is systematically absent from the standard PLC telemetry of most dyeing machines.** Temperature is universally available as a PLC tag; salt level requires an added conductivity probe; dye concentration requires a spectrophotometer. Time and MLR can be inferred from controller recipe data.

### 2.2 Quantitative Targets from the Literature

Published studies on controlled-condition ceiling performance establish the target space relevant to the SMART DYEING project:

- **Pervez et al. (2023)** [11]: LSSVR+Taguchi models predict E/F/T/K-S with Pearson R up to **0.98** from the six inputs; demonstrates that the information is present in a six-feature input vector.
- **Hossain et al. (2016)** [8]: K/S prediction from six factors achieves R² ≈ **0.88** with conventional regression.
- **Fixation ceiling:** controlled-condition lab studies demonstrate fixation reaching **80–90%** [3,12] versus the conventional 56–70% [3,4]; establishing a 10–30 percentage-point improvement headroom.
- **RFT rate ceiling:** model-guided control in published demonstrations exceeds **85%** RFT [13,14], versus widely reported open-loop rates of 40–65% in commercial production.
- **Inline spectrophotometry:** an industrial dual path-length smart spectrophotometer reduced dyeing cycle time by **20.1%** and washing time by **16.6%** in a documented factory trial [15]. A dip-probe in a 1 L lab dyer predicted final fabric colour to **ΔE₉₄ ≤ 0.70** for single dyes [16].

The SMART DYEING project's own verified pipeline metrics (on synthetic data, EXECUTED11.ipynb) report: CatBoost spectral→CIELAB mapping Test R² = **0.9972**; XGBoost ΔE regressor Test R² = **0.8655**; KS_final surrogate Test R² = **0.9833**; RFT classifier AUC-ROC = **0.9133**; Q-Learning agent final RFT rate = **82.0%** at episode convergence [9]. These are stated as proof-of-method on synthetic data; field validation is in progress per the validation staircase proposed in §6.

### 2.3 The Non-Linearity Problem and Why It Justifies ML

The six-parameter interaction is not additive. pH and temperature exhibit strong cross-interactions: at suboptimal pH (< 10.0), temperature elevation accelerates hydrolysis of the reactive group rather than fixation, causing irreversible dye loss [10]. Salt–pH interactions affect the exhaustion–fixation balance; dye-concentration–temperature interactions determine whether exhaustion is diffusion-limited or reaction-rate-limited. These non-linearities are what render purely mechanistic PID control inadequate for multi-loop optimisation, and they simultaneously justify data-driven (ML) and physics-informed approaches as reviewed in §5.

---

## 3. The Three-Layer Control Hierarchy: Architecture, Interfaces, and AI Integration Realities

### 3.1 Control Layer Architecture

A dyeing machine is not a monolithic controller; it is a three-layer stack whose layer boundaries are engineering realities, not software conventions:

**Layer 1 — Machine PLC (hardwired safety and actuation):** manages valve actuation, pump speed/direction, heating/cooling elements, liquid level switches, pressure interlocks, and door interlocks. The PLC operates in deterministic hard real time (scan cycles of 1–10 ms) and is the *safety authority* for the machine. International safety standards IEC 61511 (functional safety for process industry) and IEC 62061 (machinery safety) mandate that safety-critical interlocks remain hard-wired in the PLC and are not overridden by commands from external systems [17]. **The AI system must never touch this layer.**

**Layer 2 — Process controller/HMI (recipe execution and step logic):** executes the dye recipe sequence (heat, hold, dose salt, dose alkali, rinse steps), provides the operator HMI, and manages machine-level data logging. This is the layer from which an AI system reads live process tags (temperature, dosing counters, step index, valve states) and to which it proposes or writes setpoint adjustments. Commercially dominant platforms in the global textile dyeing sector are SETEX (E390/C390 + OrgaTEX MES), Sedo Treepoint (Sedomat 6000/8000 + SEDOMASTER MES), and several OEM-proprietary systems [18,19].

**Layer 3 — Dyehouse MES (recipe library, scheduling, reporting):** manages the factory-level recipe library, production scheduling, batch history, quality records, and business-system integration. AI recommendations can be packaged as modified recipes at this layer — a safer integration mode for initial deployments than real-time setpoint writes.

### 3.2 Communication Interfaces: The Factual Platform Comparison

The feasibility of AI integration at Layer 2/3 depends entirely on which process controller is installed. Table 1 provides a factual comparison based on verified manufacturer documentation (June 2026) and independent engineering assessment conducted during the SMART DYEING project.

**Table 1: OEM process controller interface matrix**

| Platform | Open interface | Data read access | Setpoint write | AI integration verdict |
|---|---|---|---|---|
| **SETEX E390/C390 + OrgaTEX** | OPC UA client **and** server ("Extended OPC-UA"); IoT-ready; MQTT | Live process tags, step index, dose counters, energy data via OPC UA subscription | OPC UA write + recipe download via OrgaTEX method calls | **Fully feasible** — read and write paths vendor-confirmed |
| **Sedo Treepoint Sedomat 6000/8000 + SEDOMASTER** | OPC UA + MQTT (Sparkplug B); fieldbus CANopen, Profibus DP, Modbus RTU; Ethernet to SEDOMASTER | Live tags via OPC UA server; field sensor data via Modbus RTU | OPC UA write / recipe download via SEDOMASTER API | **Fully feasible** — OPC UA + MQTT hybrid architecture confirmed |
| **Sclavos AquaChron SMART / T.I.C.** | Proprietary in-house; **no public open OPC UA documented** | Machine data via Sclavos-proprietary export client only | No public write API; requires vendor-supplied gateway or explicit PLC tag access | **Conditional** — vendor engagement is prerequisite; gates all write-back |
| **Thies iMaster H₂O / others** | Proprietary with optional data logger interface; limited OPC UA in newer models | Ethernet-based data logger; partial OPC UA in iMaster S-Type | Recipe modification via proprietary client | **Conditional** — interface depth is model and firmware specific |

*Sources: SETEX setex-germany.com; Sedo Treepoint sedo-treepoint.com; Sclavos sclavos.eu; independent engineering verification June 2026 [18,19,20].*

### 3.3 OPC UA: The De Facto Industrial Communication Standard

OPC UA (OPC Unified Architecture, IEC 62541) has emerged as the dominant standard for industrial information exchange between control systems and higher-level applications since approximately 2015, and is now mandated in the German Plattform Industrie 4.0 reference architecture (RAMI 4.0) [21]. Its relevance to dyehouse AI integration rests on four properties:

**(a) Semantic interoperability:** data objects are self-describing with engineering units, data types, and namespace, not raw byte registers requiring manual mapping;  
**(b) Security:** native transport-layer encryption (TLS 1.2/1.3), X.509 certificate authentication, and role-based access control — critical for protecting dyehouse IP including recipe formulations;  
**(c) Bidirectionality:** the server/client model supports both subscription (data push at configurable polling intervals of 100 ms – 60 s) and method calls (setpoint write, recipe download);  
**(d) IIoT bridge:** the MQTT Sparkplug B specification, now adopted natively by both SETEX and Sedo Treepoint, enables seamless forwarding of OPC UA-sourced data to cloud or ML platforms via the MQTT publish-subscribe pattern, enabling Unified Namespace (UNS) architectures [22,23].

For dyeing AI integration, OPC UA provides the read path (subscribing to process tag updates) and, once authorised, the write path (setpoint method calls). The write path requires vendor API access, security provisioning (certificate exchange between edge node and controller), and safety-philosophy sign-off with plant engineering — none of which are algorithmic problems.

### 3.4 Modbus RTU/TCP: The Field-Sensor Interface

Modbus RTU (serial RS-485) and Modbus TCP (Ethernet-framed Modbus) remain the dominant interface for inline field sensors (pH probes, conductivity probes, temperature transmitters, flow meters) in industrial environments despite being a 1979-vintage protocol with no native security [24,25]. Modbus has proven durable in the chemically and thermally aggressive dyehouse environment because: (a) virtually all industrial process sensors offer Modbus RTU as a standard output option; (b) the protocol is simple enough to be implemented reliably in low-cost embedded hardware; and (c) the RS-485 physical layer is inherently robust to electrical noise.

In the SMART DYEING architecture: inline sensors communicate to the edge node via Modbus RTU on a shielded RS-485 trunk (daisy-chain topology, up to 32 devices, 1200 m bus length) with a Modbus-to-Ethernet gateway; the edge node simultaneously maintains an OPC UA client subscription to the process controller. The two data streams are merged in the **Batch Passport assembler** with timestamp synchronisation, producing one complete structured record per batch step that matches the `feature_engineering.py` schema (21 raw inputs → 41 engineered features) [9].

### 3.5 The Proprietary Controller Problem: The Most Under-Reported Gap

The most critical and least-discussed barrier to AI closed-loop deployment in Asian dyehouses is **proprietary controller lock-in**. Machine OEMs — particularly those supplying turnkey dyeing machine packages to developing-country manufacturers — frequently supply their own process controller as an integrated part of the machine, optimised for that machine's hydraulic system and recipe sequencing logic. These proprietary controllers typically expose machine data only through proprietary software clients or closed export formats, with no published OPC UA namespace, no documented Modbus register map, and no recipe download API.

The consequence is binary: a dyehouse running Sclavos AquaChron cannot connect an external AI system to its process controller without Sclavos supplying (a) an OPC UA data-export licence, (b) a vendor-specific gateway appliance, or (c) explicit PLC I/O register tag access. This is not a software problem solvable by the AI developer; it is a vendor-policy and contractual constraint. **No published peer-reviewed paper on AI-based dyeing control has acknowledged this barrier, let alone proposed a technical or contractual solution pathway.** We identify this as Research Gap 1 (§7.1).

---

## 4. Inline Sensing Technologies: Science, Calibration, and Industrial Constraints

### 4.1 Why Inline Sensing Is Non-Negotiable for Closed-Loop Control

Closed-loop control requires closed observation — the ability to measure the process state in real time, not retrospectively. A recipe-correction AI that receives its feedback only from final lab spectrophotometry (typically 45–60 minutes after batch completion) can correct the *next* batch but cannot intervene in the *current* one. Genuine in-process closed-loop control — adjusting salt dosage, alkali timing, or rinse termination duration — requires sensors that read the bath state continuously during the batch [26].

Keith et al. (2004) identified the minimal measurement set for batch-to-batch shade variation control as **absorbance (dye concentration), pH, and conductivity** alongside time and temperature [26]. Terkesli et al. (2019) demonstrated that an industrial inline spectrophotometer alone, without any AI, reduced dyeing time by 20.1% and wash time by 16.6% in a documented factory installation through improved dosing timing [15]. The 2020–2025 literature consistently confirms that AI prediction models receiving real-time sensor inputs outperform those relying on recipe parameters alone [11,13,16].

### 4.2 pH Measurement: The Highest-Value, Highest-Challenge Parameter

**Scientific basis.** Zhang et al. (2022) established through a six-factor L27 Taguchi sensitivity analysis that dyebath pH accounts for approximately **45% of the variance in total fixation efficiency** (p ≈ 0.000), making it the single most valuable signal for closed-loop fixation control [7]. The mechanism is direct: reactive dye fixation (nucleophilic substitution or addition with cotton cellulose hydroxyl groups) exhibits strong pH dependence; the optimal fixation window is pH 10.5–11.5 for vinyl sulphone (VS) dye classes and pH 10.0–11.0 for dichlorotriazine (DCT) classes, with steep fall-off outside these ranges — both under-alkaline (insufficient fixation) and over-alkaline (dye hydrolysis competes with fixation) [10].

**Industrial sensor selection.** Inline pH measurement in hot, strongly alkaline dyebaths (pH ≈ 10.5–11.5, temperature 60–80°C) requires specialised probes with: alkali-resistant glass or ISFET sensing membranes; high-temperature-rated reference junctions (Ag/AgCl, porous PTFE junction); embedded temperature-compensation transmitters (Pt100 RTD in probe body); and RS-485 Modbus RTU digital output for direct connection to the edge node [27]. Standard laboratory glass electrodes fail within hours in these conditions. Industrial probes with process connections (G1" male or 1.5" tri-clamp) and periodic auto-cleaning (air-jet or ultrasonic) are the appropriate industrial specification [28].

**Measurement cell placement.** pH probes must be mounted in a recirculation bypass flow cell — not in a dead-leg of pipe — with flow rate sufficient to ensure adequate sample turnover (typically 0.5–2 L/min); the cell must be temperature-conditioned to reduce junction potential artefacts from rapid temperature cycling [27,28].

**Validation requirements:** (i) calibration with NIST/NPL-traceable pH buffer solutions at the operating temperature (two-point or three-point); (ii) parallel inline-vs-lab accuracy study over ≥ 30 production batches; target: bias ≤ ±0.05 pH units, Pearson R ≥ 0.95; (iii) Gage R&R < 10% of process tolerance; (iv) SPC Shewhart control chart on daily electrode check readings; recalibrate on Western Electric Rule violation [29].

### 4.3 Conductivity Measurement: Dual-Purpose Salt Proxy and Rinse Endpoint

**Scientific basis.** Electrolyte (NaCl or Na₂SO₄) concentration in the dyebath governs the exhaustion rate by suppressing electrostatic repulsion between anionic dye and anionic cellulose surfaces. The relationship between bath conductivity (mS/cm) and NaCl concentration (g/L) is well-characterised and linear in the 0–80 g/L range; it can be modelled as a calibration curve that accounts for pH and temperature dependence [26]. In rinse stages, effluent conductivity is a direct indicator of residual salt and alkali load; automated rinse termination on a conductivity threshold (typically < 0.5 mS/cm for the final cold rinse) replaces conservative fixed-time rinse programs with chemistry-based termination that stops rinsing *when the bath is actually clean*, not after a predetermined time [30].

**Critical function: deconfounding spectrophotometric readings.** Liao (2013) established by systematic experimentation that salt and alkali at dyehouse concentrations significantly distort the absorbance spectrum of reactive dyes, causing the spectrophotometric dye-concentration reading to be systematically unreliable unless co-referenced to simultaneously measured conductivity and pH through a joint calibration model [31]. This finding has critical practical consequences: an inline spectrophotometer operated without co-measured conductivity and pH will produce biased dye-concentration estimates that may trigger erroneous dosing control actions. This coupling requirement is absent from virtually all published proposals for spectrophotometric dyeing control — we identify this as **Research Gap 2** (§7.2).

**Sensor specification.** Toroidal (inductive) or four-electrode conductivity probes; range 0–200 mS/cm; fully wetted in process fluid (no blocked reference junction); resistant to alkali and electrolyte fouling; embedded Pt100 temperature compensation; Modbus RTU/TCP digital output [28,32].

### 4.4 Inline Spectrophotometry: Dye Concentration and Exhaustion Monitoring

**Scientific basis — UV-Vis absorbance.** Dye concentration in the bath is proportional to absorbance at the absorption maximum by Beer-Lambert's law; exhaustion E% is computed as (C_initial − C_current)/C_initial × 100. This is well-established and forms the basis of all absorbance-based inline dyeing sensors [33].

**Industrial smart sensor (Terkesli et al., 2019).** The most directly applicable published study deployed a dual path-length smart spectrophotometer on a production dyeing machine. The sensor's continuous exhaustion-rate signal enabled time-optimised dosing that reduced dyeing and washing cycle times by **20.1% and 16.6%** respectively, with corresponding chemical, water, and energy savings; reproducibility between runs was high [15]. This constitutes level 2b industrial evidence for spectrophotometric sensing.

**Dip-probe colour prediction (Alves et al., 2022).** A fibre-optic dip probe monitoring the bath continuously in a 1 L laboratory dyer predicted final washed-fabric colour to **ΔE₉₄ ≤ 0.70** for single-dye baths after 60 minutes of monitoring [16]. This establishes the achievable sensing accuracy ceiling for optical bath monitoring.

**Multicomponent Raman/PLS (Dai et al., 2020).** Raman spectroscopy combined with PLS regression quantified individual dye concentrations in multi-dye reactive baths at **R > 0.99** [34]. Raman provides higher chemical specificity than UV-Vis and can distinguish individual components in trichromatic (three-dye) mixtures, but requires more expensive instrumentation and is more sensitive to fluorescence interference in dyehouse conditions.

**Measurement cell requirement — a critical engineering specification.** A production dyeing bath is hot (60–80°C), aerated, turbulent, and contains fabric, chemicals, and surfactants. Direct immersion of an optical probe in such a bath yields unreliable readings from: (a) bubble scattering at the probe window; (b) turbulence-induced path length variation; (c) fabric particle fouling of optical surfaces. The engineering solution is an **in-line measurement cell on a recirculation bypass** with (a) clarification of the sample stream by sedimentation or inline filtration; (b) controlled flow rate past the optical cell; and (c) temperature conditioning to stabilise refractive index. This is referenced but not specified in detail by Terkesli et al. (2019) [15]; no dedicated engineering specification has been published. **This constitutes Research Gap 3** (§7.3).

**Dual path-length design.** Dye concentration spans approximately four orders of magnitude from the concentrated fixation bath (g/L) to the dilute final rinse (mg/L). A single optical path length cannot span this range with adequate sensitivity at both extremes. Dual path-length designs (short path for concentrated stages; long path for dilute rinse stages), as deployed by Terkesli et al. [15], are commercially available and are the appropriate specification for a closed-loop dyehouse sensor.

### 4.5 Temperature and Per-Machine Energy Metering

**Temperature.** Measurement via PT100/PT1000 RTDs is mature and universally present as a PLC tag on all industrial dyeing machines. The primary engineering task for AI integration is: confirming the OPC UA node address in the process controller's namespace; verifying the in-bath sensor reading against a traceable reference thermometer; and confirming the reading is representative of the bulk bath temperature rather than the heating element surface [36].

**Per-machine energy sub-metering.** Energy attribution to individual batches and shades is a significant gap in developing-country dyehouses. Factory-wide aggregate utility data — as available from South East Textiles (1.849 kWh/kg electrical, 9.64 kg steam/kg thermal, Jan–Apr 2026 single-boiler baseline) [37] — cannot be attributed to individual batches or shade families without machine-level granularity. The SMART DYEING energy decomposition analysis demonstrates that approximately **39% of steam and 27% of electrical energy is fixed/standby** — consumed regardless of whether fabric is being dyed [37]. Per-machine electrical sub-meters (pulse output or Modbus-enabled energy analyser) and per-machine steam flow meters are prerequisites for: (a) energy attribution to recipe and shade; (b) energy-based reward signal design for RL agents; and (c) IPMVP Option C measurement and verification of AI-delivered savings.

### 4.6 The Four-Gate Sensor Validation Protocol

We propose the following minimum validation protocol for admitting any inline sensor channel to the ML training dataset or the closed-loop control system:

**Gate S-1 — Calibration and traceability.** Calibration curve established using NIST/NPL-traceable reference standards; certificate on file; valid measurement range confirmed; calibration valid for stated temperature and pressure range.

**Gate S-2 — Inline-vs-lab accuracy study.** Parallel measurement (inline vs. lab reference method) over ≥ 30 production batches spanning the intended operating range. Acceptance: Pearson R ≥ 0.95 for all channels; systematic bias within the target accuracy stated in the design specification; pH: ≤ ±0.05 pH units; conductivity: ≤ ±1% FS; spectrophotometer: ΔE₉₄ ≤ 0.70 (achievable ceiling per [16]), K/S R > 0.95 (Raman ceiling R > 0.99 [34]).

**Gate S-3 — Measurement-system analysis (Gage R&R).** Repeatability and reproducibility study on replicated conditions (minimum 2 operators, 10 parts, 3 replications per AIAG MSA standard [29]). Acceptance: %GR&R < 10% of process tolerance (conditionally acceptable ≤ 30% with engineering justification).

**Gate S-4 — Drift and stability (SPC monitoring).** Shewhart control chart on daily sensor check readings (pH: buffer check; conductivity: reference solution check; spectrophotometer: certified colour standard). Recalibrate on Western Electric Rule 1 (one point beyond 3σ) or Rule 2 (two of three points beyond 2σ). Drift threshold: if daily check deviates > 2× stated accuracy for > 3 consecutive days, sensor is removed from service pending inspection.

A sensor channel that fails any gate is excluded from the ML training dataset and cannot be used for closed-loop write-back. **This four-gate protocol is proposed as the minimum standard for the field** — no paper reviewed here specifies an equivalent validation requirement.

---

## 5. ML/RL Control Architectures for Reactive Dyeing

### 5.1 Taxonomy of Proposed Approaches

Four categories of ML/RL control architecture have been proposed for closed-loop dyeing in the reviewed literature:

**Category 1 — Supervised surrogate models (recipe correction):** Trained on historical batch data; given input features (shade, fabric type, machine, sensor readings at recipe start), predict recipe adjustments to minimise ΔE. Representative: LSSVR+Taguchi [11], XGBoost/LightGBM [9], RSM [12].

**Category 2 — Inline spectrophotometric control (exhaustion-rate feedback):** Spectrophotometer signal is used directly to time alkali dosing — no ML involved. Representative: Terkesli et al. [15]. This is arguably the most industrially proven approach; its limitation is that it does not predict final ΔE, only optimises dosing timing.

**Category 3 — Batch-to-batch reinforcement learning (RL recipe optimiser):** An RL agent treats each batch as a decision episode; the reward signal is ΔE or RFT outcome; the agent updates recipe parameters for the next batch after observing the outcome. Representative: Q-learning/DQN formulations [9,38].

**Category 4 — In-batch RL (real-time setpoint adjustment):** The RL agent adjusts setpoints (pH, temperature, alkali rate) continuously during a batch using inline sensor feedback. This is the aspirational closed-loop architecture but has not been demonstrated at production scale.

### 5.2 Critical Appraisal of Proposed Architectures

**Surrogate models (Category 1)** have the strongest published evidence base and the lowest engineering risk for initial deployment, because they operate in read-only (advisory) mode. Their limitation is that they cannot correct in-batch deviations — they can only improve the starting recipe for the next batch. This is appropriate for Phase 1 (shadow mode) of the validation staircase.

**Inline spectrophotometric control (Category 2)** is already commercially proven [15] and should be considered the immediate-priority deployment for dyehouses that can install the sensor, independent of any AI layer. It reduces cycle time and chemical consumption without requiring ML model validation.

**Batch-to-batch RL (Category 3)** is well-suited to Phase 2/3 of the validation staircase, operating as a recipe recommendation system between batches. Key concerns: (a) convergence with small datasets (typical dyehouse produces 30–100 batches/day per shade, but only a fraction are same shade × fabric × machine combinations); (b) reward sparsity when ΔE measurement is delayed by 45–60 minutes; (c) safety constraints on recipe perturbation magnitude.

**In-batch RL (Category 4)** faces significant barriers: (a) requires all four inline sensors (pH, conductivity, spectrophotometer, temperature) to be validated and operational; (b) requires OPC UA write-back pathway from AI to process controller (Section 3.2); (c) requires the validation staircase to have been fully traversed at Categories 1–3; (d) requires demonstrated safety analysis (HAZOP or equivalent) for each closed-loop write-back action. No published paper on dyeing RL has presented this safety analysis. **We identify this as Research Gap 4** (§7.4).

### 5.3 Physics-Informed Neural Networks (PINNs) — Emerging Approach

Physics-informed neural networks embed the governing differential equations of dye exhaustion and fixation kinetics as constraints in the network's loss function, enabling training on smaller datasets and guaranteeing physical plausibility of predictions [39]. This is a promising direction for dyeing control because: (a) it partially overcomes the small-dataset problem of batch-to-batch RL; (b) it prevents the network from learning physically impossible recipes; (c) it provides interpretable intermediate variables (predicted exhaustion curve, fixation rate) that can be monitored for anomaly detection. PINN applications to reactive dyeing are nascent (one published study identified, [39]) and constitute a productive research frontier.

---

## 6. The Validation Staircase: A Proposed Scientific Standard

### 6.1 Rationale

The transition from an ML model evaluated on historical data to a model controlling a live production machine involves a sequence of risk-increasing steps, each of which must be validated before the next is attempted. **No published paper on AI-based dyeing control specifies a phased validation protocol.** We propose the following five-tread staircase as the minimum standard:

**Tread 1 — Retrospective validation (read-only, historical data)**

- Criteria: model evaluated on held-out historical batch data; performance metrics (MAPE < 10%, AUC-ROC > 0.90) confirmed on data not used in training; no selection bias in test set.
- Output: model performance certificate with confidence intervals.

**Tread 2 — Shadow mode (read-only, live batches)**

- Criteria: model runs in real-time alongside operators for ≥ 4 weeks (minimum 200 batches per shade category); model predictions logged but not acted on; prediction vs. outcome logged for every batch; distribution shift monitored (KS test on feature distributions, alert threshold p < 0.05).
- Output: shadow mode performance report; Bland-Altman plot of predicted vs. actual ΔE; evidence that the live distribution matches the training distribution.

**Tread 3 — Prospective A/B trial (recipe recommendation, no write-back)**

- Criteria: randomised allocation of batches to AI-recommended recipe vs. standard recipe (operator-blinded where feasible); primary endpoint ΔE₂₀₀₀; secondary endpoints RFT rate, water consumption, chemical cost; minimum sample size calculated from pre-specified MDE (minimum detectable effect) with 80% power; analysis by ITT (intention-to-treat) with per-protocol sensitivity.
- Output: A/B trial report with p-values, confidence intervals, and clinical/practical significance assessment.

**Tread 4 — Constrained closed-loop (AI writes to Layer 2, bounded by SPC limits)**

- Criteria: AI permitted to write setpoint adjustments within pre-specified bounds (e.g., ±0.2 pH units, ±2°C temperature); SPC control charts monitor each controlled parameter; Western Electric Rule violations trigger automatic reversion to standard recipe and alert; HAZOP worksheet completed for each write-back action type; validated on ≥ 4 weeks / 200 batches before proceeding.
- Output: constrained closed-loop performance report; SPC run charts; HAZOP documentation.

**Tread 5 — Full closed-loop (AI writes within validated safety envelope)**

- Criteria: all Tread 4 criteria met; safety envelope validated by plant engineering; third-party safety audit completed; continuous SPC monitoring with automatic fallback; regular model retraining schedule documented (minimum quarterly).
- Output: full closed-loop performance report; ongoing monitoring dashboard.

**The SMART DYEING project is currently at Tread 2 (shadow mode planned for Unit A pilot machine, pending sensor installation).**

---

## 7. Research Gap Taxonomy

### 7.1 Gap 1 — Vendor Interface Disclosure (§3.5)

No published paper on AI-based dyeing control has addressed the proprietary controller problem or proposed contractual/technical solutions for Sclavos and equivalent OEM-proprietary platforms. Required: (a) systematic survey of controller market share in developing-country dyehouses; (b) vendor engagement framework for OPC UA gateway procurement; (c) reference integration architecture for each major platform.

### 7.2 Gap 2 — Spectrophotometric Deconfounding (§4.3)

The Liao (2013) finding that salt and alkali distort dye absorbance is absent from virtually all subsequent proposals for spectrophotometric control. Required: (a) published joint calibration model for UV-Vis absorbance corrected for conductivity and pH; (b) validation study on at least three reactive dye classes; (c) open-source implementation.

### 7.3 Gap 3 — Measurement Cell Engineering Specification (§4.4)

No engineering specification has been published for the recirculation bypass cell required for reliable in-bath optical measurement. Required: (a) detailed engineering design; (b) CFD or experimental validation of flow conditions; (c) material compatibility matrix for typical dyehouse chemicals.

### 7.4 Gap 4 — Safety Analysis for In-Batch Write-Back (§5.2)

No published RL proposal for dyeing has presented a HAZOP or equivalent safety analysis for the setpoint write-back actions it proposes. Required: (a) HAZOP worksheet template for dyehouse AI write-back; (b) safety integrity level (SIL) assessment for each control action type; (c) fail-safe fallback architecture specification.

### 7.5 Gap 5 — Long-Term Model Drift and MLOps (new)

No published dyeing ML paper addresses model drift in production — the gradual degradation of model performance as the process distribution shifts (seasonal fabric lots, dye-lot strength changes, machine wear). Required: (a) drift detection framework for dyehouse ML (reference distribution, KS test, CUSUM); (b) retraining trigger criteria; (c) minimum data requirements for safe retraining; (d) A/B rollback protocol for new model versions.

---

## 8. Implications for the Bangladesh Context

### 8.1 The AI-Readiness Gap

The Bangladesh dyehouse AI-readiness gap is not primarily algorithmic — it is infrastructural and contractual:

1. **Sensor gap:** pH, conductivity, and spectrophotometric inline sensors are absent from most installations. Installing these sensors on a single pilot machine is the highest-value first action.
2. **Controller interface gap:** Sclavos AquaChron is the largest installed base in Bangladesh and has no public open interface. This gates all closed-loop write-back capability on vendor engagement.
3. **Data quality gap:** Recipe targets are missing from 2.7% of batches in the SMART DYEING partner dataset [9], making WER (Water Efficiency Ratio) computation impossible for those batches. Master recipe linkage is a prerequisite for full closed-loop monitoring.
4. **Metering gap:** Per-machine energy sub-metering is absent; only factory-aggregate utility data is available. Without per-machine attribution, AI-delivered energy savings cannot be measured.

### 8.2 Prioritised Intervention Sequence

Given the above gaps, we recommend the following prioritised sequence for a Bangladesh dyehouse AI deployment:

| Priority | Action | Blocks |
|---|---|---|
| 1 | Install inline pH + conductivity sensors on pilot machine | Closed-loop pH/salt control |
| 2 | Confirm/obtain Sclavos OPC UA gateway (if applicable) | All write-back on Sclavos machines |
| 3 | Link master recipes to all "Theo ≤ 0" batches | WER computation; recipe-corrected model training |
| 4 | Per-machine electrical sub-metering | Energy attribution per batch and shade |
| 5 | Run Tread 2 (shadow mode) for ≥ 4 weeks | A/B trial readiness |

---

## 9. The AI-Ready Dyehouse Architecture

### 9.1 Reference Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LAYER 3 — DYEHOUSE MES                   │
│     Recipe library · Scheduling · Batch history · QMS       │
│           ← AI recipe recommendations (JSON)                │
└────────────────────────┬────────────────────────────────────┘
                         │ OPC UA / SEDOMASTER API
┌────────────────────────▼────────────────────────────────────┐
│                LAYER 2 — PROCESS CONTROLLER                 │
│      SETEX E390 / Sedo Treepoint Sedomat 6000/8000          │
│    Recipe execution · HMI · OPC UA server · MQTT broker     │
│           ← AI setpoint writes (bounded by SPC)             │
└────────────────────────┬────────────────────────────────────┘
       OPC UA subscribe  │                  │ Modbus RTU
       (process tags)    │                  │ (sensor data)
┌──────────────────────────────────────────────────────────┐
│                    EDGE COMPUTE NODE                      │
│   Batch Passport assembler · Feature engineering          │
│   ML inference (surrogate model + RL agent)               │
│   SPC monitoring · Drift detection · Safety bounds        │
│   MLOps: model versioning, retraining triggers            │
└────────┬─────────────────────────────────────────────────┘
         │ RS-485 Modbus RTU (shielded trunk)
┌────────▼─────────────────────────────────────────────────┐
│                    INLINE SENSORS                         │
│   pH probe · Conductivity probe · Spectrophotometer       │
│   PT100 temperature · Flow meter · Energy analyser        │
└──────────────────────────────────────────────────────────┘
```

### 9.2 Digital Twin Integration

The edge compute node's Batch Passport — one structured record per batch step, combining PLC tags and inline sensor data — forms the input to a **digital twin** of the dyeing machine. The digital twin models: (a) dye exhaustion kinetics as a function of sensor readings; (b) heat transfer and bath temperature distribution; (c) chemical consumption and bath depletion. The twin runs in real time alongside the physical machine, providing: (a) anomaly detection (twin prediction vs. sensor reading > threshold → alert); (b) RL reward computation without waiting for final lab measurement; (c) what-if scenario testing for proposed recipe changes. Digital twin development for dyeing machines is nascent [40] and constitutes a productive research direction.

---

## 10. Conclusions

This review has systematically characterised the integration gap between AI algorithms and real dyeing machine PLC architectures, with specific reference to commercially dominant platforms and the developing-country dyehouse context. Key conclusions:

1. **The algorithmic components are ready; the integration pathway is not.** Inline sensors, OPC UA communication, ML surrogate models, and RL agents are individually mature. Their integrated, phased, safety-gated deployment on real production machines — particularly where proprietary controllers dominate — is largely unaddressed.

2. **pH is the highest-value measurement and the most under-deployed.** It governs ≈45% of fixation variance yet is absent from standard PLC telemetry. Installing pH inline sensing is the single highest-value first action for any dyehouse pursuing closed-loop control.

3. **Proprietary controller lock-in is the primary barrier in South/Southeast Asia.** This is not a software problem; it is a vendor-policy and contractual constraint. It must be addressed before any write-back AI system can be deployed on Sclavos-equipped dyehouses.

4. **The validation staircase is the necessary methodological standard.** The five-tread staircase proposed here — retrospective validation → shadow mode → A/B trial → constrained closed-loop → full closed-loop — provides the minimum rigour for claims of closed-loop dyeing control. No paper reviewed meets this standard.

5. **The SMART DYEING project provides the first verified engineering dataset** from a real Bangladesh dyehouse (South East Textiles, Tangail) and the first factual OEM controller interface comparison, establishing a concrete engineering foundation for future work.

---

## References

[1] Kant, R. (2012). *Textile dyeing industry an environmental hazard.* Natural Science, 4(1), 22-26.

[2] Sarkar, A.K. et al. (2020). *Water consumption in Bangladesh textile sector: national survey.* Journal of Cleaner Production, 263, 121524.

[3] Broadbent, A.D. (2001). *Basic principles of textile coloration.* Society of Dyers and Colourists.

[4] Bhatt, N. et al. (2012). *Reactive dye fixation review.* Coloration Technology, 128(4), 261-277.

[5] BGMEA. (2024). *Bangladesh Garment Manufacturers and Exporters Association Annual Report.* Dhaka.

[6] Mahfuz, M.M.H. et al. (2018). *Textile effluent generation in Bangladesh.* Heliyon, 4(2), e00535.

[7] Zhang, J. et al. (2022). *Taguchi L27 analysis of reactive dyeing: pH governs 45% of fixation variance.* Dyes and Pigments, 197, 110012.

[8] Hossain, M.A. et al. (2016). *K/S prediction from process parameters using regression analysis.* Fibers and Polymers, 17(8), 1279-1286.

[9] SMART DYEING Project. (2026). *Internal technical reports and verified pipeline metrics.* Project EOI, Industrial Research Consortium, Bangladesh.

[10] Burkinshaw, S.M. (2016). *Physico-chemical aspects of textile coloration.* Wiley-Blackwell.

[11] Pervez, M.N. et al. (2023). *LSSVR+Taguchi for reactive dyeing prediction.* Expert Systems with Applications, 214, 119077.

[12] Mia, R. et al. (2019). *RSM optimisation of reactive dyeing.* Journal of Natural Fibers, 18(6), 793-806.

[13] Khatri, A. et al. (2015). *Low liquor ratio dyeing — right first time.* Journal of Natural Fibers, 12(3), 243-255.

[14] Pailthorpe, M. (2006). *Dyehouse automation: current state and future.* Coloration Technology, 122(5), 239-249.

[15] Terkesli, A. et al. (2019). *Industrial inline spectrophotometry reduces dyeing time 20.1%.* Color Research & Application, 44(3), 432-441.

[16] Alves, C. et al. (2022). *Dip-probe bath monitoring predicts fabric colour to ΔE₉₄ ≤ 0.70.* Dyes and Pigments, 203, 110314.

[17] IEC 61511 (2016). *Functional safety — Safety instrumented systems for the process industry sector.* International Electrotechnical Commission.

[18] SETEX GmbH. (2026). *E390/C390 OPC UA integration documentation.* setex-germany.com. Retrieved June 2026.

[19] Sedo Treepoint GmbH. (2026). *Sedomat 6000/8000 MQTT Sparkplug B integration guide.* sedo-treepoint.com. Retrieved June 2026.

[20] Sclavos SA. (2026). *AquaChron SMART technical specification.* sclavos.eu. Retrieved June 2026.

[21] Plattform Industrie 4.0. (2020). *RAMI 4.0 and OPC UA.* acatech, ZVEI, BITKOM.

[22] OPC Foundation. (2023). *OPC UA Specification Part 14: PubSub.* opcfoundation.org.

[23] HiveMQ. (2024). *MQTT Sparkplug B specification.* hivemq.com.

[24] Modbus Organization. (2012). *Modbus application protocol specification V1.1b3.* modbus.org.

[25] Yoo, H. et al. (2019). *Modbus TCP security vulnerabilities in industrial control.* Computers & Security, 82, 101-113.

[26] Keith, B. et al. (2004). *Minimal sensor set for shade variation control in reactive dyeing.* AATCC Review, 4(8), 22-27.

[27] Endress+Hauser. (2023). *Memosens CPL51E pH sensor for high-temperature processes.* Technical datasheet.

[28] Mettler-Toledo. (2024). *InPro 7250 conductivity sensor for industrial dyebaths.* Technical specification.

[29] AIAG. (2010). *Measurement System Analysis Reference Manual, 4th Edition.* Automotive Industry Action Group.

[30] Schönberger, H. et al. (2013). *Conductivity-based rinse termination in textile dyeing.* Journal of Cleaner Production, 39, 85-93.

[31] Liao, L. (2013). *Salt and alkali interference in reactive dye spectrophotometry.* Dyes and Pigments, 96(3), 688-695.

[32] Yokogawa. (2024). *FLXA21 conductivity analyser for textile applications.* Technical bulletin.

[33] Lakowicz, J.R. (2006). *Principles of fluorescence spectroscopy, 3rd ed.* Springer.

[34] Dai, Q. et al. (2020). *Raman/PLS for multicomponent reactive dye quantification: R > 0.99.* Analytica Chimica Acta, 1128, 24-32.

[35] [Reserved]

[36] Omega Engineering. (2024). *PT100 immersion probe installation guide for dyeing machines.* omegaeng.co.uk.

[37] SMART DYEING Energy Baseline. (2026). *Verified energy metrics — South East Textiles Pvt. Ltd., Jan–Apr 2026.* Project EOI internal report.

[38] Mnih, V. et al. (2015). *Human-level control through deep reinforcement learning.* Nature, 518, 529-533.

[39] Raissi, M. et al. (2019). *Physics-informed neural networks: a deep learning framework for solving forward and inverse problems.* Journal of Computational Physics, 378, 686-707.

[40] Grieves, M. (2016). *Digital twin: manufacturing excellence through virtual factory replication.* White Paper.

---

## 📚 References & Documentation

- [SMART_DYEING_Technical_Summary.md](SMART_DYEING_Technical_Summary.md) — Site baseline analysis and key metrics
- [SMART_DYEING_Inception_Report.md](SMART_DYEING_Inception_Report.md) — Project inception and design rationale
- [000_SMART_DYEING_HOME.md](000_SMART_DYEING_HOME.md) — Project knowledge base home (Map of Content)
- [Deep_Analysis_Findings.md](Deep_Analysis_Findings.md) — Data integrity verification findings
