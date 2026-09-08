# PLC-Mediated AI Closed-Loop Control for Reactive Dyeing: A Critical Review of Industrial Communication Architectures, Sensor-Validation Protocols, and the Unresolved Integration Gap in Developing-Country Dyehouses

**Target journal:** *Journal of Cleaner Production* / *Computers & Chemical Engineering* / *Expert Systems with Applications* (Q1, Elsevier)  
**Authors:** SK MainuddinÂ¹, [Co-author(s)]Â¹  
**Affiliation:** Â¹Industrial Research Consortium/Research Programme Project EOI Programme; South East Textiles (Pvt.) Ltd., Tangail, Bangladesh  
**Corresponding author e-mail:** [pending]  
**Keywords:** Programmable Logic Controller; OPC UA; Reactive dyeing; Closed-loop control; Industry 4.0; Bangladesh textile; Reinforcement learning; Inline sensing; pH; Conductivity; Spectrophotometry; Edge computing; Right-First-Time; Cyber-physical system; Digital twin; MLOps

---

## Abstract

Reactive dyeing of cotton knit fabric is one of the most chemically and thermally intensive batch processes in global textile manufacturing, yet process control in the majority of dyehousesâ€”particularly those in developing economiesâ€”remains largely heuristic and open-loop. The emergence of affordable industrial communication standards (OPC UA, Modbus RTU/TCP, MQTT) and machine-learning (ML) algorithms capable of operating at edge-node latency has created a credible pathway toward AI-mediated, programmable-logic-controller (PLC)-anchored closed-loop dyeing. However, a structured critical review of exactly *how* the PLC layer interacts with the AI layerâ€”what signals it can expose, at what cadence and fidelity, under which safety constraints, and within what vendor-specific interface realitiesâ€”remains absent from the peer-reviewed literature. This review addresses that gap.

Drawing on 60+ peer-reviewed sources (2012â€“2025) and on verified engineering documentation from the SMART DYEING project (Project EOI/Industrial Research Consortium/Research Programme, South East Textiles, Bangladesh, 2025â€“2026), we: (i) characterise the three-layer control hierarchy (machine PLC â†’ process controller/HMI â†’ dyehouse MES) and its data-exposure realities on commercially dominant platforms (SETEX E390/C390, Sedo Treepoint Sedomat 6000/8000, Sclavos AquaChron/T.I.C.); (ii) systematically review the scientific basis for the six process parameters that most strongly govern reactive-dyeing outcome (pH â‰ˆ45% of fixation variance, temperature, dye concentration, salt/conductivity, time, liquor ratio); (iii) critically appraise inline sensing technologiesâ€”spectrophotometry, pH/ORP, conductivity, RTD temperatureâ€”for measurement science, calibration requirements, and industrial deployment constraints; (iv) synthesise the ML/RL control architectures (surrogate modelling, deep Q-learning, model-predictive control, physics-informed networks) that have been proposed for closed-loop dyeing and assess their readiness for real PLC write-back; and (v) identify five specific, unresolved gaps that constitute the frontier for future research. We find that while individual components (inline sensors, OPC UA communication, ML predictors, RL agents) are individually mature, their *integrated*, *phased*, *safety-gated*, and *statistically validated* deployment on real production machinesâ€”particularly in South and Southeast Asian dyehouses where proprietary controllers dominateâ€”represents a largely unaddressed research and engineering challenge. A rigorous validation staircase (shadow mode â†’ prospective A/B trial â†’ constrained closed-loop with SPC drift monitoring) is proposed as the necessary methodological standard for future work claiming closed-loop dyeing control.

**Highlights:**
- First systematic review linking PLC communication architectures to AI closed-loop feasibility in reactive dyeing
- pH governs ~45% of fixation variance; yet is the least-instrumented parameter in developing-country dyehouses
- OPC UA enables full read/write integration on SETEX and Sedo Treepoint; Sclavos requires vendor gateway â€” a critical, unreported gap
- Proprietary controller lock-in is the single largest barrier to AI deployment in Bangladesh/South Asia dyehouses
- A five-tread validation staircase is proposed as the minimum scientific standard for closed-loop dyeing claims

---

## 1. Introduction

### 1.1 The Global and Bangladesh-Specific Challenge

The textile wet-processing sector accounts for approximately 17â€“20% of global industrial water pollution [1], and reactive dyeing of cellulosic fibres is its single most resource-intensive sub-process. In Bangladeshâ€”the world's second-largest apparel exporter by valueâ€”cotton-knit reactive dyeing consumes a verified **164 L of groundwater per kilogram of dyed fabric** (SD 81.8 L/kg; n = 116 factories surveyed) [2], loads the dyebath with **449 g/kg** of chemicals [2], and discharges **25â€“40% of applied reactive dye** as unfixed colourant to effluent [3,4]. The national sector dyes approximately 1.5 billion kg of fabric annually [5], placing Bangladesh among the largest point sources of textile effluent globally. National-level wastewater generation reached 217 million mÂ³ in 2016 and is rising [6].

Critically, these losses are not irreducible properties of reactive dye chemistryâ€”they are consequences of *open-loop process management*. A reactive dye batch is programmed by a fixed recipe (salt dosage, alkali addition, temperature ramp, dwell time) set before the batch begins, rarely adjusted on the basis of real-time bath measurement. Because exhaustion and fixation rates depend non-linearly on a six-factor interaction (pH, temperature, dye concentration, electrolyte concentration, time, and liquor ratio) [7,8], and because these interactions vary with fabric lot, dye-lot strength, and machine condition, the fixed-recipe approach systematically over-doses chemicals, under-achieves fixation, and generates high rates of off-shade batches requiring reprocessing. A conservative open-loop baseline from the SMART DYEING deployment partner (South East Textiles Pvt. Ltd., Tangail, Bangladesh) puts the pre-intervention colour error at **Î”Eâ‚‚â‚€â‚€â‚€ = 13.05 Â± 2.50** against a commercial acceptance gate of Î”E â‰¤ 1.0 [9]. Each failed batch effectively doubles its thermal and chemical footprint.

The solution principleâ€”**closed-loop control**, where the machine adjusts its own recipe in response to real-time measurementsâ€”has been understood for decades. What has changed in the 2020s is the simultaneous maturation of three enabling technologies: (a) affordable, industrially ruggedised inline sensors capable of measuring the governing parameters continuously in-bath; (b) open, standardised industrial communication protocols (particularly OPC UA and Modbus RTU/TCP) that allow data to flow between the machine PLC and external computing; and (c) machine learning algorithmsâ€”both supervised surrogate models and reinforcement learning (RL) agentsâ€”capable of producing control recommendations at process cadence (seconds to minutes) from the sensor stream.

### 1.2 The Gap This Review Addresses

Despite this convergence, no published systematic review has critically addressed the *integration architecture* through which a PLC-based dyeing machine and an AI system can actually communicateâ€”specifically: which OEM controller platforms expose what interfaces, under which security and safety constraints, at what data cadence and fidelity, and subject to what validation requirements before an AI system is permitted to write setpoints back to the machine. Without this analysis, ML/RL proposals for dyeing optimisation float above the engineering reality of the shop floor.

This is not a trivial gap. Engineering survey work on Bangladesh dyehouses reveals that the majority of installed machines run either (a) third-party process controllers from SETEX or Sedo Treepointâ€”both of which expose OPC UA and are technically open to AI integrationâ€”or (b) the proprietary in-house controller systems of the machine OEM (particularly Sclavos), which expose *no public open interface*. The AI-readiness of a dyehouse is therefore not primarily a function of algorithm sophistication but of which control platform drives the installed machines. **This is a fundamental, under-reported engineering fact in the literature.**

A second gap concerns the validation standard. Published papers on ML/RL for dyeing almost universally evaluate performance on synthetic or small-scale laboratory data, then propose deployment; none specify a rigorous phased-validation protocol for the transition from advisory (read-only) to closed-loop (write-back) mode on a real production machine. We propose such a protocolâ€”the *validation staircase*â€”as a scientific standard for the field.

### 1.3 Scope and Structure

This review covers the period 2012â€“2025 (emphasis on 2019â€“2025) and is scoped to:
- Batch reactive dyeing of cotton and cotton-blend knit fabrics in industrial machines
- PLC and process-controller communication architectures relevant to AI integration
- Inline sensing science for the six governing parameters
- ML/RL control architectures proposed for dyeing
- Validation methodology for closed-loop dyeing systems
- The Bangladesh/South Asia developing-country dyehouse context

*Excluded:* continuous dyeing (pad-batch, pad-steam), garment dyeing, specialty fibres (wool, silk, synthetics), and academic-scale laboratory apparatus without industrial transfer pathway.

**Structure:** Â§2 establishes the process science baseline; Â§3 analyses the three-layer control architecture and controller-specific interface realities; Â§4 reviews inline sensing technologies and their validation science; Â§5 critically appraises ML/RL control architectures; Â§6 proposes the validation staircase; Â§7 synthesises the research gap taxonomy; Â§8 presents implications for the Bangladesh context; Â§9 discusses the AI-ready dyehouse architecture; Â§10 concludes.

---

## 2. Process Science Basis: What Parameters Govern Reactive Dyeing Outcome

### 2.1 The Six Governing Parameters and Their Evidence Base

Reactive dyeâ€“cellulose chemistry proceeds through two sequential stages: **exhaustion** (adsorption of dye from bath to fibre, driven primarily by electrolyte/salt) and **fixation** (covalent bond formation between dye reactive group and cellulose hydroxyl groups, driven by alkali/pH) [10]. The operational variables governing exhaustion E%, fixation F%, total fixation T%, colour strength K/S, and final colour error Î”E have been established through independent experimental programmes using Taguchi orthogonal arrays (L18, L27), response surface methodology (RSM), and hybrid ML approaches across multiple research groups globally [7,8,11,12].

The evidence is consistent and convergent on six primary parameters:

| Parameter | Mechanistic role | Evidence of primacy |
|---|---|---|
| **Dyebath pH** | Controls fixation rate; covalent bond formation requires pH â‰¥ 10 | Taguchi L27 sensitivity: pH â‰ˆ 45% of total fixation variance (p â‰ˆ 0.000) [7] |
| **Temperature** | Controls exhaustion and fixation kinetics; optimum â‰ˆ 60â€“75Â°C | RSM optimum: 69Â°C [12]; Taguchi rank #2 [8] |
| **Dye concentration (% owf)** | Sets total chromophore available; dye-lot strength varies Â±15% [13] | LSSVR+Taguchi: Pearson R up to 0.98 on E/F/T/K-S [11] |
| **Electrolyte (NaCl/Naâ‚‚SOâ‚„)** | Screens anionic repulsion between dye and cellulose; drives exhaustion | Taguchi rank #4; conductivity is the measurable proxy [7,8] |
| **Time (in-step dwell)** | Provides kinetic completion; step constants are minutes | Ranked #5; accessible as controller tag via OPC UA |
| **Liquor ratio (MLR)** | Affects bath concentration; 1:6â€“1:10 typical for knit | Ranked #6; constrained once machine is loaded |

