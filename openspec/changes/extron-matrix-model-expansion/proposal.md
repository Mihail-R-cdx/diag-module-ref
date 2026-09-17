# Change: Extron matrix model expansion

## Why

The application currently exposes Matrix diagnostics and routing through an IN1804-specific handler and a single-output presentation model. The next supported-device expansion needs to cover additional Extron presentation switchers and matrix frames without conflating physical connectors, logical routing outputs, or model-specific SIS semantics.

The supported scope for this change is:

- Extron IN1804 (existing hardware-validated baseline, preserved without regression)
- Extron IN1808
- Extron IN1608 xi
- Extron DTP CrossPoint family
- Extron XTP CrossPoint family
- Extron XTP II CrossPoint family

Legacy CrossPoint 300/450/Ultra devices are explicitly out of scope.

The change also needs to remove the current single-output assumption from the normalized Matrix state and room GUI so devices with multiple independently routable outputs can be represented correctly.

## What Changes

- Introduce an explicit Extron Matrix capability/topology model that separates:
  - exact device identity;
  - logical input/output numbering;
  - actually available input/output IDs;
  - independently routable outputs;
  - physical output connectors/endpoints;
  - per-family command/capability support.
- Preserve the current IN1804 hardware-confirmed command profile as the compatibility baseline, even where an official manual documents an alternate accepted SIS form.
- Add model/family-specific SIS profiles for IN1808 and IN1608 xi.
- Add a common multi-output CrossPoint routing profile for DTP CrossPoint, XTP CrossPoint, and XTP II CrossPoint, while keeping identity/topology and diagnostic capabilities family-specific.
- Discover fixed DTP CrossPoint topology from authoritative exact-model identity/profile data.
- Discover XTP/XTP II runtime topology from read-only identity/dimension and installed-board evidence; do not infer topology with state-changing route probes.
- Normalize Matrix routing as an output-to-input mapping instead of a single `current_connection` scalar.
- Render one routing column per independently routable and currently available output in the Matrix GUI. Physical output connectors SHALL NOT create duplicate routing columns when they share one logical route.
- Keep input signal presence, HDCP state, names, temperature, and output metadata capability-driven. Unsupported or unproven reads SHALL remain unavailable rather than using speculative SIS commands.
- Use family-specific HDCP decoders because raw values `1` and `2` have different meanings across Extron generations.

## Command Evidence Baseline

The change SHALL use the existing working IN1804 implementation as the hardware-validated compatibility baseline for currently deployed IN1804 devices:

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

The Extron transport appends the command terminator; pseudo-characters used in Extron manuals (for example the printed symbol representing carriage return) are not literal command bytes.

For new devices, only officially documented or separately hardware-validated SIS operations may be added to a capability profile.

## Out of Scope

- Legacy analog CrossPoint 300/450/Ultra support.
- Speculative support for commands not proven by official Extron documentation or hardware evidence.
- Reworking unrelated codec, audio-DSP, PDU, room-search, credential, or occupancy behavior.
- Treating every physical output connector as an independently routable output.
- Topology discovery by sending state-changing switch commands.

## Expected Result

A Matrix record can represent both a single-output presentation switcher and a multi-output CrossPoint frame through one normalized domain model. The GUI can therefore render the correct number of route columns dynamically, while the handler layer selects the correct SIS syntax and status decoders for each supported family.