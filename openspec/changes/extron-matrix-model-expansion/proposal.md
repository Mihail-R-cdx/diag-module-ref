# Change: Extron matrix model expansion

## Why

The application currently exposes Matrix diagnostics and routing through an IN1804-specific handler and a single-output presentation model. The next supported-device expansion needs to cover additional Extron presentation switchers and matrix frames without conflating physical connectors, logical routing outputs, or model-specific SIS semantics.

The supported scope for this change is explicitly limited to:

- Extron IN1804 (existing hardware-validated baseline, preserved without regression)
- Extron IN1806
- Extron IN1808
- Extron IN1608 xi
- Extron DTP CrossPoint 84
- Extron DTP CrossPoint 4K Series: DTP CrossPoint 82 4K, 84 4K, 86 4K, and 108 4K

First-generation XTP CrossPoint 1600/3200 and XTP II CrossPoint 1600/3200/6400 remain deferred from production-supported scope in this change. This is an explicit scope decision independent of the Matrix General-information fields. Earlier XTP/XTP II implementation in this branch is historical work only and SHALL NOT keep those models production-dispatchable.

Legacy CrossPoint 300/450/Ultra, DTP2 CrossPoint, DTP3 CrossPoint, and any other CrossPoint generation not named above are explicitly out of scope and SHALL NOT inherit a supported profile by family-name similarity.

The change also removes the current single-output assumption from normalized Matrix state and room GUI so devices with multiple independently routable outputs can be represented correctly.

## What Changes

- Modify the existing root Matrix requirements rather than creating parallel normative contracts for supported diagnostics, limited device control, fail-closed Matrix normalization/reconciliation, MatrixScreen intent ownership, and Matrix room presentation.
- Introduce an explicit Extron Matrix capability/topology model that separates exact device identity, logical input/output numbering, actually available input/output IDs, independently routable outputs, physical output connectors/endpoints, and per-family command/capability support.
- Preserve the current IN1804 hardware-confirmed command profile as the compatibility baseline, even where an official manual documents an alternate accepted SIS form.
- Add model/family-specific SIS profiles for IN1806, IN1808, and IN1608 xi. IN1806 remains its own exact six-input application/profile identity rather than being represented as IN1808. For these newly added presentation-switcher profiles, canonical Matrix routing is video-only so polling, mutation, and reconciliation describe the same visible state; IN1804 retains its separate hardware-confirmed legacy compatibility profile.
- Keep identity resolution closed while accepting hardware-proven exact evidence: `IN1608 xi IPCP SA` resolves to canonical `IN1608 xi`, DTP CrossPoint 108 4K exact part number `60-1381-12` resolves to that existing canonical profile, and IN1806 exact identity/part number remains `IN1806` / `60-1663-01`.
- Keep DTP CrossPoint route semantics video-only: canonical `routes[output_id]` is read with `<O>%`, set with `<I>*<O>%`, and untied with `0*<O>%`. Audio ties are outside the current Matrix table. Deferred XTP/XTP II route syntax is historical evidence only and SHALL NOT authorize production dispatch.
- Remove hardware-QA-discovered production Matrix presentation leftovers: no `Отладка` affordance, no information-card `IP-адрес` row, no embedded `!`/warning action, and no trailing action/footer area below the approved information fields.
- For DTP CrossPoint, support only the exact DTP CrossPoint 84 and DTP CrossPoint 4K model set listed above; fixed topology is resolved from authoritative exact-model identity/profile data.
- Retire XTP/XTP II from unified production registration and inventory dispatch in this change. Their exact identity/topology research may be reused only by a future separately reviewed change that proves the same mandatory six-field acquisition contract.
- Normalize Matrix routing as an output-to-input mapping instead of a single `current_connection` scalar.
- Render one routing column per independently routable and currently available logical output. Physical output connectors SHALL NOT create duplicate routing columns when they share one logical route.
- Keep input signal presence, HDCP state, names, and output metadata capability-driven. For every remaining in-scope Matrix, complete successful refresh requires all five General-information values: model, MAC address, serial number, firmware version, and temperature. MAC and serial are mandatory canonical inventory prerequisites; firmware and temperature use exact approved SIS reads.
- Use family-specific HDCP command and decoder profiles for the remaining supported IN/DTP scope. Historical XTP/XTP II HDCP work does not keep those deferred profiles supported.
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
- Any DTP generation not explicitly resolved to one of the approved profiles above.
- First-generation XTP CrossPoint and XTP II CrossPoint production support; these models remain explicitly deferred from this change and require a separately reviewed scope decision before production enablement.
- Speculative support for commands not proven by official Extron documentation or hardware evidence.
- Reworking unrelated codec, audio-DSP, PDU, room-search, credential, or occupancy behavior.
- Treating every physical output connector as an independently routable output.
- Topology discovery by sending state-changing switch commands.

## Expected Result

A Matrix record can represent both a single-output presentation switcher and a multi-output CrossPoint frame through one normalized domain model. The GUI renders the authoritative available logical outputs dynamically, while the handler layer selects exact generation/model-specific SIS command and decoder profiles without guessing unsupported capabilities.