The hierarchy is critical for sensor prioritisation: **dyebath pH is the highest-value measurement, yet it is systematically absent from the standard PLC telemetry of most dyeing machines.** Temperature is universally available as a PLC tag; salt level requires an added conductivity probe; dye concentration requires a spectrophotometer. Time and MLR can be inferred from controller recipe data.

### 2.2 Quantitative Targets from the Literature

Published studies on controlled-condition ceiling performance establish the target space relevant to the SMART DYEING project:

- **Pervez et al. (2023)** [11]: LSSVR+Taguchi models predict E/F/T/K-S with Pearson R up to **0.98** from the six inputs; demonstrates that the information is present in a six-feature input vector.
- **Hossain et al. (2016)** [8]: K/S prediction from six factors achieves RÂ² â‰ˆ **0.88** with conventional regression.
- **Fixation ceiling:** controlled-condition lab studies demonstrate fixation reaching **80â€“90%** [3,12] versus the conventional 56â€“70% [3,4]; establishing a 10â€“30 percentage-point improvement headroom.
- **RFT rate ceiling:** model-guided control in published demonstrations exceeds **85%** RFT [13,14], versus widely reported open-loop rates of 40â€“65% in commercial production.
- **Inline spectrophotometry:** an industrial dual path-length smart spectrophotometer reduced dyeing cycle time by **20.1%** and washing time by **16.6%** in a documented factory trial [15]. A dip-probe in a 1 L lab dyer predicted final fabric colour to **Î”Eâ‚‰â‚„ â‰¤ 0.70** for single dyes [16].

The SMART DYEING project's own verified pipeline metrics (on synthetic data, EXECUTED11.ipynb) report: CatBoost spectralâ†’CIELAB mapping Test RÂ² = **0.9972**; XGBoost Î”E regressor Test RÂ² = **0.8655**; KS_final surrogate Test RÂ² = **0.9833**; RFT classifier AUC-ROC = **0.9133**; Q-Learning agent final RFT rate = **82.0%** at episode convergence [9]. These are stated as proof-of-method on synthetic data; field validation is in progress per the validation staircase proposed in Â§6.

### 2.3 The Non-Linearity Problem and Why It Justifies ML

The six-parameter interaction is not additive. pH and temperature exhibit strong cross-interactions: at suboptimal pH (< 10.0), temperature elevation accelerates hydrolysis of the reactive group rather than fixation, causing irreversible dye loss [10]. Saltâ€“pH interactions affect the exhaustionâ€“fixation balance; dye-concentrationâ€“temperature interactions determine whether exhaustion is diffusion-limited or reaction-rate-limited. These non-linearities are what render purely mechanistic PID control inadequate for multi-loop optimisation, and they simultaneously justify data-driven (ML) and physics-informed approaches as reviewed in Â§5.

---

## 3. The Three-Layer Control Hierarchy: Architecture, Interfaces, and AI Integration Realities

### 3.1 Control Layer Architecture

A dyeing machine is not a monolithic controller; it is a three-layer stack whose layer boundaries are engineering realities, not software conventions:

**Layer 1 â€” Machine PLC (hardwired safety and actuation):** manages valve actuation, pump speed/direction, heating/cooling elements, liquid level switches, pressure interlocks, and door interlocks. The PLC operates in deterministic hard real time (scan cycles of 1â€“10 ms) and is the *safety authority* for the machine. International safety standards IEC 61511 (functional safety for process industry) and IEC 62061 (machinery safety) mandate that safety-critical interlocks remain hard-wired in the PLC and are not overridden by commands from external systems [17]. **The AI system must never touch this layer.**

**Layer 2 â€” Process controller/HMI (recipe execution and step logic):** executes the dye recipe sequence (heat, hold, dose salt, dose alkali, rinse steps), provides the operator HMI, and manages machine-level data logging. This is the layer from which an AI system reads live process tags (temperature, dosing counters, step index, valve states) and to which it proposes or writes setpoint adjustments. Commercially dominant platforms in the global textile dyeing sector are SETEX (E390/C390 + OrgaTEX MES), Sedo Treepoint (Sedomat 6000/8000 + SEDOMASTER MES), and several OEM-proprietary systems [18,19].

**Layer 3 â€” Dyehouse MES (recipe library, scheduling, reporting):** manages the factory-level recipe library, production scheduling, batch history, quality records, and business-system integration. AI recommendations can be packaged as modified recipes at this layer â€” a safer integration mode for initial deployments than real-time setpoint writes.

### 3.2 Communication Interfaces: The Factual Platform Comparison

The feasibility of AI integration at Layer 2/3 depends entirely on which process controller is installed. Table 1 provides a factual comparison based on verified manufacturer documentation (June 2026) and independent engineering assessment conducted during the SMART DYEING project.

**Table 1: OEM process controller interface matrix**

| Platform | Open interface | Data read access | Setpoint write | AI integration verdict |
|---|---|---|---|---|
| **SETEX E390/C390 + OrgaTEX** | OPC UA client **and** server ("Extended OPC-UA"); IoT-ready; MQTT | Live process tags, step index, dose counters, energy data via OPC UA subscription | OPC UA write + recipe download via OrgaTEX method calls | **Fully feasible** â€” read and write paths vendor-confirmed |
| **Sedo Treepoint Sedomat 6000/8000 + SEDOMASTER** | OPC UA + MQTT (Sparkplug B); fieldbus CANopen, Profibus DP, Modbus RTU; Ethernet to SEDOMASTER | Live tags via OPC UA server; field sensor data via Modbus RTU | OPC UA write / recipe download via SEDOMASTER API | **Fully feasible** â€” OPC UA + MQTT hybrid architecture confirmed |
| **Sclavos AquaChron SMART / T.I.C.** | Proprietary in-house; **no public open OPC UA documented** | Machine data via Sclavos-proprietary export client only | No public write API; requires vendor-supplied gateway or explicit PLC tag access | **Conditional** â€” vendor engagement is prerequisite; gates all write-back |
| **Thies iMaster Hâ‚‚O / others** | Proprietary with optional data logger interface; limited OPC UA in newer models | Ethernet-based data logger; partial OPC UA in iMaster S-Type | Recipe modification via proprietary client | **Conditional** â€” interface depth is model and firmware specific |

*Sources: SETEX setex-germany.com; Sedo Treepoint sedo-treepoint.com; Sclavos sclavos.eu; independent engineering verification June 2026 [18,19,20].*

### 3.3 OPC UA: The De Facto Industrial Communication Standard

OPC UA (OPC Unified Architecture, IEC 62541) has emerged as the dominant standard for industrial information exchange between control systems and higher-level applications since approximately 2015, and is now mandated in the German Plattform Industrie 4.0 reference architecture (RAMI 4.0) [21]. Its relevance to dyehouse AI integration rests on four properties:

**(a) Semantic interoperability:** data objects are self-describing with engineering units, data types, and namespace, not raw byte registers requiring manual mapping;
**(b) Security:** native transport-layer encryption (TLS 1.2/1.3), X.509 certificate authentication, and role-based access control â€” critical for protecting dyehouse IP including recipe formulations;
**(c) Bidirectionality:** the server/client model supports both subscription (data push at configurable polling intervals of 100 ms â€“ 60 s) and method calls (setpoint write, recipe download);
**(d) IIoT bridge:** the MQTT Sparkplug B specification, now adopted natively by both SETEX and Sedo Treepoint, enables seamless forwarding of OPC UA-sourced data to cloud or ML platforms via the MQTT publish-subscribe pattern, enabling Unified Namespace (UNS) architectures [22,23].

For dyeing AI integration, OPC UA provides the read path (subscribing to process tag updates) and, once authorised, the write path (setpoint method calls). The write path requires vendor API access, security provisioning (certificate exchange between edge node and controller), and safety-philosophy sign-off with plant engineering â€” none of which are algorithmic problems.

### 3.4 Modbus RTU/TCP: The Field-Sensor Interface

Modbus RTU (serial RS-485) and Modbus TCP (Ethernet-framed Modbus) remain the dominant interface for inline field sensors (pH probes, conductivity probes, temperature transmitters, flow meters) in industrial environments despite being a 1979-vintage protocol with no native security [24,25]. Modbus has proven durable in the chemically and thermally aggressive dyehouse environment because: (a) virtually all industrial process sensors offer Modbus RTU as a standard output option; (b) the protocol is simple enough to be implemented reliably in low-cost embedded hardware; and (c) the RS-485 physical layer is inherently robust to electrical noise.

In the SMART DYEING architecture: inline sensors communicate to the edge node via Modbus RTU on a shielded RS-485 trunk (daisy-chain topology, up to 32 devices, 1200 m bus length) with a Modbus-to-Ethernet gateway; the edge node simultaneously maintains an OPC UA client subscription to the process controller. The two data streams are merged in the **Batch Passport assembler** with timestamp synchronisation, producing one complete structured record per batch step that matches the `feature_engineering.py` schema (21 raw inputs â†’ 41 engineered features) [9].

### 3.5 The Proprietary Controller Problem: The Most Under-Reported Gap

The most critical and least-discussed barrier to AI closed-loop deployment in Asian dyehouses is **proprietary controller lock-in**. Machine OEMs â€” particularly those supplying turnkey dyeing machine packages to developing-country manufacturers â€” frequently supply their own process controller as an integrated part of the machine, optimised for that machine's hydraulic system and recipe sequencing logic. These proprietary controllers typically expose machine data only through proprietary software clients or closed export formats, with no published OPC UA namespace, no documented Modbus register map, and no recipe download API.

The consequence is binary: a dyehouse running Sclavos AquaChron cannot connect an external AI system to its process controller without Sclavos supplying (a) an OPC UA data-export licence, (b) a vendor-specific gateway appliance, or (c) explicit PLC I/O register tag access. This is not a software problem solvable by the AI developer; it is a vendor-policy and contractual constraint. **No published peer-reviewed paper on AI-based dyeing control has acknowledged this barrier, let alone proposed a technical or contractual solution pathway.** We identify this as Research Gap 1 (Â§7.1).

---

## 4. Inline Sensing Technologies: Science, Calibration, and Industrial Constraints

### 4.1 Why Inline Sensing Is Non-Negotiable for Closed-Loop Control

Closed-loop control requires closed observation â€” the ability to measure the process state in real time, not retrospectively. A recipe-correction AI that receives its feedback only from final lab spectrophotometry (typically 45â€“60 minutes after batch completion) can correct the *next* batch but cannot intervene in the *current* one. Genuine in-process closed-loop control â€” adjusting salt dosage, alkali timing, or rinse termination duration â€” requires sensors that read the bath state continuously during the batch [26].

Keith et al. (2004) identified the minimal measurement set for batch-to-batch shade variation control as **absorbance (dye concentration), pH, and conductivity** alongside time and temperature [26]. Terkesli et al. (2019) demonstrated that an industrial inline spectrophotometer alone, without any AI, reduced dyeing time by 20.1% and wash time by 16.6% in a documented factory installation through improved dosing timing [15]. The 2020â€“2025 literature consistently confirms that AI prediction models receiving real-time sensor inputs outperform those relying on recipe parameters alone [11,13,16].

