# Federated Pharmacovigilance on Nextdata — A Deep Understanding

This is the document to internalise before you demo. It is organised as four
passes over the same system, each at a different altitude: what it *does*
(functional), how it is *built* (architectural), what is *non-obvious about it*
(conceptual, including the AI/LLM mechanics), and finally how to *show and
explain it* (queries + code flow). Read it top to bottom once; after that it is
a reference.

A note on framing for yourself: this is not "a chatbot that queries a database."
It is a demonstration that three independently-governed data products can have a
metric computed *across* them, on demand, by a language model, without any of the
underlying raw data ever leaving the domain that owns it. Almost everything
interesting follows from that one sentence.

---

## PART 1 — THE FUNCTIONAL STORY

### 1.1 The problem that justifies the whole thing

In a real pharma company, two facts are simultaneously true:

- The **adverse-event counts** live with the Pharmacovigilance / Drug Safety
  team. They are the numerator of any safety signal.
- The **prescription volume** lives with Commercial Analytics. It is the
  denominator — the exposure base.

The metric that actually matters for safety surveillance — the *adverse-event
reporting rate per 1,000 prescriptions* — requires both. And the two teams, by
design and often by regulation, do not hand each other their raw datasets.
Commercial does not get patient-level safety data; Safety does not get the
commercial book. So the single most important number in the domain is one that
**no single team can compute**, because each owns exactly one half of the
fraction.

This is the crux. The demo is not impressive because it joins two tables. It is
impressive because it computes a number that is *organisationally impossible* to
compute under the normal data-sharing rules, and does it without breaking those
rules.

### 1.2 Why raw counts actively mislead (the analytical payload)

The headline insight of the demo is a **rank inversion**. Look at 2025-Q3:

- NEURVANTA in North America has **605 adverse events** — by far the most of any
  product anywhere. By raw count it looks like the most dangerous drug in the
  portfolio.
- But it also has **205,000 prescriptions**. Its rate is **3.0 per 1,000 Rx** —
  the *safest* product per unit of exposure.
- IMMUNADEX in Europe has only **59 adverse events** — almost nothing by raw
  count. But against just **1,800 prescriptions** its rate is **32.8 per 1,000
  Rx** — over ten times NEURVANTA's. That is the real signal.

The raw-count ranking and the rate ranking are nearly *reversed*. This is not a
contrived demo artifact; it is the actual reason pharmacovigilance works in rates
and not counts. A high-volume drug accumulates raw events simply by being
prescribed a lot. Signal detection is about disproportionality relative to
exposure. The demo makes a real epidemiological principle visible in one table.

This matters for how you present: the "wow" is not the technology, it is that the
technology surfaces a *correct and counter-intuitive clinical conclusion* that
the raw data hides.

### 1.3 The three secondary stories

Once the headline lands, three follow-ups deepen it:

- **Emerging signal (trend):** IMMUNADEX in North America runs 20.0 → 25.0 → 30.0
  per 1,000 Rx across Q1–Q3. A rising rate on a *growing* prescription base is the
  textbook definition of an emerging safety signal — exactly what a PV team
  escalates.
- **Regional disproportionality:** VELORIN's rate in Europe (~15.6) is roughly
  3× its North America rate (~4.9), and the *serious*-event rate shows the same
  3× gap (6.2 vs 1.7). Same drug, same quarter — a regional difference that would
  trigger a region-specific investigation, invisible in raw counts.
- **The governance-narrative question:** "NEURVANTA has the most adverse events,
  is it our most dangerous drug?" The answer — no, it is the safest per
  prescription — is the entire thesis of the demo compressed into one exchange.

### 1.4 Where the language model fits

The LLM is not analysing anything statistically. Its job is **translation and
composition**: turn a business question in English into a correct federated SQL
statement, run it through a governed tool, and narrate the result. The
intelligence on display is that a non-technical user can ask "is NEURVANTA our
most dangerous drug?" and the system (a) knows which two governed tables to
touch, (b) writes the correct normalised SQL, (c) executes it where the data
lives, and (d) explains why the raw-count intuition is wrong. No analyst, no
pre-built dashboard, no data movement.

---

## PART 2 — THE ARCHITECTURE

### 2.1 The topology: three data products, two roles

