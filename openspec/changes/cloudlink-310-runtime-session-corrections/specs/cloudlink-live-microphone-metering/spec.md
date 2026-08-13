# cloudlink-live-microphone-metering Specification

## MODIFIED Requirements

### Requirement: CloudLink live microphone metering has a closed model and protocol contract

Live microphone metering SHALL support exactly these diagnostic models:

```text
CloudLink Bar 310
CloudLink Box 310
```

The capability SHALL reuse the application-selected credential and the shared CloudLink 310 handler/session boundary. It SHALL NOT create a credential source, select or iterate credential candidates in the handler/worker, alias Bar and Box identities, or persist successful credential/profile memory from meter-only telemetry.

For `CloudLink Bar 310`, the live sample source SHALL remain exactly:

```text
GET /v1/mediacontrol/mic/current-volume
```

Before the Bar request, the current CloudLink handler generation SHALL have established the modern read context through:

```text
POST /v1/login/session
POST /v1/login/account
```

using only the credential already assigned by the application/composition layer. The successful modern login SHALL yield a usable `data.acCSRFToken` retained only as in-memory session material. The Bar meter request SHALL transmit that token as `X-Access-Token` in the established modern HTTP session. The token is not a new credential, SHALL NOT be persisted, and SHALL NOT authorize handler-owned credential fallback.

After response decoding, `data["curMicVouumeList"]` SHALL be a list. Every Mapping entry in the complete list SHALL be eligible regardless of `deviceId`. Every non-negative numeric `curVolume` SHALL contribute an observation, and the raw microphone level SHALL be the maximum valid `curVolume` across all entries. The implementation SHALL NOT exclude `deviceId == 18`, assume a fixed identifier range, select one preferred device, or use list position as channel authority.

For `CloudLink Box 310`, the live sample source SHALL remain exactly:

```text
POST action.cgi?ActionID=WEB_GetCurrentAudioParam
```

The Box meter request SHALL use the existing legacy compatibility subcontext and its already approved Box-specific action/payload semantics. This change SHALL NOT route `WEB_GetCurrentAudioParam` through the modern read subcontext, SHALL NOT newly require `X-Access-Token` or the modern body-token shape for this endpoint, and SHALL NOT redirect Box metering to the Bar `/v1/mediacontrol/mic/current-volume` endpoint. A later change may migrate this exact Box endpoint only after separate approved compatibility evidence.

Only this existing closed Box microphone field set SHALL contribute:

```text
mic1ValueIndex
mic2ValueIndex
mic3ValueIndex
mic4ValueIndex
micArray1_01ValIdx
micArray1_02ValIdx
micArray1_03ValIdx
micArray2_01ValIdx
micArray2_02ValIdx
micArray2_03ValIdx
micArray3_01ValIdx
micArray3_02ValIdx
micArray3_03ValIdx
```

Each present non-negative numeric value SHALL contribute an observation and the raw level SHALL be the maximum valid value. The implementation SHALL NOT scan arbitrary field names or include TRS, RCA, HDMI, Bluetooth, UAC, `m220w_porwer_hint`, or another unreviewed non-microphone audio field.

An empty Bar list, a Bar list with no valid `curVolume`, or a Box payload with no valid value from the closed microphone set SHALL be an unavailable sample and SHALL NOT be represented as numeric zero. A successfully observed raw numeric `0` SHALL remain an available sample at 0%.

An established-session HTTP 401/403 SHALL remain a typed session invalidation under the existing bounded same-credential recovery policy. A generic HTTP-200 application response with `success: 0`, arbitrary exception/message text, or another unapproved discriminator SHALL NOT by itself authorize credential fallback, token discovery, model switching, or string-heuristic session invalidation.

#### Scenario: Bar meter uses the modern read token

- **GIVEN** the application has assigned exact `CloudLink Bar 310` and one credential
- **AND** the shared handler established its modern read context successfully
- **WHEN** live metering requests `GET /v1/mediacontrol/mic/current-volume`
- **THEN** the request reuses that modern session and cookies
- **AND** it transmits the in-memory modern token as `X-Access-Token`
- **AND** it does not establish a meter-specific credential flow

#### Scenario: Bar sample includes device ID 18

- **GIVEN** a successful Bar sample contains valid `curVolume` observations including `deviceId == 18`
- **WHEN** the raw level is normalized
- **THEN** every valid list entry participates in the maximum
- **AND** `deviceId == 18` is not excluded

#### Scenario: Bar observed silence is available

- **WHEN** a successful Bar payload has valid observations whose maximum is numeric zero
- **THEN** the sample is available
- **AND** raw level is zero
- **AND** the display fraction is 0%

#### Scenario: Box meter keeps its approved source and legacy context

- **GIVEN** the current exact model is `CloudLink Box 310`
- **WHEN** live metering reads a sample
- **THEN** it uses `WEB_GetCurrentAudioParam` through the existing legacy compatibility subcontext
- **AND** this change does not require the modern read token/header/body shape for that endpoint
- **AND** it does not call the Bar current-volume endpoint
- **AND** only the existing closed Box microphone fields contribute

#### Scenario: Established meter session is rejected

- **WHEN** a current Bar or Box meter request receives established-session HTTP 401 or 403
- **THEN** the failure remains typed session invalidation
- **AND** same-credential bounded recovery remains authoritative
- **AND** the handler does not advance credentials or switch Bar/Box identity

#### Scenario: Application-level unsuccessful sample has no approved auth discriminator

- **WHEN** an established meter request returns HTTP 200 with generic `success: 0`
- **AND** no separately approved structured authentication discriminator is present
- **THEN** the cycle is treated as an endpoint command/protocol outcome according to the common failure boundary
- **AND** arbitrary response strings do not authorize credential fallback or model switching

#### Scenario: No valid microphone observation exists

- **WHEN** the model-specific successful response contains no valid microphone-level observation
- **THEN** the sample is unavailable
- **AND** numeric zero is not manufactured