### 4.2 pH Measurement: The Highest-Value, Highest-Challenge Parameter

**Scientific basis.** Zhang et al. (2022) established through a six-factor L27 Taguchi sensitivity analysis that dyebath pH accounts for approximately **45% of the variance in total fixation efficiency** (p â‰ˆ 0.000), making it the single most valuable signal for closed-loop fixation control [7]. The mechanism is direct: reactive dye fixation (nucleophilic substitution or addition with cotton cellulose hydroxyl groups) exhibits strong pH dependence; the optimal fixation window is pH 10.5â€“11.5 for vinyl sulphone (VS) dye classes and pH 10.0â€“11.0 for dichlorotriazine (DCT) classes, with steep fall-off outside these ranges â€” both under-alkaline (insufficient fixation) and over-alkaline (dye hydrolysis competes with fixation) [10].

**Industrial sensor selection.** Inline pH measurement in hot, strongly alkaline dyebaths (pH â‰ˆ 10.5â€“11.5, temperature 60â€“80Â°C) requires specialised probes with: alkali-resistant glass or ISFET sensing membranes; high-temperature-rated reference junctions (Ag/AgCl, porous PTFE junction); embedded temperature-compensation transmitters (Pt100 RTD in probe body); and RS-485 Modbus RTU digital output for direct connection to the edge node [27]. Standard laboratory glass electrodes fail within hours in these conditions. Industrial probes with process connections (G1" male or 1.5" tri-clamp) and periodic auto-cleaning (air-jet or ultrasonic) are the appropriate industrial specification [28].

**Measurement cell placement.** pH probes must be mounted in a recirculation bypass flow cell â€” not in a dead-leg of pipe â€” with flow rate sufficient to ensure adequate sample turnover (typically 0.5â€“2 L/min); the cell must be temperature-conditioned to reduce junction potential artefacts from rapid temperature cycling [27,28].

**Validation requirements:** (i) calibration with NIST/NPL-traceable pH buffer solutions at the operating temperature (two-point or three-point); (ii) parallel inline-vs-lab accuracy study over â‰¥ 30 production batches; target: bias â‰¤ Â±0.05 pH units, Pearson R â‰¥ 0.95; (iii) Gage R&R < 10% of process tolerance; (iv) SPC Shewhart control chart on daily electrode check readings; recalibrate on Western Electric Rule violation [29].

### 4.3 Conductivity Measurement: Dual-Purpose Salt Proxy and Rinse Endpoint

**Scientific basis.** Electrolyte (NaCl or Naâ‚‚SOâ‚„) concentration in the dyebath governs the exhaustion rate by suppressing electrostatic repulsion between anionic dye and anionic cellulose surfaces. The relationship between bath conductivity (mS/cm) and NaCl concentration (g/L) is well-characterised and linear in the 0â€“80 g/L range; it can be modelled as a calibration curve that accounts for pH and temperature dependence [26]. In rinse stages, effluent conductivity is a direct indicator of residual salt and alkali load; automated rinse termination on a conductivity threshold (typically < 0.5 mS/cm for the final cold rinse) replaces conservative fixed-time rinse programs with chemistry-based termination that stops rinsing *when the bath is actually clean*, not after a predetermined time [30].

**Critical function: deconfounding spectrophotometric readings.** Liao (2013) established by systematic experimentation that salt and alkali at dyehouse concentrations significantly distort the absorbance spectrum of reactive dyes, causing the spectrophotometric dye-concentration reading to be systematically unreliable unless co-referenced to simultaneously measured conductivity and pH through a joint calibration model [31]. This finding has critical practical consequences: an inline spectrophotometer operated without co-measured conductivity and pH will produce biased dye-concentration estimates that may trigger erroneous dosing control actions. This coupling requirement is absent from virtually all published proposals for spectrophotometric dyeing control â€” we identify this as **Research Gap 2** (Â§7.2).

**Sensor specification.** Toroidal (inductive) or four-electrode conductivity probes; range 0â€“200 mS/cm; fully wetted in process fluid (no blocked reference junction); resistant to alkali and electrolyte fouling; embedded Pt100 temperature compensation; Modbus RTU/TCP digital output [28,32].

### 4.4 Inline Spectrophotometry: Dye Concentration and Exhaustion Monitoring

**Scientific basis â€” UV-Vis absorbance.** Dye concentration in the bath is proportional to absorbance at the absorption maximum by Beer-Lambert's law; exhaustion E% is computed as (C_initial â€“ C_current)/C_initial Ã— 100. This is well-established and forms the basis of all absorbance-based inline dyeing sensors [33].

**Industrial smart sensor (Terkesli et al., 2019).** The most directly applicable published study deployed a dual path-length smart spectrophotometer on a production dyeing machine. The sensor's continuous exhaustion-rate signal enabled time-optimised dosing that reduced dyeing and washing cycle times by **20.1% and 16.6%** respectively, with corresponding chemical, water, and energy savings; reproducibility between runs was high [15]. This constitutes level 2b industrial evidence for spectrophotometric sensing.

**Dip-probe colour prediction (Alves et al., 2022).** A fibre-optic dip probe monitoring the bath continuously in a 1 L laboratory dyer predicted final washed-fabric colour to **Î”Eâ‚‰â‚„ â‰¤ 0.70** for single-dye baths after 60 minutes of monitoring [16]. This establishes the achievable sensing accuracy ceiling for optical bath monitoring.

**Multicomponent Raman/PLS (Dai et al., 2020).** Raman spectroscopy combined with PLS regression quantified individual dye concentrations in multi-dye reactive baths at **R > 0.99** [34]. Raman provides higher chemical specificity than UV-Vis and can distinguish individual components in trichromatic (three-dye) mixtures, but requires more expensive instrumentation and is more sensitive to fluorescence interference in dyehouse conditions.

**Measurement cell requirement â€” a critical engineering specification.** A production dyeing bath is hot (60â€“80Â°C), aerated, turbulent, and contains fabric, chemicals, and surfactants. Direct immersion of an optical probe in such a bath yields unreliable readings from: (a) bubble scattering at the probe window; (b) turbulence-induced path length variation; (c) fabric particle fouling of optical surfaces. The engineering solution is an **in-line measurement cell on a recirculation bypass** with (a) clarification of the sample stream by sedimentation or inline filtration; (b) controlled flow rate past the optical cell; and (c) temperature conditioning to stabilise refractive index. This is referenced but not specified in detail by Terkesli et al. (2019) [15]; no dedicated engineering specification has been published. **This constitutes Research Gap 3** (Â§7.3).

**Dual path-length design.** Dye concentration spans approximately four orders of magnitude from the concentrated fixation bath (g/L) to the dilute final rinse (mg/L). A single optical path length cannot span this range with adequate sensitivity at both extremes. Dual path-length designs (short path for concentrated stages; long path for dilute rinse stages), as deployed by Terkesli et al. [15], are commercially available and are the appropriate specification for a closed-loop dyehouse sensor.

### 4.5 Temperature and Per-Machine Energy Metering

**Temperature.** Measurement via PT100/PT1000 RTDs is mature and universally present as a PLC tag on all industrial dyeing machines. The primary engineering task for AI integration is: confirming the OPC UA node address in the process controller's namespace; verifying the in-bath sensor reading against a traceable reference thermometer; and confirming the reading is representative of the bulk bath temperature rather than the heating element surface [36].

**Per-machine energy sub-metering.** Energy attribution to individual batches and shades is a significant gap in developing-country dyehouses. Factory-wide aggregate utility data â€” as available from South East Textiles (1.849 kWh/kg electrical, 9.64 kg steam/kg thermal, Janâ€“Apr 2026 single-boiler baseline) [37] â€” cannot be attributed to individual batches or shade families without machine-level granularity. The SMART DYEING energy decomposition analysis demonstrates that approximately **39% of steam and 27% of electrical energy is fixed/standby** â€” consumed regardless of whether fabric is being dyed [37]. Per-machine electrical sub-meters (pulse output or Modbus-enabled energy analyser) and per-machine steam flow meters are prerequisites for: (a) energy attribution to recipe and shade; (b) energy-based reward signal design for RL agents; and (c) IPMVP Option C measurement and verification of AI-delivered savings.

### 4.6 The Four-Gate Sensor Validation Protocol

We propose the following minimum validation protocol for admitting any inline sensor channel to the ML training dataset or the closed-loop control system:

**Gate S-1 â€” Calibration and traceability.** Calibration curve established using NIST/NPL-traceable reference standards; certificate on file; valid measurement range confirmed; calibration valid for stated temperature and pressure range.

**Gate S-2 â€” Inline-vs-lab accuracy study.** Parallel measurement (inline vs. lab reference method) over â‰¥ 30 production batches spanning the intended operating range. Acceptance: Pearson R â‰¥ 0.95 for all channels; systematic bias within the target accuracy stated in the design specification; pH: â‰¤ Â±0.05 pH units; conductivity: â‰¤ Â±1% FS; spectrophotometer: Î”Eâ‚‰â‚„ â‰¤ 0.70 (achievable ceiling per [16]), K/S R > 0.95 (Raman ceiling R > 0.99 [34]).

**Gate S-3 â€” Measurement-system analysis (Gage R&R).** Repeatability and reproducibility study on replicated conditions (minimum 2 operators, 10 parts, 3 replications per AIAG MSA standard [29]). Acceptance: %GR&R < 10% of process tolerance (conditionally acceptable â‰¤ 30% with engineering justification).

**Gate S-4 â€” Drift and stability (SPC monitoring).** Shewhart control chart on daily sensor check readings (pH: buffer check; conductivity: reference solution check; spectrophotometer: certified colour standard). Recalibrate on any Western Electric Rule violation. Optical channel drift additionally monitored via the conductivity/pH model residual per Liao [31].

Only channels satisfying S-1 through S-4 are admitted to model training (Tread 2) or closed-loop actuation (Tread 4) per the validation staircase in Â§6.

---

*[Continues in Part 2: Sections 5â€“10, References, and Appendices]*

---
*[Continuation â€” Sections 5â€“10, References, and Appendices]*

---

## 5. Machine Learning and Reinforcement Learning Control Architectures: Critical Appraisal

### 5.1 Surrogate Modelling (Predictive Engine 1): Review and Critique

The most extensively developed AI approach for dyeing optimisation is **supervised surrogate modelling**: training a regression (or classification) model on historical batch data, with inputs comprising the six governing parameters plus recipe variables, and outputs comprising quality metrics (K/S, Î”Eâ‚‚â‚€â‚€â‚€, E%, F%, RFT pass/fail). The trained model serves as a fast, differentiable proxy for the physical process.

