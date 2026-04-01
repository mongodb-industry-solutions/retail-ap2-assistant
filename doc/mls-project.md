# Project Summary: Mandate Ledger Service - AP2 & UCP Protocol Implementation supported on MongoDB

> For a detailed explanation of AP2 protocol theory (actors, VDCs, workflows, threat model, dispute resolution, ecosystem, and roadmap), see [AP2 Summary](./ap2-summary.md). This document focuses on **how this project implements** AP2 and UCP, and answers architectural and security questions specific to this codebase.

## Table of Contents

1. [What This Project Is](#1-what-this-project-is)
2. [Architecture](#2-architecture)
3. [Transaction Lifecycle](#3-transaction-lifecycle)
4. [Merchant Discovery and Multi-Merchant Search](#4-merchant-discovery-and-multi-merchant-search)
5. [Signatures: Who Signs What, With What Payload](#5-signatures-who-signs-what-with-what-payload)
6. [Non-Repudiation and Multi-User Agents](#6-non-repudiation-and-multi-user-agents)
7. [Security Between Agents and MITM Prevention](#7-security-between-agents-and-mitm-prevention)
8. [Signature Verification by the Auditor](#8-signature-verification-by-the-auditor)
9. [Immutability and Idempotency](#9-immutability-and-idempotency)
10. [Compliance and Audit Trail](#10-compliance-and-audit-trail)
11. [Multi-Protocol Ecosystem: UCP, A2A, and MCP](#11-multi-protocol-ecosystem-ucp-a2a-and-mcp)

---

## 1. What This Project Is

This repository is a **Proof of Concept (PoC)** demonstrating how an AP2 Mandate Ledger backed by **MongoDB Atlas** can serve as the immutable System of Record for agentic commerce. It is built with Python 3.12+, FastAPI, Motor (async MongoDB), and Pydantic.

| Component | Location | Purpose |
|-----------|----------|---------|
| **Mandate Ledger Service** | `mandate_ledger_service/` | Core append-only ledger API with authentication, state machine, and audit trail |
| **Card Flow Example** | `example/card_flow/` | Multi-agent demo using **A2A** protocol between agents |
| **UCP Flow Example** | `example/ucp_flow/` | REST-based demo using **UCP** between shopper agent and merchant server |
| **Shared AP2 Types** | `example/src/ap2/types/` | Pydantic models for IntentMandate, CartMandate, PaymentMandate |
| **Common Utilities** | `example/src/common/` | `MandateLedgerClient`, A2A helpers, validation |

---

## 2. Architecture

```
┌──────────────────────┐                    ┌──────────────────────┐
│   Consumer Agent     │   UCP REST / A2A   │   Merchant Server    │
│   (Shopper)          │◄──────────────────►│   (e.g. Amazon)      │
│                      │   /.well-known     │                      │
│   NO database        │   /api/checkout    │   HAS AP2 Ledger     │
│   NO AP2 client      │   /api/products    │   Integration        │
└──────────────────────┘                    └──────────┬───────────┘
                                                       │
                                                       │ HTTP (AP2 API)
                                                       ▼
                                            ┌──────────────────────┐
                                            │  Mandate Ledger      │
                                            │  Service (FastAPI)   │
                                            │                      │
                                            │  ┌────────────────┐  │
                                            │  │ Authentication │  │
                                            │  │ Rate Limiting  │  │
                                            │  │ Idempotency    │  │
                                            │  │ State Machine  │  │
                                            │  │ Hashing/Audit  │  │
                                            │  └────────┬───────┘  │
                                            │           │          │
                                            │           ▼          │
                                            │  ┌────────────────┐  │
                                            │  │  MongoDB Atlas │  │
                                            │  │  (Immutable    │  │
                                            │  │   Ledger)      │  │
                                            │  └────────────────┘  │
                                            └──────────────────────┘
```

The Mandate Ledger Service sits between agents and MongoDB, organized in three layers:

| Layer | Responsibility | Key Files |
|-------|---------------|-----------|
| **Authentication** | API key validation (bcrypt), RBAC, scoped permissions | `api/dependencies.py`, `services/auth_service.py` |
| **Business Logic** | State machine, idempotency, hashing, signatures | `core/state_machine.py`, `core/hashing.py`, `services/` |
| **Data Access** | MongoDB append-only inserts, aggregation queries | `repositories/`, `db/mongodb.py` |

---

## 3. Transaction Lifecycle

A complete purchase flows through these steps (combining UCP discovery with AP2 ledger writes):

| Step | Actor | Action | Ledger Effect |
|------|-------|--------|---------------|
| 1 | Shopper Agent | Fetches `/.well-known/ucp.json` from merchant | — |
| 2 | Shopper Agent | Verifies `dev.ucp.shopping.ap2_mandate` capability | — |
| 3 | Shopper Agent | `POST /api/checkout` with items + **signed intent** | — |
| 4 | Merchant | Creates **IntentMandate** (with shopper's intent signature) | IntentMandate v1 created |
| 5 | Merchant | Builds cart, signs it with **merchant private key** | — |
| 6 | Merchant | Returns checkout response with signed cart | — |
| 7 | Shopper Agent | Presents cart to user, obtains consent | — |
| 8 | Shopper Agent | `POST /api/checkout/{id}/confirm` with **cart signature** | — |
| 9 | Merchant | Creates **CartMandate** with **both signatures** | CartMandate v1 created (status: signed) |
| 10 | Shopper Agent | `POST /api/checkout/{id}/complete` with **payment signature** | — |
| 11 | Merchant | Creates **PaymentMandate** (with shopper's payment signature) | PaymentMandate v1 created (status: authorized) |
| 12 | Merchant | Processes payment, creates **Payment Record** linking all 3 mandates | Payment record created |
| 13 | Merchant | Returns order confirmation and receipt | — |

---

## 4. Merchant Discovery and Multi-Merchant Search

### Who Is Responsible for Discovery?

UCP follows a **decentralized model** there is no central registry. **Each merchant publishes its own profile** at `/.well-known/ucp.json` on its domain, like `robots.txt` or `/.well-known/openid-configuration`:

```
amazon.com        → GET https://amazon.com/.well-known/ucp.json
ebay.com          → GET https://ebay.com/.well-known/ucp.json
walmart.com       → GET https://walmart.com/.well-known/ucp.json
local-bakery.com  → GET https://local-bakery.com/.well-known/ucp.json
```

Each merchant must:
1. Expose a `/.well-known/ucp.json` endpoint declaring capabilities, payment handlers, and signing keys
2. Implement the declared capabilities (product search, checkout, orders)
3. Optionally declare `dev.ucp.shopping.ap2_mandate` if they integrate AP2

The **platform or consumer agent** is responsible for knowing which merchant domains to query. This works through several mechanisms:

| Discovery Method | How It Works | Example |
|-----------------|-------------|---------|
| **Direct URL** | User provides the merchant domain | "Buy from amazon.com" |
| **Search engine integration** | Platform queries a search index for merchants selling a product | Google Shopping, Bing Shopping |
| **Merchant aggregator/catalog** | Platform maintains a curated list of known UCP-compliant merchants | Similar to Google Merchant Center |
| **Crawling/indexing** | Automated systems discover `/.well-known/ucp.json` by crawling known e-commerce domains | Like Googlebot for web pages |
| **A2A Agent Cards** | In the A2A protocol variant, agents discover each other via `agent.json` files | Card flow demo uses hardcoded URLs |

In this project's demo, the shopper agent uses a **configured URL** (environment variable `UCP_MERCHANT_URL`) to know where the merchant is:

```python
DEFAULT_MERCHANT_URL = os.getenv("UCP_MERCHANT_URL", "http://localhost:8004")
```

In a production system, the **platform** (e.g., Google, a shopping aggregator) would maintain an index of known UCP-compatible merchant domains, built through a combination of merchant self-registration (via tools like Google Merchant Center) and automated crawling.

#### Does Registration Exist?

While the **UCP specification itself** does not mandate a central registry, **platforms** that implement UCP (like Google) do offer **integration paths** for merchants to register:

- **Google Merchant Center:** merchants register their product catalogs, which Google then surfaces in conversational AI experiences
- **Developer consoles:** merchants configure their UCP endpoints and verify domain ownership
- **Partner programs:** large retailers may have direct integration partnerships

This is similar to how any website serves content in a decentralized manner, while search engines like Google and Bing create centralized indexes for easier discoverability. Although UCP does not require a centralized registry, platforms such as Google provide integration options (e.g., Merchant Center, developer consoles) that function as a centralized layer for surfacing information on top of the decentralized framework.

### How Multi-Merchant Product Search Works

When a user asks "I want to buy speakers," the system must search across multiple merchants. This happens in layers:

#### The Flow

```
User: "I want to buy speakers"
         │
         ▼
┌─────────────────────────┐
│   Platform / AI Agent   │  (ChatGPT, Gemini, etc.)
│                         │
│  1. Identify candidate  │
│     merchant domains    │──────────┬─────────────┬─────────────┐
│                         │          │             │             │
│  2. Discover each       │     ┌──────────┐  ┌──────────┐  ┌──────────┐
│     merchant via        │────►│ Amazon   │  │  eBay    │  │ Walmart  │
│     /.well-known/ucp    │     │ .well-   │  │ .well-   │  │ .well-   │
│                         │     │ known/   │  │ known/   │  │ known/   │
│  3. Search products     │     │ ucp.json │  │ ucp.json │  │ ucp.json │
│     on each merchant    │     └────┬─────┘  └────┬─────┘  └────┬─────┘
│                         │          │             │             │
│  4. Aggregate results   │     GET /products  GET /products  GET /products
│                         │     ?q=speakers   ?q=speakers   ?q=speakers
│  5. Present unified     │          │             │             │
│     list to user        │          ▼             ▼             ▼
│                         │     3 results      3 results    3 results
│  6. User selects one    │          │             │             │
│                         │◄─────────┴─────────────┴─────────────┘
│  7. Checkout with the   │
│     chosen merchant     │
└─────────────────────────┘
```

#### Step-by-Step

| Step | Actor | Action |
|------|-------|--------|
| 1 | **Platform** | Determines candidate merchants from its index (Merchant Center, search index, user preferences, etc.) |
| 2 | **Platform** | Calls `/.well-known/ucp.json` on each merchant domain to discover capabilities and endpoints |
| 3 | **Platform** | Sends `GET /api/products?q=speakers` to each merchant's product search endpoint (in parallel) |
| 4 | **Platform** | Aggregates and ranks results from all merchants |
| 5 | **Platform** | Presents a unified product list to the user: "I found speakers at Amazon ($49), eBay ($39), and Walmart ($45)" |
| 6 | **User** | Selects a product and merchant |
| 7 | **Platform** | Initiates the checkout flow **only** with the chosen merchant |


This PoC demonstrates a single-merchant flow. In production, the platform layer handles aggregation.

### Implementation in This Project

The merchant publishes its profile in `example/ucp_flow/merchant_server/well_known.py`. The shopper agent discovers it in `example/ucp_flow/shopper_agent/ucp_client.py`:

```python
async def discover(self) -> dict:
    resp = await client.get(f"{self.merchant_url}/.well-known/ucp.json")
    self._capabilities = resp.json()
    return self._capabilities

def supports_ap2_mandate(self) -> bool:
    return any(c.get("name") == "dev.ucp.shopping.ap2_mandate"
               for c in self._capabilities.get("capabilities", []))
```

---

## 5. Signatures: Who Signs What, With What Payload

### Yes, Both Parties Sign

Every purchase carries **signatures from both the client (shopping agent on behalf of the user) and the merchant**. They sign at different stages and over different content.

### The Signature Data Model

Every signature stored in the ledger follows this structure (`mandate_ledger_service/src/models/mandate.py`):

```python
class SignatureEntry(BaseModel):
    signature: str       # The cryptographic output (JWT, hex hash, verifiable credential)
    signer_id: str       # Who signed (e.g., "ucp_shopper", "ucp_merchant")
    signer_type: str     # Role (e.g., "consumer-agent", "merchant-agent")
    algorithm: str       # Algorithm used (EdDSA, ES256, RS256, SHA256, JWT)
    signed_at: datetime  # UTC timestamp
    metadata: dict       # Key ID, verification URL, etc.
```

### What Each Party Signs (Step by Step With Payload Examples)

#### Step 1: Shopper Signs the Intent

The shopper agent creates a signature over the user's shopping intent. The **content being signed** is the intent data, what the user wants to buy:

```json
// CONTENT BEING SIGNED (input to hash function):
{
  "intent": "I want to buy an Espresso Machine",
  "product": {
    "label": "Espresso Machine - Professional Grade",
    "amount": { "currency": "USD", "value": 189.99 }
  }
}

// RESULTING SIGNATURE ENTRY (stored in the IntentMandate):
{
  "signature": "sig_7a3f2b1c9e4d5f6a8b0c1d2e3f4a5b6c",  // SHA-256 hash of canonical JSON above
  "signer_id": "ucp_shopper",
  "signer_type": "consumer-agent",
  "algorithm": "SHA256",
  "signed_at": "2026-03-30T14:22:00Z"
}
```

#### Step 2: Merchant Signs the Cart (merchant_authorization)

The merchant builds the cart and signs it with their private key. The **content being signed** is the complete cart offer, items, prices, shipping, totals:

```json
// CONTENT BEING SIGNED (the entire CartMandate data):
{
  "contents": {
    "id": "cart_ucp_checkout_a1b2c3_9f8e7d6c",
    "user_cart_confirmation_required": true,
    "payment_request": {
      "method_data": [{ "supported_methods": "CARD", "data": {"network": ["visa","mastercard"]} }],
      "details": {
        "id": "order_ucp_checkout_a1b2c3",
        "display_items": [
          { "label": "Espresso Machine", "amount": {"currency": "USD", "value": 189.99} }
        ],
        "total": { "label": "Total", "amount": {"currency": "USD", "value": 189.99} }
      }
    },
    "cart_expiry": "2026-03-30T15:00:00Z",
    "merchant_name": "UCP Demo Merchant"
  },
  "merchant_authorization": "eyJhbGciOiJSUzI1NiIs..."  // JWT signed with merchant's private key
}

// RESULTING SIGNATURE ENTRY:
{
  "signature": "eyJhbGciOiJSUzI1NiIs...",  // JWT (in production) or mock
  "signer_id": "ucp_merchant",
  "signer_type": "merchant-agent",
  "algorithm": "JWT",
  "signed_at": "2026-03-30T14:22:05Z"
}
```

#### Step 3: Shopper Signs the Cart (cart confirmation)

After the user reviews and approves the cart, the shopper signs the **entire cart content** (including the merchant's authorization inside it). The signed payload is the same cart object the merchant built:

```json
// CONTENT BEING SIGNED (the full cart as received from merchant):
{
  "contents": {
    "id": "cart_ucp_checkout_a1b2c3_9f8e7d6c",
    "payment_request": { "...same as above..." },
    "merchant_name": "UCP Demo Merchant"
  },
  "merchant_authorization": "eyJhbGciOiJSUzI1NiIs..."
}

// RESULTING SIGNATURE ENTRY:
{
  "signature": "sig_b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9",
  "signer_id": "ucp_shopper",
  "signer_type": "consumer-agent",
  "algorithm": "SHA256",
  "signed_at": "2026-03-30T14:23:10Z"
}
```

**Both signatures are then stored together** on the CartMandate ledger entry:

```python
cart_entry = await ledger_client.create_mandate(
    mandate_type="CartMandate",
    mandate_data=cart_mandate.model_dump(),
    initial_signatures=[shopper_cart_signature, merchant_signature],
    initial_status="signed",
)
```

#### Step 4: Shopper Signs the Payment Authorization

The shopper creates a final signature authorizing payment. The **content being signed** is the payment-specific data:

```json
// CONTENT BEING SIGNED:
{
  "checkout_id": "ucp_checkout_a1b2c3",
  "cart_id": "cart_ucp_checkout_a1b2c3_9f8e7d6c",
  "payment_method": "CARD",
  "amount": { "label": "Total", "amount": {"currency": "USD", "value": 189.99} }
}

// RESULTING SIGNATURE ENTRY:
{
  "signature": "sig_c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0",
  "signer_id": "ucp_shopper",
  "signer_type": "consumer-agent",
  "algorithm": "SHA256",
  "signed_at": "2026-03-30T14:24:00Z"
}
```

### What Differentiates a Merchant Signature from a Client Signature?

The **signature structure is identical**, both produce a `SignatureEntry` with the same fields. The differences are:

| Aspect | Client (Shopper) Signature | Merchant Signature |
|--------|---------------------------|-------------------|
| `signer_id` | User/agent identifier (e.g., `"ucp_shopper"`) | Merchant identifier (e.g., `"ucp_merchant"`) |
| `signer_type` | `"consumer-agent"` | `"merchant-agent"` |
| `algorithm` | SHA-256 (PoC) / EdDSA or ES256 (production) | JWT with RS256 (production) |
| **Private key** | User's device key (hardware-backed in production) | Merchant's server-side private key |
| **What it proves** | "I (the user) agree to these terms" | "I (the merchant) commit to fulfilling these terms at this price" |
| **Content signed** | Varies per step (intent, cart, payment) | The cart offer with pricing |

### Are Signatures Inside the Content Being Signed?

**Yes, by design.** When the shopper signs the cart at Step 3, the merchant's `merchant_authorization` is **already inside** the cart payload. This is intentional, the shopper is signing "I agree to this cart **as offered by this merchant** (as proven by their signature)." This creates a nested attestation chain:

```
Shopper's signature covers:
  └── Cart content
        └── merchant_authorization (merchant's JWT signature)
              └── Cart terms (items, prices, totals)
```

If the merchant's signature were removed or altered, the shopper's hash would no longer match, detecting the tampering.

---

## 6. Non-Repudiation and Multi-User Agents

### The Problem: One Shopping Agent, Many Users

A shopping agent (like Gemini or ChatGPT) serves millions of users. If the agent signs mandates with a shared agent key, any user could claim "that wasn't me" and the signature would only prove "some user of Gemini approved this" not *which* user.

### How AP2 Solves This (Production Architecture)

AP2 specifies that the user's signature must be created with a **hardware-backed key on the user's personal device**, not the agent's server key:

| Layer | Mechanism | Non-Repudiation Strength |
|-------|-----------|------------------------|
| **Device key binding** | The user's private key lives in their device's secure enclave (TPM, Secure Element). It never leaves the device. | Proves the physical device was present |
| **Biometric authentication** | The key is unlocked via fingerprint, face scan, or PIN before signing | Proves the device owner was present |
| **Key per user, not per agent** | Each user has their own key pair. The agent never holds the private key. | Eliminates "which user?" ambiguity |

The flow works like this:

```
Shopping Agent (server)                    User's Device (phone/laptop)
        │                                          │
        │  "Please approve this cart"              │
        │────────────────────────────────────────► │
        │                                          │ 1. Display cart to user
        │                                          │ 2. User confirms via biometric
        │                                          │ 3. Secure enclave signs the cart
        │                                          │    with user's PERSONAL private key
        │  ◄──── signed mandate  ──────────────────│
        │                                          │
        │  Agent forwards the user-signed          │
        │  mandate to the merchant                 │
```

The agent acts as a **relay**, it orchestrates the flow but never holds the user's signing key. This is similar to how Apple Pay works: the phone's secure enclave signs the transaction, not the merchant's app.

### What This PoC Implements

This PoC uses **simplified signatures** (SHA-256 hashes with an agent-level key) for demonstration. In production:

| PoC (This Project) | Production (AP2 Spec) |
|--------------------|----------------------|
| `hashlib.sha256(data).hexdigest()` | `device_secure_enclave.sign(data, user_private_key)` |
| Agent key shared across sessions | User's personal hardware-backed key |
| No biometric gate | Fingerprint/face required before signing |
| Signer identified by `signer_id` string | Signer identified by verifiable credential + device attestation |

---

## 7. Security Between Agents and MITM Prevention

### Signatures Do NOT Secure the Connection

This is a critical distinction:

| Concern | Mechanism | What It Protects |
|---------|-----------|-----------------|
| **Non-repudiation** | Cryptographic signatures on mandates | Proves who authorized what, used **after** the transaction for disputes |
| **Transport security** | TLS/HTTPS, mTLS, API keys, OAuth2 | Protects data **in transit**, prevents eavesdropping and MITM |

Signatures prove "this data was approved by this party." They do **not** guarantee that the party you are talking to right now is who they claim to be. That is the job of transport-layer security.

### How MITM Is Prevented

Agent-to-agent and agent-to-service communication is protected by **multiple layers**, none of which are the mandate signatures:

#### Layer 1: TLS/HTTPS (Transport Encryption)

All communication uses HTTPS. A MITM attacker cannot read or alter data in transit because:
- The server presents a TLS certificate issued by a trusted CA
- The client verifies the certificate chain before sending data
- All traffic is encrypted end-to-end

#### Layer 2: API Key Authentication (Service Identity)

The Mandate Ledger Service requires an API key (`Authorization: Bearer mlsk_...`) on every request. Each agent has its own key with specific scopes:

```python
# Every request is authenticated, unknown agents are rejected
if not verify_api_key(api_key, key_record.key_hash):
    raise InvalidApiKeyError(key_prefix)
```

#### Layer 3: Agent Allowlists (Trust Registry)

As stated in the AP2 specification, the current trust model uses **manually curated allowlists**:

```python
# From example/src/roles/shopping_agent/remote_agents.py:
# "This registry serves as the initial allowlist of remote agents
#  that the shopping agent trusts."

merchant_agent_client = PaymentRemoteA2aClient(
    name="merchant_agent",
    base_url="http://localhost:8001/a2a/merchant_agent",
    required_extensions={EXTENSION_URI},
)
```

Each participant maintains a list of trusted counterparts:
- The **shopping agent** has an allowlist of trusted merchants and credentials providers
- The **merchant** has an allowlist of trusted shopping agents (identified by API key, not by the user behind them)
- The **credentials provider** has an allowlist of trusted shopping agents

### You Are Correct: The Merchant Needs an ACL Independent of Users

Yes. A merchant's trust relationship is with **agents/services, not with individual users**. The merchant validates:

1. **Is this agent in my allowlist?** (agent-level trust via API key or A2A Agent Card)
2. **Does this agent's request contain valid user signatures?** (user-level authorization via mandate signatures)

These are two separate checks:

```
AGENT TRUST (Layer 3 - allowlist):
  "Is the agent calling me a legitimate shopping agent I recognize?"
  → Checked via API key, Agent Card, or mTLS certificate

USER AUTHORIZATION (mandate signatures):
  "Has the user behind this agent actually approved this cart?"
  → Checked via cryptographic signature on the mandate
```

A rogue agent that is not in the merchant's allowlist will be rejected at the connection level, regardless of what signatures it presents. A legitimate agent that presents tampered signatures will be rejected at the mandate verification level.

### Future Evolution

The AP2 specification plans to evolve from static allowlists to **dynamic trust establishment** using:
- Identity assertions built into A2A/MCP protocols
- DNS ownership verification
- mTLS with certificates issued by trusted authorities
- Real-time reputation and risk scoring

---

## 8. Signature Verification by the Auditor

### The Question

If signatures are created by encrypting a hash with a private key, how does the auditor verify them without the private key?

### The Answer: Public Key Cryptography

This is standard asymmetric cryptography. Each signer has a **key pair**: a private key (secret, used to sign) and a public key (shared, used to verify). The auditor only needs the **public key**, which is openly available.

#### For Merchant Signatures

The merchant's public keys are published at `/.well-known/ucp.json/keys` as JWK entries:

```json
{
  "keys": [{
    "kid": "merchant-demo-key-2026",
    "kty": "EC",
    "crv": "P-256",
    "x": "MKBCTNIcKUSDii11ySs3526iDZ8AiTo7Tu6KPAqv7D4",
    "y": "4Etl6SRW2YiLUrN5vfvVHuhp7x8PxltmWWlbbM4IFyM"
  }]
}
```

Verification flow:
1. Auditor fetches the merchant's public key from `/.well-known/ucp.json/keys`
2. Auditor takes the mandate content that was signed
3. Auditor uses the public key + the JWT signature + the content to verify mathematically that the signature was produced by the holder of the corresponding private key

#### For User Signatures (Production)

In production, user public keys would be:
- Registered with a **Credentials Provider** (digital wallet) during setup
- Included in the **Verifiable Digital Credential** alongside the signature
- Chained to a device attestation certificate (e.g., Android Key Attestation, Apple DeviceCheck)

The auditor can verify the signature using the public key embedded in or referenced by the VDC, and can verify the key's authenticity through the attestation chain.

#### In This PoC

This PoC uses SHA-256 hashes (not asymmetric encryption), so "verification" is simpler, the auditor checks that the signature field exists and matches the expected hash of the content. The auditor agent in `example/ucp_flow/auditor_agent/tools.py` checks structural presence:

```python
signature_checks = {
    "buyer_intent_signature": bool(intent_mandate.get("signatures")),
    "seller_cart_signature": bool(cart_mandate.get("signatures")),
    "buyer_payment_signature": bool(payment_mandate.get("signatures"))
}
all_signatures_valid = all(signature_checks.values())
```

In production, this would be replaced by full cryptographic verification using public keys.

---

## 9. Immutability and Idempotency

### How Immutability Is Ensured

The ledger enforces immutability through five mechanisms:

**A. Append-Only Architecture:** The API only exposes INSERT operations. No UPDATE or DELETE endpoints exist. Status changes create new versions; old versions are never modified.

**B. Blockchain-Style Hash Chaining:** Each version stores a SHA-256 hash of its content and a reference to the parent version's hash:

```python
class MandateLedgerEntry(BaseModel):
    parent_version: Optional[int]       # None for v1
    parent_version_hash: Optional[str]  # SHA-256 of parent's canonical JSON
    current_version_hash: str           # SHA-256 of this version's canonical JSON
```

Tampering with any version breaks the chain, since child hashes reference the parent hash.

**C. Optimistic Locking** : Concurrent writes are detected and retried with exponential backoff, preventing version chain corruption.

**D. State Machine** : The `core/state_machine.py` enforces unidirectional transitions. Terminal states (expired, cancelled, failed) have no outgoing transitions. States cannot move backwards.

**E. Consistency Verification** : The `ConsistencyService` scans the ledger for version gaps, broken chains, and hash mismatches.

### How Idempotency Is Ensured

Clients include an `X-Idempotency-Key` header on write requests. The server:

1. Checks if the key was already processed (lookup by key + agent ID in MongoDB)
2. If found, returns the cached response without re-processing
3. If not found, processes the request and stores the response
4. Records expire after 24 hours via MongoDB TTL indexes

The UCP checkout generates deterministic keys to prevent duplicate ledger writes during retries:

```python
await ledger_client.create_mandate(..., idempotency_key=f"intent_{checkout_id}")
await ledger_client.create_mandate(..., idempotency_key=f"cart_signed_{cart_id}")
await ledger_client.create_mandate(..., idempotency_key=f"payment_{payment_mandate_id}")
```

---

## 10. Compliance and Audit Trail

Every operation is logged in the `audit_logs` MongoDB collection, capturing event type, entity ID, actor ID and type, action details, timestamp, IP address, and transaction ID.

Key compliance features:

| Feature | Implementation |
|---------|---------------|
| **Audit trail** | Every mandate creation, status change, and signing generates an audit entry (`AuditRepository`) |
| **Authentication** | API keys (bcrypt-hashed, scoped, expirable, revokable) required on all endpoints |
| **RBAC** | Permission scopes (`mandate:read`, `mandate:write`, `audit:read`, `auth:manage`) |
| **Rate limiting** | Per-agent sliding window (default 60 req/min), HTTP 429 with standard headers |
| **Auditor agent** | Dedicated compliance role that verifies signatures, queries history, and tests immutability |
| **Financial records retention** | Append-only ledger means no records are ever deleted; complete authorization chain preserved via `transaction_id` |

---

## 11. Multi-Protocol Ecosystem: UCP, A2A, and MCP

> For how AP2 relates to A2A, MCP, UCP, and x402 at the protocol level, see [AP2 Summary § 10](./ap2-summary.md#10-how-ap2-relates-to-a2a-mcp-ucp-and-x402).

### How They Fit Together in Practice

| Protocol | Role | Analogy |
|----------|------|---------|
| **UCP** | Commerce semantics: discovery, checkout, orders | A shared shopping language |
| **A2A** | Agent-to-agent communication: tasks, messages, delegation | Phone calls between agents |
| **MCP** | Agent-to-tool connectivity: DB reads, API calls, functions | Power adapters for the LLM |
| **AP2** | Trust layer: signed mandates, audit trail, non-repudiation | Notarized receipts |

UCP supports all three as transport bindings. A merchant's `/.well-known/ucp.json` can declare REST, MCP, and A2A endpoints simultaneously, meaning any AI platform (ChatGPT via MCP, Gemini via A2A, custom agents via REST) can interact with the same merchant.

### Does Each Merchant Need an Agent?

UCP supports two models:

##### Model A: Merchant as a Server (UCP REST) — Used in `ucp_flow`

The merchant runs a **standard web server** (FastAPI, Express, etc.) that exposes UCP REST endpoints. No AI agent is required on the merchant side.

```
Shopper Agent (AI)  ──── REST ────►  Merchant Server (no AI)
                                     ├── /.well-known/ucp.json
                                     ├── /api/products
                                     └── /api/checkout
```

This is the simpler model. The merchant is a **conventional web service** that happens to speak UCP. This is what the `example/ucp_flow/merchant_server/` demonstrates.

##### Model B: Merchant as an Agent (A2A) — Used in `card_flow`

The merchant runs an **AI agent** that communicates with the shopper agent via the A2A protocol. Both sides have LLMs.

```
Shopper Agent (AI)  ──── A2A ────►  Merchant Agent (AI)
                                     ├── agent.json
                                     ├── Catalog sub-agent
                                     └── Payment processor agent
```

This is the richer model. The merchant agent can use AI reasoning for personalization, negotiation, and complex order handling. This is what `example/card_flow/` and `example/src/roles/merchant_agent/` demonstrate.

In summary:

| Model | Example in This Project | Merchant Side |
|-------|------------------------|--------------|
| **REST server** (no AI) | `example/ucp_flow/merchant_server/` | Standard FastAPI web server implementing UCP endpoints |
| **A2A agent** (with AI) | `example/card_flow/` + `example/src/roles/merchant_agent/` | ADK agent with LLM-powered reasoning |

In a Multi-Merchant Ecosystem not every merchant needs AI. Small merchants can run a UCP REST server; large merchants might add an A2A agent for personalization.

| Merchant | Implementation | Why |
|----------|---------------|-----|
| Amazon | UCP REST server + optional A2A agent | High volume, sophisticated catalog, REST for scale, AI agent for personalization |
| Small boutique | UCP REST server only | Simple catalog, no need for AI reasoning |
| AI-native startup | A2A agent only | Built entirely on agentic architecture |
| Legacy retailer | UCP REST adapter in front of existing e-commerce APIs | Bridges existing systems to UCP |

##### Who Is Responsible for Implementing Each Agent?

| Component | Responsible Party | What They Build |
|-----------|------------------|-----------------|
| **Shopper / Consumer Agent** | The **AI platform** (Google, OpenAI, Anthropic, etc.) | The user-facing shopping assistant with UCP client capabilities |
| **Merchant Agent / Server** | The **merchant** (Amazon, eBay, etc.) or their **e-commerce platform** (Shopify, WooCommerce, etc.) | UCP-compliant endpoints, product catalog, checkout logic |
| **Payment Processor Agent** | The **payment provider** (Stripe, Adyen, etc.) | Payment processing, tokenization, fraud detection |
| **Credentials Provider Agent** | The **wallet / identity provider** (Google Pay, Apple Pay, banks) | Secure credential storage, payment method selection |
| **Auditor / Compliance Agent** | The **merchant**, **regulator**, or **third-party auditor** | Transaction verification, compliance monitoring |
| **Mandate Ledger Service** | The **merchant** (self-hosted) or a **SaaS provider** | Immutable ledger infrastructure for AP2 mandates |

### How MCP Relates to UCP and A2A

These three protocols operate at **different layers** and are **complementary, not competing**:

```
┌───────────────────────────────────────────────────────┐
│                    AI AGENT                           │
│                                                       │
│  ┌──────────────────────────────────────────────────┐ │
│  │            LLM (Gemini, GPT, Claude)             │ │
│  └──────────┬──────────────┬───────────────┬────────┘ │
│             │              │               │          │
│       ┌─────▼─────┐  ┌─────▼─────┐  ┌──────▼──────┐   │
│       │   MCP     │  │   A2A     │  │   UCP       │   │
│       │           │  │           │  │             │   │
│       │ Tools &   │  │ Agent-to  │  │ Commerce    │   │
│       │ Data      │  │ -Agent    │  │ Semantics   │   │
│       │           │  │           │  │             │   │
│       │ • DB read │  │ • Delegate│  │ • Discover  │   │
│       │ • API call│  │ • Collab  │  │ • Checkout  │   │
│       │ • File IO │  │ • Handoff │  │ • Payment   │   │
│       └─────┬─────┘  └─────┬─────┘  └──────┬──────┘   │
│             │              │               │          │
└─────────────┼──────────────┼───────────────┼──────────┘
              │              │               │
              ▼              ▼               ▼
         Tools/APIs      Other Agents    Merchant Servers
```

#### MCP as a UCP Transport

The UCP specification explicitly supports **MCP as a transport layer**. A merchant can expose its UCP capabilities as MCP tools, meaning the LLM can call them directly through its native tool-calling interface:

```
UCP Capability                    →  MCP Tool
─────────────────────────────────────────────────
dev.ucp.shopping.checkout         →  create_checkout()
dev.ucp.shopping.product_search   →  search_products()
dev.ucp.shopping.order            →  get_order_status()
```

The UCP spec states: *"UCP capabilities map 1:1 to MCP tools"*, meaning every UCP capability can be exposed as an MCP tool that the LLM can call directly.

#### MCP in This Project

MCP appears as a transitive dependency via Google ADK (`google-adk → mcp`). The ADK uses MCP internally to manage tool registration for agents. The merchant server in this PoC uses pure REST. In production, merchants could additionally expose an MCP server where each UCP capability maps 1:1 to an MCP tool.

#### Would MCP Be Used Inside Each Agent?

**Yes**, MCP can be used **within** each agent to connect the LLM to its tools:

| Agent | MCP Usage |
|-------|-----------|
| **Shopping Agent** | MCP tools for: product search, checkout management, signature creation |
| **Merchant Agent** | MCP tools for: catalog queries, inventory checks, order management |
| **Auditor Agent** | MCP tools for: ledger queries, signature verification, integrity checks |
| **Credentials Provider** | MCP tools for: payment method retrieval, wallet access |

Each agent would have its own **MCP server** exposing the specific tools that agent needs. The LLM running inside that agent would call those tools through MCP's standardized interface.


#### Who Implements Each MCP Server?

MCP servers are implemented by **whoever owns the data or capability** being exposed:

| MCP Server | Implementer | Tools Exposed |
|------------|-------------|---------------|
| Merchant MCP | **Merchant** | `search_products()`, `create_checkout()`, `get_order()` |
| Payment MCP | **Payment provider** | `process_payment()`, `tokenize_card()` |
| Wallet MCP | **Wallet provider** | `get_payment_methods()`, `get_shipping_address()` |
| Ledger MCP | **Ledger operator** | `create_mandate()`, `get_audit_trail()` |



### Who Implements and Maintains What?

The agentic commerce ecosystem is maintained through a **layered governance model**, no single entity controls everything:

#### Protocol Governance

| Protocol | Governance | Steward |
|----------|-----------|---------|
| **UCP** | Open standard, developed by Google in collaboration with industry partners | Google + community (spec at [ucp.dev](https://ucp.dev)) |
| **A2A** | Open standard, originally developed by Google, donated to the Linux Foundation | Linux Foundation ([a2a-protocol.org](https://a2a-protocol.org)) |
| **MCP** | Open standard, created by Anthropic | Anthropic + community ([modelcontextprotocol.io](https://modelcontextprotocol.io)) |
| **AP2** | Payment protocol specification by Google | Google Agentic Commerce ([github.com/google-agentic-commerce](https://github.com/google-agentic-commerce)) |

#### Operational Responsibility

| Layer | Who Maintains It |
|-------|-----------------|
| **Protocol specifications** | Standards bodies and founding organizations (Google, Anthropic, Linux Foundation) |
| **AI platforms** | Platform operators (Google for Gemini, OpenAI for ChatGPT, Anthropic for Claude) |
| **Merchant implementations** | Each merchant independently (or their e-commerce platform vendor) |
| **Payment infrastructure** | Payment networks and processors (Visa, Mastercard, Stripe, etc.) |
| **Mandate ledger** | Each merchant or a SaaS ledger provider |
| **Merchant discovery/indexing** | Platform operators (Google Merchant Center, shopping indexes) |
| **Compliance & regulation** | Government regulators (FTC, EU, etc.) and industry standards bodies (PCI DSS) |

#### The Key Principle

**No single entity owns or controls the ecosystem.** Each participant is responsible for their own implementation:

- **Merchants** implement their own UCP servers/agents and are responsible for their product catalogs, pricing, and fulfillment
- **Platforms** implement consumer-facing agents and are responsible for user experience, privacy, and security
- **Protocol stewards** maintain the specifications and ensure backward compatibility
- **The community** contributes reference implementations, SDKs, and tooling

This is by design, just as the web works because anyone can create a website (HTTP) and anyone can build a browser, agentic commerce works because anyone can implement a UCP merchant and anyone can build a shopping agent. The **protocols are the shared contracts** that make interoperability possible.

---

## Summary

| Concern | Mechanism |
|---------|-----------|
| **Merchant Discovery** | `/.well-known/ucp.json` decentralized, per-domain |
| **Dual Signatures** | Both shopper and merchant sign; the cart carries nested signatures |
| **Non-Repudiation** | User's hardware-backed device key (production); agent-level hash (PoC) |
| **Transport Security** | TLS + API keys + agent allowlists (not mandate signatures) |
| **MITM Prevention** | TLS certificate verification + agent allowlist ACLs |
| **Signature Verification** | Public key cryptography, auditor uses published public keys |
| **Immutability** | Append-only inserts, hash chaining, state machine, no DELETE/UPDATE |
| **Idempotency** | `X-Idempotency-Key` header + MongoDB deduplication with TTL |
| **Compliance** | Audit logs, RBAC, consistency checks, auditor agent, financial retention |
| **Multi-Protocol** | UCP for commerce, A2A for agent-agent, MCP for agent-tools, AP2 for trust |

## References
- [AP2 Protocol Summary](AP2_Protocol_Summary.md) detailed protocol theory, actors, workflows, security deep dive, ecosystem
- [MongoDB: Mandate Ledger Service - AP2 Payment Flow Demo](https://github.com/mongodb-partners/aifac-mandate-ledger-service-AP2/tree/main)
- [Understanding UCP + AP2 Integration](https://github.com/mongodb-partners/aifac-mandate-ledger-service-AP2/blob/main/docs/UCP_AP2_INTEGRATION.md)
- [UCP Specification](https://ucp.dev)
- [A2A Protocol](https://a2a-protocol.org)
- [MCP Protocol](https://modelcontextprotocol.io)