```
   drug-safety-signals              commercial-prescriptions
   (source-aligned domain)          (source-aligned domain)
   schema: drug_safety_signals      schema: commercial_prescriptions
   table:  adverse_event_summary    table:  prescription_volume
   = the NUMERATOR                  = the DENOMINATOR
            \                              /
             \                            /
              \                          /
            pharma-pv-federation  (consumer-aligned / orchestrator)
            schema: pharma_pv_federation
            - Snowflake output:  pv_registry   (the credential anchor)
            - RPC/MCP output:    get_metadata, execute_federated_query
```

This maps cleanly onto data-mesh domain taxonomy. The two source-aligned products
each own and publish one governed fact table. The third is a **consumer-aligned
(aggregate) data product** — it exists to serve a cross-domain consumption use
case and owns no source data of its own. That distinction is worth stating
explicitly in the demo, because it is *why* the design is a mesh design and not
just "three schemas in one database."

### 2.2 The orchestrator's split personality

The orchestrator is two things wearing one manifest:

1. **A data product** with a Snowflake output port that materialises a tiny table
   called `pv_registry`.
2. **An MCP server** with a second output port (`mcp-api`) that exposes two
   callable tools.

The non-obvious part is the *relationship* between these two. The `pv_registry`
table looks like it exists to record which tables are federated (it stores the
two fully-qualified table names, the join keys, and a safety row count). That is
its cover story. Its **real** job is to be a Snowflake output port at all —
because declaring a Snowflake output is what causes the platform to **inject
Snowflake credentials into the runtime context** of the MCP tools. Without a
Snowflake output port, the `get_metadata` and `execute_federated_query` functions
would receive no `snowflake` object and would have nothing to authenticate with.

So `pv_registry` is, architecturally, a **credential anchor disguised as a
registry**. If you removed it, the demo's tools would lose their database
connection. This is the single most counter-intuitive structural fact in the
whole build, and it is worth understanding deeply because it is the kind of thing
that is invisible until it breaks.

### 2.3 The credential-injection contract (the "snowflake" port name)

There is an exact-string contract: the Snowflake output port must be named
**`snowflake`**. Not `snowflake-output`, not `sf`. The platform keys credential
injection off that port name. A mis-named port produces a data product that
deploys, passes health checks, and writes its table perfectly — and then the MCP
tools silently receive no credentials. This is the kind of failure that wastes a
day because nothing *errors*; it just doesn't work. (We hit exactly this class of
issue on the sales build; see Part 6.)

### 2.4 The borrowed SQL executor (cross-schema MCP server reuse)

Here is the part most people get wrong conceptually. Snowflake's server-side SQL
execution object — `SQL_EXEC_MCP_SRVR` — lives in **one** schema:
`ACCOUNT_COVERAGE`. It was created there during an earlier phase of the partner
environment. The pharma orchestrator's own schema (`pharma_pv_federation`) has no
such object.

The tools therefore do **not** use their own schema's executor (there isn't one).
They hard-code the executor's home as `ACCOUNT_COVERAGE` in the REST URL:

```
.../api/v2/databases/PARTNER_AZ_DB/schemas/ACCOUNT_COVERAGE/mcp-servers/SQL_EXEC_MCP_SRVR
```

This works for one reason that you must be able to articulate: the orchestrator
**runs as the same Snowflake role** (`PARTNER_AZ_ROLE`) as the account-coverage
product that created the executor, so it already holds USAGE on that object. And
because every SQL statement the tool sends uses **fully-qualified table names**
(`PARTNER_AZ_DB.drug_safety_signals.adverse_event_summary`), the executor's own
home schema is irrelevant to *what* it can query. The executor is just a
SQL-execution endpoint; the role's grants decide what it can see, and the
fully-qualified names decide what it touches.

The mental model to carry: **the MCP server's schema location and the data's
schema location are completely decoupled.** One is "where the engine sits," the
other is "where the fuel is." A single executor, reached cross-schema, drives
queries against any schema the role can read.

### 2.5 The full request path (every hop is a potential failure point)

When a user asks a question in Claude Desktop, the call traverses:

