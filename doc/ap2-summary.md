# Agent Payments Protocol (AP2) - Complete Summary

## Table of Contents

1. [Glossary of Acronyms](#1-glossary-of-acronyms)
2. [What is AP2? (The Simple Version)](#2-what-is-ap2-the-simple-version)
3. [Why Does AP2 Exist? The Problem It Solves](#3-why-does-ap2-exist-the-problem-it-solves)
4. [The USP (Unique Selling Proposition)](#4-the-usp-unique-selling-proposition)
5. [The Actors: Who Participates](#5-the-actors-who-participates)
6. [Architectural Overview](#6-architectural-overview)
7. [The Trust Anchors: Verifiable Digital Credentials](#7-the-trust-anchors-verifiable-digital-credentials)
8. [Core Workflows](#8-core-workflows)
9. [Security Deep Dive](#9-security-deep-dive)
10. [How AP2 Relates to A2A, MCP, UCP and x402](#10-how-ap2-relates-to-a2a-mcp-ucp-and-x402)
11. [Dispute Resolution](#11-dispute-resolution)
12. [Ecosystem and Partners](#12-ecosystem-and-partners)
13. [Roadmap](#13-roadmap)

---

## 1. Glossary of Acronyms

Before diving in, here is every acronym you will encounter, explained simply:

| Acronym | Full Name | Plain English |
|---------|-----------|---------------|
| **AP2** | Agent Payments Protocol | The open protocol this project defines. It standardizes how AI agents make payments securely. |
| **A2A** | Agent-to-Agent Protocol | An open standard for AI agents to talk to each other (tasks, messages). AP2 extends it. |
| **MCP** | Model Context Protocol | A standard for AI models to connect to external tools, APIs, and data sources. |
| **UCP** | Unified Checkout Protocol | A checkout protocol fully compatible with AP2; it implements AP2's mandates in its own checkout flow. |
| **VDC** | Verifiable Digital Credential | A cryptographically signed, tamper-proof data object used to prove identity, intent, or authorization. |
| **VP** | Verifiable Presentation | A presentation of one or more VDCs with cryptographic proof that the holder intended to share them. |
| **UA** | User Agent | The AI surface the user talks to (e.g., Gemini, ChatGPT). |
| **SA** | Shopping Agent | A specialized AI agent that handles the shopping task (finding products, building carts, etc.). |
| **CP** | Credentials Provider | A secure entity (like a digital wallet) that manages the user's payment methods and identity. |
| **ME / RE** | Merchant Endpoint / Remote Endpoint | The web interface or AI agent representing the seller. |
| **MPP** | Merchant Payment Processor | The entity that builds and sends the payment authorization message to the payment network. |
| **SCA** | Strong Customer Authentication | A regulatory requirement for secure online identification (e.g., biometrics, 2FA). |
| **PCI** | Payment Card Industry | The industry standard for protecting card data. |
| **PII** | Personally Identifiable Information | Any data that could identify a specific person (name, email, address, etc.). |
| **PSP** | Payment Service Provider | A company that processes payments for merchants (e.g., Stripe, Adyen). |
| **3DS / 3DS2** | 3D Secure (version 2) | A security protocol for authenticating online card payments (the pop-up that asks for a code). |
| **TTL** | Time-to-Live | An expiration time; how long a mandate remains valid. |
| **SKU** | Stock Keeping Unit | A unique identifier for a specific product. |
| **DPC** | Digital Payment Credentials | A cryptographic approach to payment credentials. |
| **ADK** | Agent Development Kit | Google's toolkit for building AI agents. |
| **x402** | x402 Payment Standard | A standard for digital currency payments (stablecoins, crypto). AP2 supports it. |
| **OTP** | One-Time Passcode | A single-use code sent to verify identity (e.g., SMS code). |
| **mTLS** | Mutual TLS | A security protocol where both client and server authenticate each other. |
| **ATO** | Account Takeover | When a fraudster gains control of a legitimate user's account. |

---

## 2. What is AP2? (The Simple Version)

Imagine you ask an AI assistant: *"Buy me those red shoes from Nike when they drop below $100."*

Today, no standard exists that lets your AI agent securely pay on your behalf. Current payment systems were built for *humans clicking buttons on websites* -- not for autonomous AI agents acting on your behalf.

**AP2 is an open protocol that solves this.** It defines how AI agents can:
- Prove they have your permission to buy something
- Securely handle your payment information
- Create tamper-proof receipts of what was agreed
- Give merchants confidence the order is legitimate
- Give banks visibility into AI-driven transactions

Think of AP2 as the **"rules of the road" for AI agents making purchases**. Just like HTTPS made web browsing secure, AP2 makes AI shopping secure.

---

## 3. Why Does AP2 Exist? The Problem It Solves

### The Trust Gap

When a human buys something online, the trust model is clear: you see the product, you enter your card, you click "Pay." Everyone knows who authorized it.

When an AI agent does it, fundamental questions arise:

- **Who authorized this?** How does the merchant know the agent has your permission?
- **Is this what the user wanted?** What if the AI misunderstood or "hallucinated"?
- **Who is responsible if something goes wrong?** The user? The agent developer? The merchant?

### The Fragmentation Risk

Without a common standard, every company would build its own proprietary system. This would mean:
- Your AI agent only works with some merchants
- Small businesses can't afford to integrate with dozens of different agent systems
- Banks can't consistently assess fraud risk across different agent platforms

AP2 prevents this by being **open, interoperable, and payment-method agnostic**.

---

## 4. The USP (Unique Selling Proposition)

AP2's core differentiator can be summarized in one phrase: **"Verifiable Intent, Not Inferred Action."**

Here is what makes AP2 unique compared to any other approach:

1. **Cryptographic Proof of Intent**: Every transaction is backed by a user-signed, tamper-proof digital mandate. This is not the AI *guessing* what you want -- it is you *proving* what you authorized, with a hardware-backed cryptographic signature.

2. **Role-Based Privacy Architecture**: The Shopping Agent never sees your credit card number. The Merchant never sees your full conversation. Each actor only gets the data they need. Sensitive PCI/PII data is handled exclusively by the Credentials Provider.

3. **Payment-Method Agnostic**: Works with credit cards, debit cards, digital wallets, bank transfers, and even crypto/stablecoins (via x402). Designed to accommodate any future payment method.

4. **Extends Existing Standards**: AP2 does not reinvent communication -- it adds a payment layer on top of A2A (agent-to-agent communication) and MCP (agent-to-tool communication). This makes adoption incremental.

5. **Backward Compatible with Existing Payment Infrastructure**: Existing fraud systems, 3DS challenges, and dispute processes continue to work. AP2 enhances them with additional signals, not replaces them.

6. **Open and Non-Proprietary**: Created by Google, Apache 2.0 licensed, with 100+ industry partners (Mastercard, Visa, PayPal, Shopify, Coinbase, and many more). Any framework, any runtime can implement it.

---

## 5. The Actors: Who Participates

AP2 defines six key roles. Think of them as characters in a play, each with a specific job:

```
+------------------+
|     THE USER     |  The human. You. The one who says "buy me shoes."
+--------+---------+
         |
         v
+--------+---------+
| SHOPPING AGENT   |  Your AI assistant. Finds products, builds the cart,
| (SA / UA)        |  gets your approval. Never sees your card number.
+--------+---------+
         |
    +----+----+
    |         |
    v         v
+---+----+ +--+-------------------+
| CRED.  | | MERCHANT ENDPOINT    |  The store's AI agent or website.
| PROV.  | | (ME)                 |  Shows products, negotiates the cart,
| (CP)   | +----------+-----------+  signs the cart to commit to fulfilling it.
+---+----+            |
    |                 v
    |      +----------+-----------+
    |      | MERCHANT PAYMENT     |  Builds the actual payment authorization
    |      | PROCESSOR (MPP)      |  message for the payment network.
    |      +----------+-----------+
    |                 |
    +--------+--------+
             v
    +--------+---------+
    | NETWORK & ISSUER |  Visa, Mastercard, your bank. Approves or
    +------------------+  declines the transaction.
```

### Key insight: Separation of Concerns

- The **Shopping Agent** handles product discovery and cart building, but NEVER touches payment credentials.
- The **Credentials Provider** manages payment methods securely, but doesn't know what you're buying in detail.
- The **Merchant** commits to fulfilling the order by signing the cart, but doesn't see your full conversation with the agent.

This separation is a core security feature.

---

## 6. Architectural Overview

### Layer Cake: How the Protocols Stack

```
+-----------------------------------------------+
|                   AP2 LAYER                   |  Payment mandates, VDCs,
|          (Agent Payments Protocol)            |  cart/intent/payment contracts
+-----------------------------------------------+
|            A2A LAYER           |   MCP LAYER  |
|    (Agent-to-Agent comms)      | (Agent-to-   |
|    Tasks, messages between     |  Tool comms) |
|    Shopping Agent, Merchant,   | APIs, data   |
|    Credentials Provider        | sources      |
+-----------------------------------------------+
|              TRANSPORT LAYER                  |
|         HTTPS, DNS, mTLS, OAuth2              |
+-----------------------------------------------+
```

- **A2A** is how agents talk to each other (tasks and messages)
- **MCP** is how agents talk to tools and APIs
- **AP2** adds the payment-specific vocabulary on top: mandates, payment requests, receipts

### The Flow of Trust

**Short term** (now): Trust is established through manually curated allow-lists.
- Shopping Agents maintain a list of trusted Credentials Providers
- Credentials Providers maintain a list of trusted Shopping Agents
- Merchants maintain a list of trusted Shopping Agents (and vice versa)

**Long term** (future): Real-time trust establishment using identity assertions built into A2A/MCP, leveraging HTTPS, DNS ownership, mTLS, and API key-exchange.

---

## 7. The Trust Anchors: Verifiable Digital Credentials

This is the heart of AP2's security model. VDCs are **cryptographically signed, tamper-proof JSON objects** that prove what was agreed.

There are three types:

### 7.1 Cart Mandate (Used when the user IS present)

Think of it as a **digital receipt signed before you pay**. It contains:
- Who is buying and who is selling (verified identities)
- Exactly what is being purchased (SKUs, quantities, prices)
- The total amount and currency
- The specific payment method (as a token, not raw card data)
- The shipping destination
- Risk signals for fraud assessment
- The merchant's signature (they commit to fulfilling this cart)
- The user's signature (created via biometric/device key authentication)

### 7.2 Intent Mandate (Used when the user is NOT present)

Think of it as **signed instructions left for your agent**. Used in scenarios like "buy me tickets when they go on sale." It contains:
- What the user wants (natural language description)
- Budget constraints and preferences
- Authorized payment methods (categories, not specific tokens)
- An expiration time (TTL)
- The user's cryptographic signature

### 7.3 Payment Mandate (Sent to the payment network)

Think of it as a **signal to your bank that an AI agent is involved**. It contains:
- AI agent presence indicator
- Transaction modality (Human Present vs Human Not Present)
- Reference to the Cart or Intent Mandate
- Payment token and transaction details

### How They Work Together

```
User signs Intent Mandate
        |
        v
Agent shops on behalf of user
        |
        v
Merchant creates Cart Mandate and signs it
        |
        v
User reviews and signs Cart Mandate (if present)
        |
        v
Shopping Agent creates Payment Mandate
        |
        v
Payment Mandate sent to bank/network along with payment authorization
```

---

## 8. Core Workflows

### 8.1 Human Present Transaction (Step by Step)

This is the most common flow: you ask your AI agent to buy something, and you're there to approve the final purchase.

```
Step 1: SETUP
   You connect your Shopping Agent to your Credentials Provider (e.g., your digital wallet).

Step 2: DISCOVERY & NEGOTIATION
   You say: "Find me red Nike Air Max shoes under $150."
   Your Shopping Agent talks to one or more Merchant Agents, compares options,
   and assembles a cart.

Step 3: MERCHANT VALIDATES CART
   The Merchant Agent creates a CartMandate and the Merchant entity signs it.
   This is the merchant's commitment: "I will deliver these items at this price."

Step 4: GET PAYMENT METHODS
   The Shopping Agent asks your Credentials Provider for eligible payment methods
   (credit card, debit card, wallet, etc.). The CP returns tokenized references --
   the Shopping Agent never sees your actual card number.

Step 5: SHOW CART TO USER
   Your Shopping Agent shows you the final cart:
   "Nike Air Max 90 - $120.00 | Pay with Visa ending 4242 | Ship to your home"

Step 6: SIGN & PAY
   You approve via biometric authentication (fingerprint, face, etc.) on your device.
   This creates a cryptographically signed Cart Mandate -- proof you authorized
   this exact purchase. A Payment Mandate is also prepared.

Step 7: PAYMENT EXECUTION
   The Shopping Agent sends the signed mandates to the Merchant and Credentials Provider.
   The Merchant's Payment Processor (MPP) constructs the authorization message.

Step 8: SEND TO ISSUER
   The MPP sends the transaction to the payment network (Visa, Mastercard, etc.)
   with the Payment Mandate attached, giving the bank visibility into the
   AI-driven nature of the transaction.

Step 9: CHALLENGE (if needed)
   Any party can challenge the transaction (e.g., 3DS verification, OTP).
   You complete the challenge on a trusted surface (your banking app).

Step 10: AUTHORIZATION
   The bank approves the payment. Confirmation is sent back through the chain.
   You see: "Purchase complete! Your Nike Air Max 90 will arrive by Friday."
```

### 8.2 Human Not Present Transaction (Step by Step)

This flow is for autonomous purchases: "Buy these shoes when the price drops below $100."

```
Step 1: CAPTURE INTENT
   You say: "Buy 2 tickets to this concert when they go on sale. Budget: $1000.
   I want seats close to the main stage."

Step 2: AGENT CONFIRMS UNDERSTANDING
   Your Shopping Agent repeats back: "I understand you want 2 concert tickets,
   close to the main stage, budget $1000."

Step 3: SIGN INTENT MANDATE
   You approve via biometric auth. This creates a signed Intent Mandate --
   proof you authorized this autonomous purchase within these constraints.

Step 4: AGENT WATCHES AND ACTS
   When tickets become available, your agent contacts the Merchant Agent
   and shares the Intent Mandate.

Step 5: MERCHANT DECISION
   The Merchant can:
   a) FULFILL directly: "I have tickets matching these criteria. Here's the cart."
   b) REQUEST CLARIFICATION: "I have 3 seating options. The user must choose."
      -> If (b), you get notified and brought back to confirm (creating a Cart Mandate).

Step 6: PAYMENT PROCEEDS
   The rest follows the same pattern as the Human Present flow (Steps 6-10 above),
   but with the Intent Mandate as additional evidence.
```

### 8.3 Payment Method Addition

If you don't have an eligible payment method:
- The Credentials Provider tells the Shopping Agent
- The Shopping Agent guides you to set up a payment method
- This may require a tokenization flow on a trusted payments surface

### 8.4 Transaction Challenges

Any party can challenge a transaction at any time:
- Issuers can trigger 3DS2 authentication
- Merchants can require additional verification
- Credentials Providers can request step-up authentication
- The user is redirected to a trusted surface to complete the challenge
- The challenge result is shared with all relevant parties to avoid double-challenging

---

## 9. Security Deep Dive

### 9.1 Security Principles

AP2's security model is built on four pillars:

**Pillar 1: User Control and Privacy by Design**
- The user is ALWAYS the ultimate authority
- Agents cannot make purchases without cryptographic user authorization
- Sensitive data (PCI, PII) is never exposed to Shopping Agents
- Payload encryption ensures only authorized parties see sensitive data

**Pillar 2: Role-Based Data Isolation**
- Shopping Agents handle product discovery -- they never see card numbers
- Credentials Providers manage payment data -- they don't see the full conversation
- Merchants commit to fulfillment -- they don't access raw payment credentials directly
- Each actor has minimum necessary access (principle of least privilege)

**Pillar 3: Cryptographic Non-Repudiation**
- Every mandate is signed with a hardware-backed key on the user's device
- Signatures are tamper-evident: any change invalidates the signature
- Merchant signatures commit them to fulfilling specific terms
- The chain of signatures creates an immutable audit trail

**Pillar 4: Backward Compatibility**
- Existing fraud detection systems continue to work
- 3DS2, OTP, and other challenge mechanisms are fully supported
- Payment networks receive additional AI-specific signals to enhance their risk models
- No existing security measure is bypassed or weakened

### 9.2 How AP2 Handles Specific Threats

| Threat | How AP2 Mitigates It |
|--------|---------------------|
| **Agent Hallucination** (AI makes wrong purchase) | Cart Mandate requires explicit user signature on exact items. Intent Mandate captures constraints. Merchant can force user confirmation if intent is ambiguous. |
| **First-Party Fraud** (user claims "I didn't authorize this") | User-signed VDC with hardware-backed cryptographic proof. Non-repudiable. |
| **Man-in-the-Middle Attack** (attacker alters transaction) | All mandates are cryptographically signed. Any tampering invalidates signatures. |
| **Account Takeover** (fraudster controls user's account) | Authentication signals during mandate signing provide evidence. Device-key binding makes remote exploitation harder. |
| **Agent Impersonation** (fake agent pretends to be legitimate) | Trust registries (short-term). Identity verification via A2A/MCP (long-term). |
| **PCI Data Leakage** (card numbers exposed to agents) | Role-based architecture ensures Shopping Agents never see raw card data. Only the CP handles payment credentials. |
| **Unauthorized Autonomous Purchase** (agent exceeds its authority) | Intent Mandate has explicit constraints (budget, TTL, product categories). Violations are detectable by comparing mandate vs. actual transaction. |
| **Replay Attacks** (reusing a valid mandate for another purchase) | Mandates contain unique IDs, timestamps, and specific transaction details. TTL ensures expiration. |

### 9.3 The Cryptographic Chain of Trust

```
[User's Device Key]
       |
       | signs
       v
[Cart Mandate / Intent Mandate]  <--- Contains: items, price, merchant, payment method
       |
       | includes
       v
[Merchant Signature]  <--- Merchant commits to fulfilling these exact terms
       |
       | generates
       v
[Payment Mandate]  <--- Sent to payment network with AI agent signals
       |
       | verified by
       v
[Payment Network / Issuer]  <--- Can verify all signatures, assess risk, approve/deny
```

Each link in this chain is cryptographically verifiable. If any party tampers with any data, the signatures break and the fraud is detected.

### 9.4 What Happens Today vs. What's Coming

**Today (v0.1):**
- Trust via manually curated allow-lists of agents/merchants/CPs
- Support for human-present "pull" payments (cards)
- Risk field in JSON exchanges (intentionally open-ended for industry to define)
- Standard challenge flows (3DS2, OTP) supported

**Future (v1.x and beyond):**
- Real-time trust establishment via identity assertions in A2A/MCP
- Support for human-not-present and push payments
- Trusted public key infrastructure (keys issued by banks, networks, governments)
- Delegated authorization with granular, time-bound access controls

---

## 10. How AP2 Relates to A2A, MCP, UCP and x402

### Simple Disambiguation

- **MCP**: Agents talk to data/tools (APIs)
- **A2A**: Agents talk to other agents (tasks and messages)
- **AP2**: Agents talk about payments (mandates)
- **UCP**: A checkout protocol that implements AP2's mandates in its flow
- **x402**: A payment method standard for digital currencies that AP2 supports

### AP2 + A2A

AP2 is a formal A2A extension. When agents use A2A to communicate, they can include AP2-specific data (mandates) as DataParts in A2A Messages and Artifacts. Agent Cards declare AP2 support and specify roles (merchant, shopper, credentials-provider, payment-processor).

### AP2 + MCP

MCP allows agents to connect to tools and APIs. AP2 is building MCP servers so that agents can interact with payment providers through standardized tool interfaces. An agent using MCP can invoke payment tools that produce AP2-compliant mandates.

### AP2 + UCP

UCP is fully AP2-compliant. UCP's Checkout Object is equivalent to AP2's Cart Mandate. When a checkout is completed in UCP, it produces both a CheckoutMandate (for the merchant) and a PaymentMandate (for the payment network) -- exactly as AP2 requires.

### AP2 + x402

x402 is a standard for digital currency payments (stablecoins, crypto). AP2 is payment-method agnostic by design, so x402 is simply one of many payment methods AP2 can accommodate. Shared implementations already exist at `google-agentic-commerce/a2a-x402`.

---

## 11. Dispute Resolution

AP2 is designed to make disputes resolvable with evidence, not guesswork.

### Principles
1. Stay close to existing dispute processes (especially card network flows)
2. Use the cryptographic chain of evidence as non-repudiable proof
3. Accountability lands on a real-world entity (user, merchant, or issuer) -- not on the AI agent, unless the AI made a provably wrong decision

### How It Works

When a dispute arises, the network adjudicator can receive:
- The user-signed Cart Mandate or Intent Mandate
- The merchant-signed Cart
- The Payment Mandate
- All standard existing dispute evidence

The adjudicator can then verify signatures and determine:
- Did the user approve this exact cart? (check Cart Mandate signature)
- Did the merchant commit to this fulfillment? (check Merchant signature)
- Did the agent act within the user's stated constraints? (compare Intent Mandate vs actual transaction)

### Common Dispute Scenarios

| Scenario | Evidence | Likely Outcome |
|----------|----------|----------------|
| User claims fraud but actually authorized it | User-signed Cart Mandate proves authorization | User is accountable |
| Agent picked wrong item, user approved cart | Cart Mandate shows user signed off on the wrong item | Shared accountability (user approved it) |
| Agent bought outside user's constraints | Intent Mandate vs transaction shows discrepancy | Agent developer may be accountable |
| Merchant didn't deliver | Valid mandates + payment confirmed, no fulfillment proof | Merchant is accountable |
| Account takeover | Analysis of authentication signals during signing | Depends on authentication evidence |

---

## 12. Ecosystem and Partners

AP2 has over **130 industry partners** spanning payments, commerce, identity, crypto, and technology. Notable names include:

- **Card Networks**: Mastercard, American Express, JCB, China UnionPay
- **Payment Processors**: PayPal, Adyen, Stripe (via Checkout.com), Worldpay, Fiserv, Global Payments
- **Commerce**: Shopify, Walmart, Etsy, Booking.com, Alibaba, Shopee, Wayfair
- **BNPL/Fintech**: Klarna, Affirm, Revolut, Plaid, Block
- **Web3/Crypto**: Coinbase, MetaMask, Ethereum Foundation, Solana, Polygon, Binance
- **Identity**: Okta, Auth0, 1Password, Ping Identity
- **Consulting**: Accenture, Deloitte, PwC
- **Tech**: Adobe, Cloudflare, Dell, Red Hat, Salesforce, ServiceNow

The project is open source under Apache 2.0 license, created by Google.

---

## 13. Roadmap

| Phase | Timeline | Key Features |
|-------|----------|-------------|
| **v0.1** | Sept 2025 | Core architecture, pull payments (cards), human-present flows, VDC framework, A2A reference implementation, step-up challenges |
| **v1.x** | TBD | Push payments (bank transfers, wallets), recurring payments, human-not-present flows, MCP implementations |
| **Long-term** | TBD | Multi-merchant transactions, real-time agent-to-agent negotiations, advanced trust infrastructure |

### Current deliverables in progress:
- AP2 specifications v0.1 (done)
- AP2 A2A extension v0.1 (in progress)
- AP2 MCP server v0.1 (in progress)
- AP2 Python SDK v0.1 (in progress)
- AP2 Android SDK v0.1 (in progress)

---

## Summary: Why AP2 Matters

AP2 solves the fundamental problem of trust in AI-driven commerce. By introducing cryptographically signed mandates (VDCs), a role-based privacy architecture, and backward compatibility with existing payment infrastructure, it creates a world where:

- **Users** can confidently delegate purchases to AI agents
- **Merchants** can accept AI-initiated orders with clear accountability
- **Banks and networks** get visibility into AI transactions and can assess risk
- **Developers** can build payment-capable agents on any framework
- **The ecosystem** avoids fragmentation through a common, open standard

The protocol's USP -- "Verifiable Intent, Not Inferred Action" -- ensures that every AI-driven transaction is backed by real, provable human authorization, not just an AI's interpretation of what the user wanted.

## References
- [GitHub: Agent Payments Protocol (AP2)](https://github.com/google-agentic-commerce/AP2)
- [UCP Translates AP2 Requirements into Reality](https://ap2-protocol.org/topics/ap2-and-ucp/)
- [Under the Hood: Universal Commerce Protocol (UCP)](https://developers.googleblog.com/under-the-hood-universal-commerce-protocol-ucp/)
- [What is AP2?](https://ap2-protocol.org/)
- [A2A: The Agent2Agent Protocol](https://learn.deeplearning.ai/courses/a2a-the-agent2agent-protocol/information)