**Historical foundations.** Early applications of artificial neural networks (ANNs) to dyeing colour prediction date to the 1990sâ€“2000s. Senthilkumar & Selvakumar (2012) demonstrated ANN-based colour prediction for reactive dyes on cotton with Pearson R > 0.98, establishing the feasibility of the approach [38]. Wu et al. (2003) demonstrated a genetic algorithm with grey nonlinear programming for dyeing recipe optimisation, achieving structured reduction in chemical use [39]. These works established the conceptual foundation but were limited to small datasets and offline use.

**Contemporary gradient-boosting approaches.** The 2020â€“2025 period has seen a shift toward gradient-boosted tree ensembles (XGBoost, CatBoost, LightGBM) for dyeing prediction, driven by their strong performance on tabular data, interpretability through SHAP (Shapley Additive Explanations) feature importance, and efficient inference. Representative results:

- **Pervez et al. (2023)** [11]: LSSVR (Least Squares Support Vector Regression) with Taguchi-designed L27 experimental data predicted exhaustion E%, fixation F%, total fixation T%, and colour strength K/S from six process inputs with Pearson R up to **0.98**. Dataset: 27 systematically designed lab batches; deployment: offline recipe recommendation.
- **Hossain et al. (2016)** [8]: Multiple regression and gradient boosting on K/S from six Taguchi factors, RÂ² â‰ˆ **0.88** on a 18-run L18 dataset.
- **Chen et al. (2024)** [40]: Multi-output modelling for CIELAB prediction in sustainable textile dyeing, demonstrating simultaneous prediction of L*, a*, b* with competitive accuracy. DOI: 10.1007/s43684-024-00076-8.
- **Zhang et al. (2021)** [41]: Hyperspectral imaging + improved recurrent neural network for dyeing recipe prediction (Color. Technol. 137(2):166â€“180).
- **Li et al. (2022)** [42]: FWSVR (fuzzy weighted SVR) + PSO for recipe prediction from bath measurements (Color. Technol. 138(5):495â€“508).
- **SMART DYEING (2026)** [9]: CatBoost spectralâ†’CIELAB mapping Test RÂ² = **0.9972** (spectral input L*_wet, a*_wet, b*_wet â†’ L*_dry, a*_dry, b*_dry); XGBoost Î”E regressor Test RÂ² = **0.8655** (marginal: overfit gap 0.0826 > 0.05 target); KS_final LSSVR surrogate Test RÂ² = **0.9833** (overfit gap 0.0167); RFT XGBoost classifier AUC-ROC = **0.9133**. All metrics on synthetic physics-generated data.

**SHAP interpretation: what the ML models reveal.** The SHAP analysis from the SMART DYEING pipeline identifies `dye_dosage_pct_owf` and `water_pickup_pct` as the dominant features for Î”E variance [9]; CatBoost SHAP identifies `b*_wet` (0.691) > `a*_wet` (0.168) > `L*_wet` (0.050) for the wetâ†’dry colour conversion module [9]. These feature-importance findings are internally consistent with process chemistry: the b* axis captures the yellowâ€“blue dimension most sensitive to reactive fixation completion; dye dosage is the primary chemical lever on colour depth.

**Critical limitation common to all published surrogate models.** The overwhelming majority of published surrogate models â€” including the SMART DYEING pipeline at the time of writing â€” are trained on **synthetic or small-scale laboratory data**, not on real production batches. Physics-based synthetic data generators encode only the explicitly modelled chemical relationships; they cannot capture: (a) lot-to-lot dye-strength variation (Â±15% is typical in commercial dyestuff supply); (b) fabric structural variation (knit construction, GSM, finishing treatments); (c) machine-specific hysteresis in pump flow rates, valve response times, and heat-exchanger fouling; (d) operator interventions and unrecorded process deviations. **The performance degradation on transfer from synthetic to real production data â€” and the recalibration methods required â€” have not been systematically studied in any published work.** This is identified as **Research Gap 4** (Â§7.4).

### 5.2 Reinforcement Learning for Setpoint Optimisation (Engine 2)

RL agents learn an optimal control policy through interaction with an environment â€” a physical process or its simulator â€” receiving scalar reward signals based on outcome quality. For dyeing, the natural Markov Decision Process (MDP) formulation is:

- **State s_t:** [bath pH_t, temperature_t, conductivity_t, K/S_t or dye_abs_t, step_index_t, time_in_step_t, dosing_accumulated_t, fabric_lot_features]
- **Action a_t:** adjustments to [alkali dose rate, salt dose rate, temperature setpoint, rinse termination flag, dwell extension duration] â€” all within pre-agreed safety clamps
- **Reward r_t:** composite function of [Î”Eâ‚‚â‚€â‚€â‚€ penalty (large if > 1.0), water_consumed_per_kg, steam_consumed_per_kg, RFT_terminal_bonus]

The agent learns to map states to actions that maximise discounted cumulative reward over the batch episode.

**Published RL applications to textile chemical processes:**

- **Kim et al. (2024)** [30]: Q-learning-based process recommendation model for dyeing, trained on real production data from a Korean dyehouse. Achieved average **66.58% reduction in residual dye concentration** vs. baseline (DOI: 10.1007/s40684-024-00627-7). This is the strongest published RL result for dyeing and notably one of very few using real production data.
- **He et al. (2021)** [43]: Deep RL (DQN) multi-criteria decision support system for textile chemical process optimisation. Demonstrated convergent Q-learning policy on simulated dyeing environment; multi-criteria reward incorporating quality, chemical cost, and time (Comput. Ind. 125:103373).
- **He et al. (2022)** [44]: Multi-objective DQN + multi-agent RL for manufacturing system optimisation including textile chemical processes (J. Manuf. Syst. 62:939â€“949).
- **Dogru et al. (2022)** [45]: Comprehensive review of RL in process industries; covers reward design, exploration strategies, and safety constraints relevant to dyeing deployment (Ind. Eng. Chem. Res. 61(46):16961â€“16978).
- **SMART DYEING Q-Learning (2026)** [9]: Deep Q-Network trained for 25,070 episodes (3,853 discrete Q-states, validated by executed notebook), achieving final RFT rate of **82.0%** and mean reward +30.8. Physics-informed twin environment uses Langmuir adsorption isotherms and Arrhenius kinetics; pH 10.0 threshold for soda ash (Naâ‚‚COâ‚ƒ) injection. All results on synthetic data.

**Advanced RL architectures for dyeing.** Beyond tabular Q-learning, three architectures are candidates for production deployment:
- **Soft Actor-Critic (SAC)** [46]: Maximum-entropy RL optimising both expected reward and policy entropy; suited for continuous action spaces (continuous dosing rate adjustment); stable training with off-policy replay.
- **Twin Delayed Deep Deterministic Policy Gradient (TD3)** [47]: Reduces overestimation bias in continuous control; demonstrated on process industry applications.
- **Proximal Policy Optimisation (PPO)** [48]: On-policy policy gradient; easier to tune than SAC/TD3; used in several manufacturing control demonstrations.

The choice between these architectures depends on whether the control action space is discrete (on/off dose trigger) or continuous (dose rate), and on available computational resources at the edge node.

**Critical limitation: no prospective randomised validation on real machines.** All published RL agents for dyeing â€” including the SMART DYEING Q-Network â€” are trained and evaluated in simulation. None have been validated in a prospective randomised trial on a real production dyeing machine with PLC write-back enabled. The evidence-based medicine standard â€” a pre-registered randomised controlled trial with a specified primary endpoint, pre-defined sample size, and independent statistical analysis â€” does not yet exist for RL-based dyeing control. We propose the A/B validation trial in Â§6 (Tread 4) as the domain-appropriate equivalent. This is **Research Gap 5** (Â§7.5).

### 5.3 Model-Predictive Control (MPC) for Batch Dyeing

MPC uses a process model to predict future state trajectories over a receding time horizon and solves a constrained optimisation problem at each control step to determine the optimal action sequence [49]. For batch dyeing, the MPC formulation predicts K/S and Î”E over the remaining batch time, subject to constraints on dosing rates (physical limits), safety clamps (agreed in governance step), and remaining process time. The optimal first action is executed; the optimisation repeats at the next step.

MPC's advantages for dyeing are: (a) explicit constraint handling (safety limits are in the optimisation, not a post-hoc clamp); (b) preview of consequences â€” it does not react, it anticipates; (c) compatibility with either mechanistic or data-driven surrogate models. Its primary challenge for edge deployment is computational load: each MPC step requires solving a (possibly nonlinear) optimisation problem, typically within the control period (1â€“30 s for dyeing). This is achievable with a fast surrogate model (CatBoost or XGBoost inference: < 1 ms per prediction on modern hardware) but not with a deep network without GPU acceleration [49,50].

### 5.4 Physics-Informed Neural Networks (PINNs) and Digital Twins

**PINNs.** Raissi et al. (2019) introduced PINNs â€” neural networks trained simultaneously on observed data and on the residuals of physical differential equations â€” as a data-efficient, physically consistent modelling approach [51]. For reactive dyeing, the relevant physics are: Langmuir adsorption isotherms (dye uptake rate), Arrhenius kinetic equations (temperature dependence of fixation rate), and Fick's diffusion laws (dye diffusion into fibre). A PINN trained on sparse laboratory measurements constrained by these equations would: (a) require fewer experimental batches than a pure black-box model; (b) extrapolate more safely to shade depths and dye classes outside the training distribution; and (c) provide a mechanistically interpretable model for auditing AI control decisions. Toscano et al. (2025) extended the PINN framework to Physics-Informed Kolmogorov-Arnold Networks (PIKANs) [52]. Yang et al. (2024) applied the PINN digital-twin concept to data-driven process simulation [53]. The SMART DYEING physics-informed twin (Langmuir + Arrhenius) is a step toward this architecture.

**Digital twins.** A digital twin of the dyeing machine â€” a real-time virtual replica updated by live sensor feeds â€” provides: (a) a safe environment for testing recipe modifications in silico before physical execution; (b) a training environment for RL agents that avoids wasting real batches on exploration failures; (c) root-cause analysis of quality deviations (replay the batch from the twin with varied inputs to identify the causal factor); and (d) operator training via realistic simulation [54,55]. Grieves & Vickers (2017) provide the foundational conceptual framework for digital twins in manufacturing [54]. The SMART DYEING twin is implemented in Python with a physics-based bath simulation; Langmuir and Arrhenius equations govern dye uptake and fixation; pH 10.0 triggers Naâ‚‚COâ‚ƒ injection in the twin's step logic [9].

### 5.5 Federated Learning: Cross-Factory Model Improvement Without Recipe Disclosure

A long-term scaling challenge for dyehouse AI is the **proprietary nature of dye formulations**: sharing raw batch data across factories for joint model training exposes commercial recipes that represent significant competitive IP. McMahan et al.'s Federated Averaging (FedAvg) algorithm [56] and its derivatives enable gradient-only sharing â€” the model's parameter update is shared after local training, not the raw data â€” protecting recipe confidentiality while allowing a shared model to improve across diverse production environments. The SMART DYEING architecture explicitly anticipates federated learning as a Phase 8 extension, sharing model gradient updates, not recipe details, across participating factories [9].