```
Claude Desktop
  -> nxd-partner MCP gateway (the "proxy")          [hop 1: discovery + routing]
    -> pharma-pv-federation pod, mcp-api port        [hop 2: your function runs here]
      -> Snowflake REST: /session/v1/login-request   [hop 3: authenticate]
      -> Snowflake REST: MCP initialize + tools/call  [hop 4: drive SQL_EXEC_MCP_SRVR]
        -> SQL_EXEC_MCP_SRVR executes the SQL          [hop 5: actual query]
```

Each hop has its own session lifecycle and timeout. The reason this matters: when
something "times out," *which* hop timed out tells you something completely
different. A hang at hop 4 (Snowflake calls outlasting the proxy's patience at
hop 1) looks identical from the user's seat to a transport failure at hop 2 — but
the fix is the opposite. Understanding the hop structure is what turned the
sales-build debugging from guesswork into diagnosis (Part 6).

### 2.6 Discovery vs. liveness (two different "is it there?" questions)

There are two independent registries and they lag each other:

- **The proxy's `connected_data_products`** — the live truth. If your DP is in
  this list, the gateway can route to it *now*.
- **The `tool_search` vector index** — a searchable embedding index that ingests
  data products asynchronously. This is what surfaces the tool with its hash
  suffix (e.g. `get_metadata__h2b3ufmbyu`).

A brand-new DP is in the first list immediately but absent from the second for a
while (cold-start lag). That gap is purely a *discoverability* problem, not a
*functionality* problem — the tool works the moment it is connected; it just is
not yet findable by semantic search. A client restart forces a fresh `tools/list`
which pulls it into the searchable set. Knowing these are two separate systems
saves you from "redeploying" something that was never broken.

---

## PART 3 — THE CONCEPTUAL LAYER (the non-obvious, much of it AI-specific)

This is the section with the things you are least likely to have from elsewhere.

### 3.1 The get_metadata → execute_federated_query handshake is schema-level RAG

The mandatory "call `get_metadata` first" pattern is **retrieval-augmented
generation applied to schema**. A language model does not know your column names.
Left unaided it will write fluent, confident, *wrong* SQL — it will guess
`adverse_events` when the column is `adverse_event_count`, or `quarter` when it is
`report_period`. These are hallucinations in the precise technical sense: plausible
tokens unconstrained by ground truth.

`get_metadata` is the retrieval step. It injects the *live* schema — real column
names, types, join keys, and the metric formula — into the model's context window
immediately before it writes SQL. The model then generates against retrieved
ground truth instead of its prior. This is structurally identical to document RAG;
the "document" is the database schema, fetched live at query time. Frame it this
way in the demo and a technical audience immediately understands why the two-tool
design exists and is not redundant.

### 3.2 Tool descriptions are prompts, not documentation

When the model decides *which* tool to call, the only thing it sees is each tool's
**description string**. Those descriptions are therefore not documentation for
humans — they are prompt fragments steering an LLM's tool-selection and
argument-construction. "Call this FIRST before execute_federated_query" is a
literal instruction to the model. "Use fully-qualified names such as
PARTNER_AZ_DB.drug_safety_signals.adverse_event_summary" is few-shot guidance that
makes the generated SQL correct. The care spent on those strings is prompt
engineering embedded into infrastructure. A sloppy description produces a model
that picks the wrong tool or omits the schema qualifier; a precise one produces
reliable behaviour. This is a genuinely under-appreciated surface: **your tool
descriptions are part of your prompt, and they ship inside your data product.**

### 3.3 Deterministic core, probabilistic shell

The architecture deliberately isolates the non-deterministic part of the system
from the consequential part. The LLM's choice of SQL is probabilistic — run the
same question twice and you may get slightly different SQL. But once the SQL
exists, Snowflake executes it **deterministically and auditably**. Every guardrail
in the tool exists to manage that seam:

- **SELECT/WITH-only** — the probabilistic component can never mutate state.
- **Automatic `LIMIT 1000` injection** — a model that forgets a limit cannot melt
  the warehouse.
- **get_metadata grounding** — shrinks the space of plausible-but-wrong SQL.

The pattern generalises far beyond this demo and is worth saying aloud: *let the
model decide, but make the decision cheap to verify and impossible to make
catastrophic.* Constrain the probabilistic part; keep the irreversible part
deterministic and logged.

