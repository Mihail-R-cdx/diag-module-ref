# Change: Extron matrix model expansion

## Why

The application currently exposes Matrix diagnostics and routing through an IN1804-specific handler and a single-output presentation model. The next supported-device expansion needs to cover additional Extron presentation switchers and matrix frames without conflating physical connectors, logical routing outputs, or model-specific SIS semantics.

The supported scope for this change is explicitly limited to:

- Extron IN1804 (existing hardware-validated baseline, preserved without regression)
- Extron IN1808
- Extron IN1608 xi
- Extron DTP CrossPoint 84
- Extron DTP CrossPoint 4K Series: DTP CrossPoint 82 4K, 84 4K, 86 4K, and 108 4K
- Extron XTP CrossPoint Series frames supported by the first-generation XTP profile
- Extron XTP II CrossPoint Series frames supported by the XTP II profile

Legacy CrossPoint 300/450/Ultra, DTP2 CrossPoint, DTP3 CrossPoint, and any other CrossPoint generation not named above are explicitly out of scope and SHALL NOT inherit a supported profile by family-name similarity.

The change also removes the current single-output assumption from normalized Matrix state and room GUI so devices with multiple independently routable outputs can be represented correctly.

## What Changes

- Modify the existing root Matrix requirements rather than creating parallel normative contracts for supported diagnostics, limited device control, fail-closed Matrix normalization/reconciliation, MatrixScreen intent ownership, and Matrix room presentation.
- Introduce an explicit Extron Matrix capability/topology model that separates exact device identity, logical input/output numbering, actually available input/output IDs, independently routable outputs, physical output connectors/endpoints, and per-family command/capability support.
- Preserve the current IN1804 hardware-confirmed command profile as the compatibility baseline, even where an official manual documents an alternate accepted SIS form.
- Add model/family-specific SIS profiles for IN1808 and IN1608 xi.
- Add a common multi-output CrossPoint AV-routing profile only where the documented SIS syntax is shared, while keeping identity/topology and diagnostic command profiles family-specific.
- For DTP CrossPoint, support only the exact DTP CrossPoint 84 and DTP CrossPoint 4K model set listed above; fixed topology is resolved from authoritative exact-model identity/profile data.
- For XTP/XTP II, select the generation-specific profile from authoritative frame identity evidence before decoding board/configuration evidence. Matrix dimensions alone SHALL NOT discriminate XTP from XTP II.
- Discover XTP/XTP II runtime topology from read-only matrix-dimension plus installed-board evidence; do not infer topology with state-changing route probes.
- Normalize Matrix routing as an output-to-input mapping instead of a single `current_connection` scalar.
- Render one routing column per independently routable and currently available logical output. Physical output connectors SHALL NOT create duplicate routing columns when they share one logical route.
- Keep input signal presence, HDCP state, names, temperature, and output metadata capability-driven. Unsupported or unproven reads SHALL remain unavailable rather than using speculative SIS commands.
- Use family-specific HDCP command and decoder profiles. In particular, DTP output HDCP uses `WO<N>HDCP`, first-generation XTP output HDCP uses `W0<N>HDCP`, and XTP II output HDCP remains UNPROVEN until separately established from official evidence.
- Preserve existing Matrix route mutation ambiguity/no-replay and reconciliation safety.

## Command Evidence Baseline

The change SHALL use the existing working IN1804 implementation as the hardware-validated compatibility baseline:

- identity/model: `1I`
- temperature: `W20STAT`
- input names: `WI<N>VNAM`
- output name: `WO1VNAM`
- signal presence: `W0LS`
- HDCP authorization: `WE<N>HDCP`
- input HDCP status: `WI<N>HDCP`
- output HDCP status: `WO1HDCP`
- current route: `!`
- route mutation: `<I>*1!`

The Extron transport appends the command terminator; pseudo-characters used in Extron manuals are not literal command bytes.

For new devices, only officially documented or separately hardware-validated SIS operations may be added to a capability profile.

## Out of Scope

- Legacy analog CrossPoint 300/450/Ultra support.
- DTP2 CrossPoint and DTP3 CrossPoint support.
- Any DTP/XTP generation not explicitly resolved to one of the approved profiles above.
- Speculative support for commands not proven by official Extron documentation or hardware evidence.
- Reworking unrelated codec, audio-DSP, PDU, room-search, credential, or occupancy behavior.
- Treating every physical output connector as an independently routable output.
- Topology discovery by sending state-changing switch commands.

## Expected Result

A Matrix record can represent both a single-output presentation switcher and a multi-output CrossPoint frame through one normalized domain model. The GUI renders the authoritative available logical outputs dynamically, while the handler layer selects exact generation/model-specific SIS command and decoder profiles without guessing unsupported capabilities.