---

## 6. The Validation Staircase: A Proposed Scientific Standard for Closed-Loop Dyeing Claims

### 6.1 The Core Scientific Deficit

The central scientific deficit in current AI-for-dyeing literature is the absence of a rigorous, phased, pre-registered validation protocol for the transition from advisory (read-only AI) to closed-loop (write-back AI). Published papers typically report: (a) a model trained on laboratory or synthetic data; (b) evaluation metrics on a held-out portion of the same dataset; and (c) a proposal for deployment. The gap between step (b) and step (c) â€” the transition from offline evaluation to real machine operation â€” is bridged only by assertion, not by evidence.

We propose the following five-tread **validation staircase** as the minimum methodological standard for publications claiming closed-loop AI dyeing control. Each tread must be completed and its gate condition documented before stepping to the next tread. Failure at any tread automatically resets the system to advisory mode (the tread below) â€” failure is never permitted to propagate to a higher trust level.

### 6.2 Tread 0 â€” Governance and Interface Verification

**Actions:**
- Identify the process controller of record (SETEX / Sedo Treepoint / Sclavos / other); record model, firmware version, and OPC UA namespace version
- Obtain the interface documentation pack: OPC UA endpoint URL, security policy, X.509 certificate, and node/tag dictionary (or Sclavos gateway specification)
- Define the **safety envelope**: explicit min/max clamps for every variable the AI may ever influence (e.g., max soda ash dose rate, max salt addition, min rinse conductivity endpoint, max temperature setpoint offset)
- Write and sign the **control philosophy document**: AI = advisory/constrained-setpoint layer; PLC = safety and execution authority; operator = ultimate accept/reject authority for all AI recommendations
- Establish an OPC UA read-only connection to a live machine; confirm all required tags are readable at the required polling rate

**Gate 0 (pass criterion):** (a) signed control philosophy document with safety envelope; (b) functional, tested read-only OPC UA connection delivering all required tags at â‰¤ 30 s polling; (c) interface documentation obtained and verified for the specific controller firmware on site.

### 6.3 Tread 1 â€” Sensing Layer Installation and Validation

**Actions:**
- Install inline sensors (pH, conductivity, spectrophotometer measurement cell, energy meters) per the hardware specification and Â§4.2â€“4.5 requirements
- Pass each sensor through the four-gate validation protocol (S-1 calibration/traceability â†’ S-2 inline-vs-lab accuracy â†’ S-3 Gage R&R â†’ S-4 SPC drift)
- Assemble the **Batch Passport** live for â‰¥ 20 consecutive real batches: one timestamp-synchronised record per batch step combining controller OPC UA tags + sensor Modbus values + issued recipe; verify it matches the machine's own batch log on all shared fields
- Write and file the **tag dictionary**: source sensor/tag â†’ engineering unit â†’ model feature name, with no silent unit mismatches

**Gate 1 (pass criterion):** (a) all required sensor channels pass S-1 through S-4; (b) Batch Passport schema matches `feature_engineering.py` input schema; (c) Passport reconstructed correctly for â‰¥ 20 consecutive real batches.

### 6.4 Tread 2 â€” Shadow (Advisory) Mode: Read-Only Correlation Study

**Actions:**
- Run the AI inference system in **read-only** mode alongside normal production for a defined campaign of â‰¥ 100 real batches
- Sampling design: stratify across light/medium/dark shade depths and â‰¥ 3 fabric structures; deliberately over-sample dark shades (L* < 25) which are the hardest-to-match and most commercially sensitive
- Log the model's predictions (recipe adjustment recommendation, predicted Î”E, predicted RFT outcome) and the actual outcomes (final lab Î”E, QC pass/fail); the operator runs the normal recipe throughout â€” no write-back
- Display model recommendations on an operator tablet clearly labelled "ADVISORY ONLY â€” not executed" for operator familiarisation

**Gate 2 (pass criterion):** shadow dataset of â‰¥ 100 real batches complete; no systematic model failure (defined as: predicted Î”E direction consistently wrong for any shade family); operators understand advisory interface.

### 6.5 Tread 3 â€” Scientific Validation on Real Data (Pre-Registered)

This is the pivotal gate. **No setpoint write-back may be enabled until all Gate 3 criteria are met on pre-registered real held-out batches.**

**Pre-registration (before data analysis):** Register all of the following acceptance thresholds, the analysis plan, and the model architecture at OSF (Open Science Framework) or equivalent registry before performing any analysis of the Tread 2 dataset. This prevents post-hoc threshold adjustment.

**Re-training/recalibration:** Retrain or recalibrate all models on the Tread 2 real batch dataset. Accept that performance will settle below synthetic-data metrics â€” RÂ² â‰ˆ 0.85â€“0.92 for regression tasks, AUC â‰ˆ 0.85â€“0.92 for classification is the realistic expectation for real production data.

**Acceptance criteria (must all be met):**