### 3.4 Why the metric is computed on demand, not precomputed

A classic BI shop would materialise `reporting_rate_per_1k_rx` in a nightly job.
This system computes it at question time, from the governed sources, every time.
The trade is explicit: you pay query latency and you accept the LLM might phrase
the SQL differently each run, in exchange for **open-ended composition** — the
model can produce *any* cross-domain metric a user thinks to ask for, not only the
ones an analyst pre-built. The demo's real claim is not "here is the AE-rate
dashboard"; it is "you did not have to build a dashboard at all, and you can ask
the next, unanticipated question without an engineering ticket."

### 3.5 Governance by construction, not by policy

In this design the data-sharing wall is not a document anyone can violate — it is
the physical separation of the data products. The orchestrator never holds the raw
safety or commercial data. It holds two table *names* and a query *executor*. The
join happens inside Snowflake, against tables each owned by its domain, and only
the aggregated result returns. "Compute travels to the data; data does not travel
to the compute." The governance property is therefore *structural* — it holds
because of how the system is shaped, not because everyone agreed to behave. That
is the strongest possible form of a data-sharing guarantee and it is the heart of
the mesh value proposition.

### 3.6 Where the metadata actually comes from (provenance, precisely)

When `get_metadata` returns, the output is a blend of three provenances, and being
precise about this protects your credibility if someone probes:

- **Live from Snowflake `INFORMATION_SCHEMA`** — the column names, data types, and
  ordinal positions. If you altered a table, this updates with no code change.
- **Semantic-model-derived, surfaced live** — the per-column business
  descriptions. You wrote these in `models.yaml` / `output_models.py`; the platform
  propagated them into Snowflake as **column COMMENTs** when it built the tables;
  the tool reads them *back* live via `INFORMATION_SCHEMA.COLUMNS`. So they
  originate in your semantic model but are not hard-coded in the tool — and the
  text matches your model files verbatim, which you can show.
- **Static, in the tool code** — the domain framing ("Owned by Pharmacovigilance"),
  the join-keys line, and the rate formula. These are f-strings in
  `get_metadata`'s body.

Note what is *not* a source: there is **no central glossary** in play. The data
product has no glossary links (`dataProductGlossaryLinks` is null). The "glossary"
contributing definitions is your own per-DP semantic model, round-tripped through
Snowflake column comments. If a stakeholder asks "is this governed by our business
glossary?", the honest answer is "it is governed by the data product's semantic
model; wiring it to a central glossary is a deliberate next step, via attribute
`relates_to` links and a glossary fetch in the tool."

### 3.7 The MCP session model (why the 404s happened, conceptually)

MCP is stateful at the transport level. A client opens a session, sends
`initialize`, then either lists tools (`tools/list`) or calls one (`tools/call`),
then tears the session down. The probe cycle the proxy runs to check health is a
*stateless-feeling* round trip: create → list → delete, fast. A real tool call is
*stateful*: it holds the session open while your function runs, however long that
takes. If your function's downstream work (the Snowflake calls) outlives the
proxy's tolerance for an open call, the proxy abandons the session and the user
sees a 404 — even though the pod is alive and the function may still be running.
This is why "the logs show probe traffic but no CallToolRequest" was the decisive
clue: it meant the call was dying in the gap between hops, not in your code. The
fix was not logic — it was making the function *fail fast* so it always returns
inside the proxy's window (Part 6).

### 3.8 The known cosmetic bug: row_count = "0"

The tool reports `row_count: "0"` even on successful multi-row results. This is a
parser mismatch, not a data error: the counting logic was written expecting a
pretty-printed text table (counting newline-delimited rows), but Snowflake returns
results as a JSON envelope. The *data* in `result` is complete and correct; only
the convenience counter is wrong. Worth knowing so you are not thrown if someone
notices it on screen — and an easy, honest "yes, that's a known cosmetic parse
issue, the payload is intact" beats being surprised.

---

## PART 4 — THE DEMO: QUERY ARC

Run these in order. The arc is deliberate: orient, surprise, deepen, then turn the
surprise into the thesis. Each is phrased as you would say it to the model.

**0. Orientation — establishes the two governed domains exist and are separate**
> "Call get_metadata with database PARTNER_AZ_DB."

Point at the screen: two schemas, two owners, the join keys, and a metric formula
that references columns from *both* tables. Say: "neither of these tables contains
that metric — it only exists in the join."

**1. The headline — rank inversion (the whole demo in one query)**
> "For 2025-Q3, rank every product and region by adverse-event reporting rate per
> 1,000 prescriptions, and show the raw adverse-event count beside it so I can see
> how the rate ranking differs from the raw-count ranking."

IMMUNADEX (59 events) tops the rate table; NEURVANTA (605 events) sinks to the
bottom. Let the audience sit with the reversal before explaining it.

**2. The thesis question — make the inversion explicit**
> "So is NEURVANTA our most dangerous drug, since it has the most adverse events?"

The model should answer no, and explain exposure-adjusted rate. This is the line
to land hard: raw counts mislead; the federated metric corrects them.

**3. Emerging signal — a trend the raw data buries**
> "Show IMMUNADEX's reporting rate per 1,000 prescriptions across all three
> quarters of 2025 in North America. Is there a trend?"

20 → 25 → 30. A rising rate on a rising base = an escalation-worthy signal.

**4. Regional disproportionality — same drug, different region**
> "Compare VELORIN's reporting rate and its serious-event rate between North
> America and Europe across 2025. Is there a regional difference worth
> investigating?"

Europe ~3× North America on both the overall and serious rates, consistent across
quarters — not noise.

**5. (Optional) Show the governance property directly**
> "Which single table holds the adverse-event reporting rate per 1,000
> prescriptions?"

The honest answer is "none — it is computed across two separately-owned tables at
query time." That answer *is* the mesh pitch.

A presentation tip: do step 0 and step 1, then pause and explain the architecture
(Part 2) while the result is on screen. The audience is most receptive to "how it
works" immediately after seeing "that it works."

---

## PART 5 — CODE FLOW: HOW THE PIECES CONNECT

Walk the files in the order the platform consumes them, not the order they were
written. The story is: *declare → materialise → expose → execute.*

### 5.1 `spec.py` — the declaration

Everything starts here. `spec.py` declares the data product, its transform, its
inputs, and its two output ports. The two outputs are the spine:

- A `data_product_output()` carrying the `pv_registry` model on a Snowflake
  storage port **named `snowflake`** (the credential-injection contract from 2.3).
- A `data_product_rpc_output()` carrying two `rpc_function`s — each binding a
  Python function (`code(get_metadata)`) to a request/response model — on an
  `mcp-api` port that enables the `/mcp` endpoint.

Read aloud, `spec.py` says: "I produce one small Snowflake table, and I expose two
callable tools, and here is how each tool's input and output is shaped." The
`.input(...)` blocks pointing at the two source DPs give the orchestrator a valid
trigger (rebuild the registry when either source updates) and record lineage.

### 5.2 `nxd_spec.py` — the import surface

A thin module that imports every DSL symbol and every model/function name the spec
references, and re-exports them via `__all__`. Two details carry hard-won scars:
the import is `from nxd.spec import code` (not `from nxd.spec.code import ...`),
and the function objects (`get_metadata`, `execute_federated_query`) are imported
here from `__mcp__` so the spec can bind them with `code(...)`.

### 5.3 `outputs/output_models.py` and `outputs/mcp_models.py` — the shapes

`output_models.py` defines `pv_registry`'s schema (the five columns). `mcp_models.py`
defines the four request/response models for the two tools — each tool has a
request model (its arguments) and a response model (its return shape). These exist
as *separate* files because the platform validates request/response models against
the manifest independently; defining them inside `__mcp__.py` fails validation.
Every model here is also listed in `models.yaml` — the platform cross-checks the
two.

### 5.4 `transform/build_pv_registry.sql` — the materialisation

A single INSERT that writes one row into `pv_registry`, reading a COUNT from the
drug-safety input. It uses the templated references
`{{ outputs["snowflake"].pv_registry }}` and
`{{ inputs.data_products["drug-safety-signals"]["snowflake"].adverse_event_summary }}`.
Functionally trivial; architecturally load-bearing — running this is what proves
the Snowflake output port is bound and the credential context is live (2.2).

### 5.5 `__mcp__.py` — the execution