| Statistical test | Acceptance threshold | Rationale |
|---|---|---|
| RFT classifier AUC-ROC | â‰¥ 0.85 | Clinically meaningful discrimination |
| Bootstrap 95% CI on AUC | Lower bound > 0.75 | Confidence interval, not just point estimate |
| DeLong test vs. no-model baseline | p < 0.05 | Significant improvement over operator default |
| Brier score | < 0.15 | Calibration: "90% pass" means 90% in reality |
| Expected Calibration Error (ECE) after Platt scaling | < 0.10 | Reliability diagram well-calibrated |
| Operating point (Youden's J on validation fold) | Pass-recall â‰¥ 0.80 AND Fail-recall â‰¥ 0.80 | Balanced sensitivity and specificity |
| Î”E regressor counterfactual check | Corrections move batches toward Î”E â‰¤ 1.0 | Directional correctness |

**Gate 3 (pass criterion):** all criteria above met simultaneously on pre-registered real held-out batches (minimum 20% of Tread 2 dataset held out, not used in retraining). Gate 3 failure requires additional data collection (return to Tread 2) before re-testing. **Write-back is forbidden until Gate 3 is passed.**

### 6.6 Tread 4 â€” Supervised Write-Back: Randomised A/B Trial

**Actions:**
- Enable OPC UA write-back for **ONE low-risk loop first** (recommended: rinse termination on conductivity threshold â€” a clearly defined, reversible, low-stakes first action)
- Implement **operator-in-the-loop confirmation**: AI proposes the setpoint (e.g., "terminate rinse at 0.45 mS/cm"); operator reviews and confirms or overrides on the HMI; confirmed value is written to the controller; all three values (proposed, confirmed, actual process response) are logged
- Randomise batches to AI-assisted vs. standard-recipe control (coin-flip or block randomisation); pre-register: (a) primary endpoint = RFT rate; (b) secondary endpoints = water per kg, steam per kg, chemical dose per kg; (c) required sample size for 80% power at the expected effect size; (d) analysis plan (logistic regression for RFT, paired t-test for resource metrics)
- Run trial to pre-registered sample size; halt if a pre-specified safety stopping rule is triggered

**Gate 4 (pass criterion):** (a) A/B trial shows statistically significant pre-registered primary endpoint improvement OR pre-registered non-inferiority with secondary resource savings; (b) zero safety events (no machine shutdown, no off-quality batch caused by AI action); (c) operator acceptance rate of AI recommendations above pre-agreed threshold (recommended: â‰¥ 70%).

### 6.7 Tread 5 â€” Constrained Closed-Loop (Automatic, One Loop at a Time)

**Actions:**
- Promote the validated loop from supervised (operator-confirmed) to **automatic** within the agreed safety clamps; operator override remains always available and is hardware-accessible
- **Add loops one at a time**, each requiring its own Treads 3â€“4 before promotion; never enable multiple new loops simultaneously
- Run **live drift monitoring** (ADWIN [57] or Page-Hinkley [58] algorithm, or Shewhart UCL on rolling prediction RMSE); on major/critical drift detection: automatically revert that loop to advisory mode and trigger a retrain notification
- Recalibrate the drift detection UCL on real production residual variance (the synthetic-data UCL value is not valid for real production residuals)
- Establish **MLOps infrastructure**: model registry (signed artifacts, training-data hash, validation report attached to each model version); scheduled retraining on accumulated real batches; forced retrain on drift trigger; audit trail of every AI setpoint write (timestamp, input state, proposed setpoint, operator confirm if applicable, actual process response)

**Gate 5 (pass criterion):** the loop maintains RFT and resource performance at or above Gate 4 A/B level for a sustained production campaign (minimum 200 additional batches); drift monitoring active with rollback demonstrated; MLOps audit trail verified by independent review.

### 6.8 The Staircase as a Publication Standard

We propose that reviewers and editors of journals publishing claims of "AI closed-loop dyeing control" should require authors to specify:
- Which tread of the staircase has been achieved
- Whether Gate 3 criteria were pre-registered before data analysis
- The source of the training data (synthetic / laboratory / real production) and sample size
- Whether a prospective randomised trial (Tread 4) has been conducted

Papers achieving only Treads 0â€“2 (advisory AI on real data) represent valuable scientific contributions; papers claiming "closed-loop control" without Tread 4 evidence are making an unsupported deployment claim.

---

## 7. Research Gap Taxonomy: Five Unresolved Frontiers

Based on the critical review above, we identify five specific, tractable, and independent research gaps that define the current frontier:

### 7.1 Gap 1: The Proprietary Controller Interoperability Problem (Systemic, High-Impact)

**Nature of the gap.** AI integration feasibility in a given dyehouse is determined primarily by which process controller is installed, not by which AI algorithm is chosen. For controllers with no public open interface (particularly Sclavos AquaChron and other OEM-proprietary systems), the entire AI integration pathway â€” from data acquisition to setpoint write â€” is blocked until the vendor provides interface access. **No peer-reviewed publication on AI-based dyeing control has addressed this barrier.**

**Required research directions:**
- (a) **Mapping study:** systematic survey of installed process controller types across Bangladesh, Sri Lanka, Vietnam, Cambodia, and other major developing-country dyeing hubs (manufacturer type, model, age, interface type). This is a dyehouse management questionnaire study â€” straightforward to execute, high policy value.
- (b) **Vendor engagement protocol:** what contractual terms should dyehouse operators request at machine purchase to ensure future AI integration rights? (OPC UA gateway provision, tag dictionary access, API licence provisions in procurement contracts.)
- (c) **Hardware-level PLC tap:** for controllers where vendor cooperation is unavailable, a generic I/O bus tap architecture â€” reading from the PLC's own analog and digital input/output modules â€” could provide process variable access independent of the controller's software stack. This requires knowledge of the specific PLC hardware (e.g., Siemens S7, Allen-Bradley CompactLogix) underlying the OEM controller, which varies by machine and vintage.

**Gap status:** Not addressed in any peer-reviewed publication to date. This gap is the gating constraint on real-world deployment for a significant fraction of dyehouses in developing countries.

### 7.2 Gap 2: The Opticalâ€“Conductivityâ€“pH Co-Calibration Model (Measurement Science)

**Nature of the gap.** Liao (2013) [31] established that reactive dye absorbance spectra are significantly distorted by salt (NaCl/Naâ‚‚SOâ‚„) and alkali (Naâ‚‚COâ‚ƒ/NaOH) concentrations at dyehouse levels, making spectrophotometric dye-concentration readings unreliable without co-referencing to simultaneously measured conductivity and pH. Despite this, virtually all published inline spectrophotometric dyeing control proposals assume the optical reading is a direct proxy for dye concentration without any correction for the electrolyte/alkali matrix.

**Required research directions:**
- (a) Systematic quantification of absorbance shift magnitude as a function of NaCl (0â€“80 g/L) and Naâ‚‚COâ‚ƒ (0â€“20 g/L) concentrations across the five major reactive dye classes (VS, DCT, MCT, bifunctional, phthalocyanine) at representative bath temperatures (50â€“80Â°C).
- (b) Development and validation of a multivariate calibration model â€” partial least squares (PLS) or feedforward ANN â€” mapping [absorbance spectrum, conductivity reading, pH reading] â†’ [dye concentration] with RMSEP < 5% of concentration range.
- (c) Industrial implementation: integrate the co-calibration model in the edge node's sensor fusion layer; validate inline vs. lab dye concentration over â‰¥ 30 batches with the model active.

**Gap status:** The problem is identified [31], but no multivariate co-calibration model has been published for industrial dyehouse conditions.

### 7.3 Gap 3: The Measurement Cell Engineering Specification (Deployment Engineering)

**Nature of the gap.** Inline spectrophotometry in a production dyebath requires an engineered measurement cell on a recirculation bypass â€” not direct probe immersion in the turbulent, aerated bath. This engineering requirement is referenced but never specified in detail in any published AI-for-dyeing paper, creating a publication-practice gap.

**Required research directions:**
- (a) Published engineering specification for a production-grade measurement cell: bypass flow rate (L/min), clarification method (gravity settling, inline filter, hydrocyclone), optical path length selection logic (dual path vs. single adaptive path), temperature conditioning method (heat exchanger or insulated bypass), fouling resistance and cleaning cycle (air back-flush, chemical clean, automatic wiper), and cell material compatibility (acid/alkali/dye resistance).
- (b) Quantitative comparison study: bypass-cell readings vs. direct-immersion readings in a production installation across the full batch cycle (concentrated dyeing bath through dilute final rinse); document absolute measurement error and reproducibility for each configuration.

**Gap status:** Terkesli et al. (2019) [15] imply a proper bypass-cell installation without publishing the cell specification. No dedicated publication exists on measurement cell design for reactive dyeing spectrophotometry.

### 7.4 Gap 4: Synthetic-to-Real Model Transfer (Statistical Machine Learning)

**Nature of the gap.** Virtually all published ML and RL models for reactive dyeing are trained on synthetic data (physics simulators) or small-scale laboratory datasets. The performance degradation on transfer to real production data â€” and the statistical methods required to efficiently recalibrate with limited real batch data â€” have not been systematically studied or reported in the open literature.

**Required research directions:**
- (a) **Matched-pairs degradation study:** train models on synthetic data from a physics simulator; evaluate on real production batches from the same factory; measure the performance degradation quantitatively (Î”RÂ², Î”AUC, Î”Brier). Understand which features and shade families show the largest degradation.
- (b) **Efficient recalibration methods:** given a limited real-batch dataset (50â€“200 batches, reflecting deployment reality), compare: (i) full retraining on real data; (ii) fine-tuning (transfer learning) from the synthetic-pretrained model; (iii) Bayesian updating of model parameters; (iv) active learning (query strategy for maximally informative new batches to acquire). Identify which method achieves acceptable performance at minimum real-batch cost.
- (c) **Model family robustness:** characterise which model families (linear, kernel-SVM, gradient boosting, deep learning) transfer most robustly from synthetic to real data for the dyeing problem; provide practical guidance for practitioners.

**Gap status:** Acknowledged as a caveat in individual papers (including the SMART DYEING project's own documentation [9]) but never systematically addressed as a primary research question.

### 7.5 Gap 5: Prospective Randomised Validation of RL Setpoint Control (Clinical-Trial Equivalent)

**Nature of the gap.** The highest level of evidence for a therapeutic intervention in medicine is the pre-registered randomised controlled trial (RCT) with a pre-specified primary endpoint and appropriate statistical power. The analogous standard for an industrial AI control system would be a prospective randomised trial (AI-assisted vs. standard recipe, randomly allocated to batches) with a pre-registered primary endpoint (RFT rate), pre-specified sample size, and independent statistical analysis. No such trial exists in the published literature for RL-based or ML-based dyeing setpoint control.

**Required research directions:**
- (a) **Design and execution:** design a pre-registered prospective A/B trial on a real production dyeing machine meeting the Gate 4 criteria in Â§6.6. Report: (i) primary endpoint (RFT rate), with 95% CI and p-value vs. standard recipe; (ii) safety events (zero tolerance); (iii) resource outcomes (water, steam, chemical per kg) with 95% CI; (iv) operator acceptance rate of AI recommendations; (v) economic analysis (cost per kg vs. AI system capital and operating cost).
- (b) **Trial reporting standard:** adopt CONSORT-style trial reporting adapted for industrial process control AI: pre-registration, randomisation method, blinding if applicable, sample size justification, ITT analysis, sensitivity analysis.

**Gap status:** Not addressed in any peer-reviewed publication to date. Kim et al. (2024) [30] comes closest with real production data but does not describe a randomised allocation or pre-registered endpoint.

---

## 8. Implications for the Bangladesh Context

### 8.1 The Scale of the Resource-Efficiency Prize

Bangladesh's cotton-knit dyeing sector processes approximately 1.5 billion kg of fabric annually. At the verified SMART DYEING energy baseline from South East Textiles (1.849 kWh/kg electrical; 9.64 kg steam/kg thermal, single-boiler baseline Janâ€“Apr 2026 [37]), and with steam representing **â‰ˆ77% of total energy** (22.6 MJ/kg thermal vs. 6.7 MJ/kg electrical), the thermal energy savings from conductivity-guided rinse optimisation â€” the single highest-ROI AI intervention â€” are substantial at sector scale. A conservative **20% steam reduction** (from 9.64 â†’ 7.71 kg steam/kg) across the sector would save approximately 2.9 Ã— 10â¹ kg steam/year, equivalent to approximately 7.0 Ã— 10â¶ GJ/year of primary thermal energy. At local natural gas prices in Bangladesh (~BDT 14â€“17/mÂ³), the annual BDT saving for the sector from this one intervention alone would be in the tens of billions of taka.

The quality prize is equally significant: raising from open-loop colour error (Î”Eâ‚‚â‚€â‚€â‚€ â‰ˆ 13.05 Â± 2.50) toward a Î”E â‰¤ 1.0 RFT gate â€” with each failed batch consuming a full second thermal cycle â€” directly links RFT improvement to steam and chemical savings. The energy decomposition analysis of SETL's data reveals that approximately **39% of steam** is fixed/standby load (condensate losses, boiler blowdown, distribution losses) â€” independent of production volume [37]. This standby fraction is a thermal audit target requiring no AI: fixing condensate return alone, before any AI is deployed, could reduce steam intensity by 15â€“25%.

### 8.2 Four Barriers Specific to Bangladesh and Developing-Country Dyehouses

**Barrier 1: Capital constraint.** The upfront cost of inline sensing (pH probe + transmitter: ~USD 1,500â€“3,000; conductivity: ~USD 1,000â€“2,500; inline spectrophotometer + measurement cell: ~USD 8,000â€“25,000; per-machine energy meters: ~USD 500â€“2,000; edge node computing hardware: ~USD 2,000â€“5,000) totals approximately **USD 13,000â€“37,000 per machine** [32]. For small and medium dyehouses (< 20 machines) operating on thin margins in a highly competitive RMG export market, this capital cost is material and requires either external financing (green finance, development bank instruments, buyer sustainability programmes) or a phased approach that starts with the lowest-cost highest-return sensors (pH + conductivity first).

**Barrier 2: Controller diversity and machine age.** Many installed dyeing machines in Bangladesh are 15â€“25 years old. For machines of this vintage: (a) the OEM process controller may be discontinued with no firmware updates available; (b) interface documentation may be lost or proprietary; (c) the installed PLC hardware may be an obsolete model with limited third-party gateway support. Upgrading the process controller on an old machine can approach the value of the machine itself. This creates a class of machines for which the Gap 1 hardware tap approach (Â§7.1c) is the only AI integration pathway.

**Barrier 3: Technical workforce capacity.** Deploying and maintaining an AI-integrated dyehouse requires skills not currently prevalent in the Bangladesh dyehouse technical workforce: industrial calibration (pH/conductivity/spectrophotometer), OPC UA client configuration and security provisioning, Linux-based edge node administration, ML model monitoring, and drift-detection response. A systematic **capacity-building programme** â€” combining vendor training (SETEX, Sedo Treepoint), vocational training institute curriculum development, and on-the-job training at pilot factories â€” is a prerequisite for sustainable deployment at scale.

**Barrier 4: Regulatory incentive alignment.** Bangladesh's Environmental Conservation Rules 2023 (ECR-2023) establish effluent discharge standards (BOD, COD, TDS, colour) relevant to reactive dyeing. The SDG framework (SDGs 6, 9, 12) and the government's Eighth Five-Year Plan (2021â€“2025) create policy alignment for green manufacturing. However, the specific regulatory instruments needed to drive investment in AI-based process control â€” energy-intensity benchmarks, effluent-reduction incentives, green technology import duty relief, green finance guarantees â€” are not yet calibrated to create a compelling business case for technology adoption at the factory level [6,57].

### 8.3 A Staged Deployment Pathway for Bangladesh Dyehouses

We recommend a staged deployment pathway that sequences interventions by evidence quality, ROI, and risk:

**Stage 1 (Immediate; no AI required; ~0â€“6 months):** Commission a thermal-system audit addressing the ~39% fixed/standby steam fraction [37]: condensate-return percentage measurement and improvement; boiler blowdown rate optimisation; pipe and valve insulation audit; boiler-to-load matching (correct boiler capacity for current production volume). Install per-machine electrical sub-meters and steam flow meters for energy attribution. Establish IPMVP Option C M&V baseline (production-normalised energy regression). This Stage alone can deliver 15â€“25% thermal savings with no sensors, no ML, and no PLC modification.

**Stage 2 (Short-term; sensors + advisory mode; ~6â€“18 months):** Install pH and conductivity per target machine; connect to edge node via Modbus; run in advisory/shadow mode (Treads 0â€“2). Collect Batch Passport data for 100+ real batches. The conductivity signal alone enables operator-guided rinse optimisation (Stage 2 already changes operator behaviour before any write-back is enabled). Capital cost at this stage: ~USD 2,500â€“5,500 per machine for sensors + shared edge node.

**Stage 3 (Medium-term; first AI write loop; ~18â€“30 months):** Pass Gate 3 on real batch data (Tread 3 scientific validation, pre-registered). Enable OPC UA write-back for rinse termination on conductivity threshold on SETEX/Sedo machines; run the Gate 4 A/B randomised trial. This is the first AI-to-PLC write action; justification to plant management is built from the Stage 2 shadow data quantifying the conductivity-vs-time relationship.

**Stage 4 (Long-term; multi-loop validated; ~30â€“48+ months):** Add spectrophotometric exhaustion monitoring (with measurement cell and co-calibration model per Gaps 2/3); implement pH-based alkali dosing loop; deploy recipe pre-correction from the real-data-retrained surrogate model. Each control loop validated through its own Gate 4 A/B trial before automation. MLOps infrastructure (model registry, scheduled retraining, audit trail) in place.

---

## 9. Discussion: The Architecture of an AI-Ready Dyehouse

### 9.1 The Edge Node as the Integration Hub

The architectural resolution of the control-hierarchy tension â€” AI intelligence without compromising PLC safety â€” is the **edge node**: a ruggedised industrial computer adjacent to (not integrated into) the dyeing machine, which:

- Runs an OPC UA client subscribing to the process controller at configurable polling intervals
- Runs a Modbus master polling inline sensors on the RS-485 bus
- Assembles the Batch Passport (one timestamp-synchronised record per batch step: controller tags + sensor values + issued recipe)
- Runs ML inference (surrogate model, RFT classifier, RL agent) at process cadence
- Serves predictions and recommendations to an operator HMI (tablet or display)
- Once authorised by Gate 3: writes constrained setpoints back to the process controller via OPC UA method calls

The edge node is the only new computing element in the architecture. The PLC's hard-wired safety interlocks are unchanged, as is the process controller's recipe execution logic. The edge node's interface to the world is purely through the process controller's OPC UA server â€” the same interface used by existing MES software â€” so it introduces no new attack surface on the PLC safety layer. If the edge node fails or loses connectivity, the machine continues on its native process controller recipe with no degradation. **The AI is fail-safe by omission.**

### 9.2 The Non-Negotiable Safety Boundary

The following control functions are PLC-hard and must remain exclusively in the PLC, unreachable by any external system including the AI:
- Over-temperature interlock (vessel contents scalding temperature)
- Over-pressure interlock (hydraulic vessel burst pressure)
- Liquid level interlocks (pump dry-run protection; vessel overfill)
- Door interlock (vessel access under pressure or temperature)

The AI system operates only through the process-controller layer (Layer 2 per Â§3.1), which already operates within the safety envelopes enforced by Layer 1. The AI additionally enforces its own software clamps (agreed in the safety envelope at Gate 0) on all proposed setpoints before they are displayed to the operator or written to the controller. This dual-layer enforcement (PLC hard limit + AI software clamp) ensures that even a malfunctioning AI cannot command a safety violation.

### 9.3 MLOps Requirements for Sustainable Production Deployment

Production deployment of AI in a dyehouse requires a model operations (MLOps) infrastructure absent from virtually all academic AI-for-dyeing proposals:

- **Model registry:** every deployed model artifact is signed, versioned, and has the training-data hash and Gate 3 validation report attached. Promotion to "Production" status requires a passed Gate 3. Rollback to any prior Production-validated model must be executable within one operator shift.
- **Scheduled retraining:** models are retrained on accumulated real batches on a defined schedule (recommended: quarterly, or after every 200 new production batches) using a rolling window that preserves seasonal and batch-lot variation.
- **Forced retraining on drift:** any ADWIN/Page-Hinkley drift trigger on a live control loop triggers an automatic revert of that loop to advisory mode and a notification to the data science team to investigate root cause and retrain.
- **Audit trail:** every AI setpoint write is logged with: UTC timestamp; batch ID; model version; input feature vector hash; proposed setpoint value; operator-confirmed value (if supervised mode); actual process response (from subsequent OPC UA reading); operator ID. This trail supports regulatory compliance, dispute resolution, and retrospective analysis.

---

## 10. Conclusion

This systematic review has synthesised the peer-reviewed evidence and engineering reality for PLC-mediated AI closed-loop control of reactive dyeing, with specific reference to the Bangladesh developing-country dyehouse context. The principal conclusions are:

1. **The process science is settled.** Dyebath pH (â‰ˆ45% of fixation variance), temperature, salt/conductivity, and dye concentration are the four parameters most strongly governing reactive dyeing outcome; their inline measurement is scientifically validated in peer-reviewed industrial trials.

2. **The communication technology stack is available.** OPC UA (SETEX, Sedo Treepoint) provides a complete, secure, bidirectional interface for AI integration on the two most commercially prevalent dyeing process controllers globally. Modbus RTU/TCP provides the field-sensor interface. The technical infrastructure for a full AI closed-loop system on these platforms exists today.

3. **Proprietary controller lock-in is the single largest unaddressed barrier.** Sclavos AquaChron and other OEM-proprietary controllers have no public open interface; a significant fraction of developing-country dyehouses run on these platforms. This is a vendor-policy and contractual problem â€” not an algorithm problem â€” and has not been acknowledged in the peer-reviewed literature.

4. **The ML/RL algorithms are algorithm-mature but deployment-immature.** No published study has demonstrated RL-based setpoint write-back on a real production dyeing machine in a prospective randomised trial with pre-registered primary endpoint. The validation gap is the critical scientific deficit separating the field's promise from its demonstrated impact.

5. **Five specific research gaps** define the unresolved frontier: (1) proprietary controller interoperability; (2) opticalâ€“conductivityâ€“pH co-calibration; (3) measurement cell engineering specification; (4) synthetic-to-real model transfer; and (5) prospective randomised validation of RL setpoint control.

6. **The five-tread validation staircase** (Governance â†’ Sensing validation â†’ Shadow mode â†’ Scientific validation on real data â†’ Randomised A/B trial â†’ Constrained closed-loop) is proposed as the minimum scientific standard for future publications claiming closed-loop AI dyeing control.

7. **The Bangladesh context amplifies both the opportunity and the difficulty.** At verified sector-scale energy intensities of 1.849 kWh/kg electrical and 9.64 kg steam/kg thermal â€” with 77% of total energy being thermal, 39% of which is fixed/standby waste â€” the resource-efficiency prize is among the largest available in any developing-country manufacturing sector. A staged deployment pathway (thermal audit â†’ advisory sensing â†’ single supervised loop â†’ multi-loop constrained closed-loop) provides a risk-graduated, evidence-based route to capturing that prize.

The transition from "AI promising for reactive dyeing" to "AI validated and deployed in reactive dyeing" requires not better algorithms but better integration engineering, better measurement science, better validation protocols, and better regulatory and financial instruments to incentivise adoption. This review is offered as a rigorous framework to guide that transition.

---

## Declaration of Interests

The authors declare that the SMART DYEING project (Project EOI) is funded by the Bangladesh Industrial Research and Development Institute (Industrial Research Consortium) under the Research Programme programme, with South East Textiles (Pvt.) Ltd. as the deployment partner. No commercial conflict of interest exists with any sensor, PLC, or software vendor mentioned in this review.

---

## References

[1] Li Z, et al. (2024). Current trends in textile wastewater treatment: a bibliometric review. *Environ. Sci. Pollut. Res.* doi:10.1007/s11356-024-XXXX

[2] Uddin MA, et al. (2023). Water and chemical consumption in the textile processing industry of Bangladesh. *PLOS Sustainability and Transformation*. doi:10.1371/journal.pstr.0000030

[3] Nallathambi A, et al. (2016). Salt-free reactive dyeing of cotton hosiery fabrics by exhaust application of cationic agent. *Carbohydrate Polymers* 150:270â€“277

[4] Khatri A, et al. (2015). A review on developments in dyeing cotton fabrics with reactive dyes for reducing effluent pollution. *J. Cleaner Production* 87:50â€“57

[5] Chakraborty R, et al. (2022). Economical use of water in cotton knit dyeing industries of Bangladesh. *J. Cleaner Production* 363:132350

[6] Hossain L, et al. (2018). Evaluation of present and future wastewater impacts of textile dyeing industries in Bangladesh. *Environ. Development* 26:23â€“33

[7] Zhang P, et al. (2022). Toward improved performance of reactive dyeing on cotton fabric using process sensitivity analysis. *Int. J. Clothing Sci. Technol.* 34(4):601â€“619

[8] Hossain I, et al. (2016). Dyeing process parameters optimisation and colour strength prediction for reactive dyeing: Taguchi method. *J. Textile Institute* 107(7):914â€“922

[9] SMART DYEING Project (2026). ML Pipeline QA & Verification Report; PLC Sensor Integration 0-to-1 Runbook; Energy Baseline Analysis SETL (Project EOI, Industrial Research Consortium/Research Programme). Internal verified technical documents, June 2026.

[10] Shore J (1995). *Cellulosics Dyeing*. Society of Dyers and Colourists, Bradford

[11] Pervez M, et al. (2023). Optimization and prediction of the cotton fabric dyeing process using a Taguchi design-integrated machine learning approach. *Scientific Reports* 13:7890

[12] Siddiqua UH, et al. (2021). Hetero-functional azo reactive dyes: synthesis and dyeing conditions optimization using RSM. *J. Eng. Fibers Fabrics* 16:1â€“12

[13] Ingle N, Jasper WJ (2025). A review of deep learning and AI in dyeing, printing and finishing. *Textile Res. J.* 95(5â€“6):625â€“657. doi:10.1177/00405175241268619

[14] SMART DYEING Technical Framework (2026). TF-SD-2026-v2.0. Internal document Project EOI.

[15] Terkesli I, et al. (2019). Industrial spectrophotometric smart sensor towards real-time optimization of textile dyeing. *IEEE Sensors Applications Symposium (SAS)*. doi:10.1109/SAS.2019.8706047

[16] Alves B, et al. (2022). Substrate colour prediction through active monitoring of the exhaustion dyeing process. *Mater. Sci. Forum* 1068:133â€“142

[17] IEC 61511 (2016). *Functional Safety â€” Safety Instrumented Systems for the Process Industry Sector*. IEC, Geneva

[18] SETEX (2024). E390/C390 controllers, Extended OPC-UA, OrgaTEX MES â€” product documentation. setex-germany.com

[19] Sedo Treepoint (2024). Sedomat 6000/8000, OPC UA + MQTT + Modbus, SEDOMASTER MES â€” product documentation. sedo-treepoint.com

[20] Sclavos (2024). AquaChron SMART, T.I.C., in-house automation. sclavos.eu

[21] ZVEI (2015). *RAMI 4.0 â€” Reference Architectural Model Industrie 4.0*. ZVEI, Frankfurt

[22] HiveMQ (2024). OPC UA and MQTT: complementary IIoT protocols. hivemq.com

[23] Eclipse Foundation (2023). MQTT Sparkplug B Specification v3.0.0

[24] Modbus Organization (2012). *Modbus Application Protocol Specification v1.1b3*

[25] FlowFuse (2024). Modbus TCP vs OPC UA: selecting the right protocol for your industrial application. flowfuse.com

[26] Keith C, et al. (2004). Real-time data acquisition in batch dyeing processes. *Color. Technol.* 120(3):108â€“114

[27] Astisensor (2023). Industrial pH/ORP probes for high-temperature alkaline applications. astisensor.com

[28] Pyxis Lab (2023). Industrial inline conductivity and pH transmitters â€” Modbus RTU. pyxis-lab.com

[29] AIAG (2010). *Measurement System Analysis Reference Manual*, 4th ed. Automotive Industry Action Group

[30] Kim S, et al. (2024). Application of reinforcement learning to dyeing processes for residual dye reduction. *Int. J. Precis. Eng. Manuf.-Green Tech.* doi:10.1007/s40684-024-00627-7

[31] Liao X (2013). Solutions for online detection of the concentration of reactive dye bath. *Spectroscopy and Spectral Analysis* (China). [Full DOI in SMART DYEING Reference Register]

[32] ProSense (2024). Toroidal conductivity selection guide for textile dyebath applications. prosense.com.au

[33] Waring DR, Hallas G (eds.) (1990). *The Chemistry and Application of Dyes*. Plenum, New York

[34] Dai Y, et al. (2020). Real-time monitoring of multicomponent reactive dye adsorption by Raman spectroscopy combined with PLS. *Spectrochim. Acta A* 231:118125

[35] Kir A, et al. (2024). Resource utilization in the sub-sectors of the textile industry: opportunities for sustainability. *Environ. Sci. Pollut. Res.* 31:36890â€“36910

[36] IEC 60751 (2022). *Industrial Platinum Resistance Thermometers and Platinum Temperature Sensors*

[37] SMART DYEING Energy Baseline Analysis â€” SETL (2026). Verified M1â€“M3 baseline, South East Textiles, Janâ€“May 2026. Project EOI deliverable.

[38] Senthilkumar M, Selvakumar N (2012). Application of artificial neural networks for colour prediction of reactive dyestuffs. *J. Textile Institute* 103(10):1068â€“1076

[39] Wu YC, et al. (2003). GA-based grey nonlinear integer programming for dyeing scheduling. *Comput. Chem. Eng.* 27(6):833â€“855

[40] Chen Z, Liu J, Li J, et al. (2024). Leveraging multi-output modelling for CIELAB prediction in sustainable textile dyeing. *Autonomous Intelligent Systems* 4(1):19. doi:10.1007/s43684-024-00076-8

[41] Zhang J, et al. (2021). Dyeing recipe prediction for cotton fabric using hyperspectral imaging and improved RNN. *Color. Technol.* 137(2):166â€“180

[42] Li F, Chen C, Mao Z (2022). FWSVR + PSO dyeing recipe prediction from bath measurements. *Color. Technol.* 138(5):495â€“508

[43] He Z, Tran KP, Thomassey S, et al. (2021). A DRL-based multi-criteria decision support system for optimizing textile chemical process. *Comput. Ind.* 125:103373

[44] He Z, Tran KP, Thomassey S, et al. (2022). Multi-objective optimization using deep-Q multi-agent RL in manufacturing. *J. Manuf. Syst.* 62:939â€“949. arXiv:2012.01101

[45] Dogru O, et al. (2022). Reinforcement learning in process industries: review and perspective. *Ind. Eng. Chem. Res.* 61(46):16961â€“16978

[46] Haarnoja T, et al. (2018). Soft actor-critic: off-policy maximum entropy deep reinforcement learning. *ICML* 80:1861â€“1870. arXiv:1801.01290

[47] Fujimoto S, van Hoof H, Meger D (2018). Addressing function approximation error in actor-critic methods (TD3). *ICML*. arXiv:1802.09477

[48] Schulman J, et al. (2017). Proximal policy optimization algorithms. arXiv:1707.06347

[49] Rawlings JB, Mayne DQ, Diehl M (2017). *Model Predictive Control: Theory, Computation, and Design*, 2nd ed. Nob Hill Publishing

[50] Dogru O, Srinivasan B, Bhatt N, et al. (2021). Soft actor-critic with hybrid mixed-integer actions for energy systems. *Ind. Eng. Chem. Res.* doi:10.1021/acs.iecr.1c01728

[51] Raissi M, Perdikaris P, Karniadakis GE (2019). Physics-informed neural networks: a deep learning framework for solving forward and inverse problems involving nonlinear PDEs. *J. Comput. Phys.* 378:686â€“707

[52] Toscano JD, et al. (2025). From PINNs to PIKANs: recent advances in physics-informed machine learning. *Mach. Learn. Comput. Sci. Eng.* 1:1â€“43

[53] Yang S, Mao Z, Karniadakis GE, et al. (2024). Data-driven physics-informed neural networks: a digital twin perspective. *Comput. Methods Appl. Mech. Eng.* (in press)

[54] Grieves M, Vickers J (2017). Digital twin: mitigating unpredictable, undesirable emergent behavior in complex systems. In: Kahlen J, Flumerfelt S, Alves A (eds.) *Transdisciplinary Perspectives on Complex Systems*. Springer, pp. 85â€“113. doi:10.1007/978-3-319-38756-7_4

[55] Grieves M (2017). Digital twin: manufacturing excellence through virtual factory replication. White Paper. Florida Institute of Technology.

[56] McMahan HB, Moore E, Ramage D, et al. (2017). Communication-efficient learning of deep networks from decentralized data (FedAvg). *AISTATS* 54:1273â€“1282. arXiv:1602.05629

[57] Bifet A, GavaldÃ  R (2007). Learning from time-changing data with adaptive windowing (ADWIN). In: Proc. 7th SIAM Int. Conf. Data Mining, pp. 443â€“448

[58] Page ES (1954). Continuous inspection schemes. *Biometrika* 41(1/2):100â€“115

[59] Rasmussen KH, et al. (2025). Water vulnerability assessment in Dhaka, Bangladesh, and Bangladesh: implications for the textile industry. *Water* 17(16):2475

[60] Bangladesh ECR-2023 (2023). Environmental Conservation Rules 2023. Ministry of Environment, Forest and Climate Change, People's Republic of Bangladesh.

---

## Appendix A: SMART DYEING Project Verified Parameter and Model Reference Table

| Parameter | Governance role | Influence rank [7] | Inline sensor | Interface | Validated performance |
|---|---|---|---|---|---|
| Dyebath pH | Fixation chemistry (â‰ˆ45% of variance) | **1** | High-T alkali-resistant probe + transmitter | Modbus RTU | Target: R â‰¥ 0.95 vs. lab; bias â‰¤ 0.05 pH |
| Temperature | Exhaustion/fixation kinetics | **2** | PT100/1000 RTD (PLC tag) | OPC UA | Â±0.5Â°C vs. traceable reference |
| Dye concentration (K/S) | E%, exhaustion endpoint, recipe pre-correct | **3** | Inline spectrophotometer in bypass cell | Ethernet/serial | Î”Eâ‚‰â‚„ â‰¤ 0.70 ceiling [16]; R > 0.99 Raman [34] |
| Conductivity | Salt level; rinse endpoint; deconfounds optics [31] | **4** | Toroidal/4-electrode | Modbus RTU | Â±1% FS; GRR < 10% |
| Dosing/step-time | Recipe kinetics context | **5** | Controller dose counters + step index | OPC UA (read) | Consistent with batch record |
| Liquor ratio | Bath concentration normaliser | **6** | Batch weight + fill volume | PLC tags | Â±2% of nominal |
| Per-batch energy | RL reward; M&V attribution | â€” | Electrical sub-meter + steam flow meter | Modbus/pulse | IPMVP Option C M&V |

**SMART DYEING verified ML metrics (synthetic data, EXECUTED11.ipynb):**

| Module | Metric | Value | Data source |
|---|---|---|---|
| Module 1 (spectralâ†’CIELAB, CatBoost) | Test RÂ² | 0.9972 | Synthetic |
| Module 2 (KS_final, LSSVR) | Test RÂ² | 0.9833 | Synthetic |
| Module 2 (Î”E regressor, XGBoost) | Test RÂ² | 0.8655 | Synthetic |
| Module 3 (RFT classifier, XGBoost) | AUC-ROC | 0.9133 | Synthetic |
| Module 3 (Q-Learning, DQN) | Final RFT rate | 82.0% | Synthetic |
| Module 3 (Q-Learning) | Episodes to convergence | 25,070 | Synthetic |
| Drift detector | Baseline RMSE / UCL | 0.8075 / 1.1075 | Synthetic |
| Energy baseline (SETL, metered) | Electrical | 1.849 kWh/kg | **Real (metered)** |
| Energy baseline (SETL, metered) | Steam (single-boiler Janâ€“Apr 2026) | 9.64 kg/kg | **Real (metered)** |

---

## Appendix B: Minimum Reporting Checklist for AI Closed-Loop Dyeing Publications

Authors and reviewers of papers claiming AI-based closed-loop dyeing control are recommended to verify the following items are reported:

- [ ] **Controller platform:** OEM, model, firmware version, interface type (OPC UA / proprietary / other)
- [ ] **Inline sensors installed:** list with calibration date, inline-vs-lab R value, GRR%, SPC status per channel
- [ ] **Opticalâ€“conductivityâ€“pH co-calibration:** co-calibration model specified or absence justified
- [ ] **Measurement cell:** bypass-cell engineering specification or direct-immersion justification
- [ ] **Training data source:** synthetic / laboratory / real production; sample size; shade and fabric distribution
- [ ] **Shadow-mode dataset:** size, shade distribution, over-sampling strategy for dark shades
- [ ] **Pre-registration:** acceptance gates pre-registered before real-data analysis (OSF or equivalent)
- [ ] **Validation staircase tread achieved:** 0 / 1 / 2 / 3 / 4 / 5 per Â§6
- [ ] **Write-back mechanism:** OPC UA node, method, safety clamp values, operator confirmation protocol
- [ ] **A/B trial design:** randomisation method, primary endpoint, sample size, statistical analysis
- [ ] **Drift monitoring:** method (ADWIN / Page-Hinkley / SPC) and rollback protocol
- [ ] **MLOps infrastructure:** model registry, retrain schedule, audit trail described

---

*Manuscript prepared June 2026. Verified quantitative data from the SMART DYEING project (Project EOI, Industrial Research Consortium/Research Programme) are traceable to executed pipeline artifacts (EXECUTED11.ipynb, smart_dyeing_work/) and metered factory data from South East Textiles (Pvt.) Ltd., Tangail, Bangladesh (Januaryâ€“May 2026). All ML performance metrics are from synthetic-data pipeline execution and are explicitly stated as such; field validation is in progress per the Â§6 validation staircase. Vendor interface information is from manufacturer public documentation (June 2026) and is marked [CONFIRM WITH VENDOR] in project engineering documents where site-specific verification is required.*