The two tools. Both follow the same five-beat REST choreography against Snowflake
(this is the hop-3/hop-4 sequence from 2.5):

1. **Login** — POST `/session/v1/login-request` with the injected credentials,
   scoped to `schemaName=ACCOUNT_COVERAGE`, returns a session token.
2. **Initialize** — POST the MCP `initialize` to the `SQL_EXEC_MCP_SRVR` URL,
   capture the `Mcp-Session-Id`.
3. **Notify** — POST `notifications/initialized`.
4. **Call** — POST `tools/call` with `sql_exec_tool` and the SQL string.
5. **Logout** — DELETE the session in a `finally` block so a token never leaks.

`get_metadata` runs a fixed `INFORMATION_SCHEMA.COLUMNS` query (scoped to the two
PV tables) and wraps the result in the static framing + example. `execute_federated_query`
guards the input (SELECT/WITH only), injects `LIMIT 1000` if absent, runs the
caller's SQL, and returns the result. Two structural rules you must be able to
explain: **every import sits inside the function body** (the platform runs these
in a restricted scope where module-level imports beyond the declared surface are
unavailable), and **all network calls use `(connect, read)` tuple timeouts** so a
stalled hop fails in ~5s and the function always returns inside the proxy's window
(3.7, Part 6).

### 5.6 The end-to-end trace, in one breath

User asks a question → model reads the tool descriptions and calls `get_metadata`
→ tool logs into Snowflake, reads live column schema, returns it with the join
keys and formula → model writes a normalised JOIN using the retrieved schema →
model calls `execute_federated_query` → tool guards, limits, and runs the SQL via
the borrowed `ACCOUNT_COVERAGE` executor against the two domain tables → Snowflake
joins them where they live and returns only the aggregate → model narrates the
rate inversion in English. No raw data left either domain at any point.

---

## PART 6 — THE FAILURE MODES WE HIT (and what each one taught)

Include one or two of these in the demo if the audience is technical. "Here is
what broke and what it revealed" is more convincing than "it worked first try,"
and each failure illuminates a real property of the platform.

- **Empty federated side (sales build).** A join returned nothing because one side
  (a Databricks-origin, Iceberg-shared table) had zero rows. Lesson: federation is
  only as live as its *least-fresh* member; a healthy pipeline with an empty source
  is silently useless. Diagnosis means checking row counts on *both* sides, not
  just that the query ran.

- **Mis-named Snowflake port.** Naming the port anything but `snowflake` produced a
  DP that deployed, went healthy, wrote its table — and whose tools got no
  credentials. Lesson: some platform contracts are exact-string and fail *silently*;
  "healthy" is not "working."

- **Wrong MCP-server schema (the long one).** Pointing the tool at its own schema's
  executor (which did not exist) instead of `ACCOUNT_COVERAGE` made calls hang until
  the proxy 404'd. The breakthrough was a **debug build** that returned the injected
  context with zero network calls — proving the function body was reached and the
  transport was fine, which isolated the fault to the Snowflake hop. Lesson: when a
  call dies in a multi-hop path, the fastest route to truth is a build that removes
  hops until it succeeds, then adds them back.

- **Flat timeouts outlasting the proxy.** The first real build used single-value
  timeouts; a slow hop could keep the function running past the gateway's patience,
  producing a 404 with no error in the logs. Switching to `(connect=5, read=N)`
  tuples made every stall fail fast and return a *legible* error. Lesson: in a
  multi-hop system, your timeouts must be tighter than the timeout of whoever is
  calling you, or you turn your own errors into someone else's silence.

- **Cold-start discovery lag.** A freshly-created DP was connected and callable but
  not yet in the searchable tool index, which read as "the tool doesn't exist."
  Lesson: liveness and discoverability are different systems with different clocks;
  confirm which one you are actually looking at before "fixing" anything.

---

## A closing mental model to carry into the room

Three governed domains. A metric that lives in none of them. A language model that
composes it on demand by sending a query to where the data sleeps, never waking
the raw data out of its home. The technology is MCP tools over a Snowflake
executor; the *idea* is that governance, freshness, and open-ended question-asking
can coexist — that you can ask the question nobody pre-built, get a correct answer,
and never have moved a row. Lead with the idea. The plumbing is in this document
for when they ask how.
