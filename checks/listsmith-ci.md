# listsmith-ci — pre-listing checklist for an x402 stall

Run every check before you seed a listing (and after any change to
prices, descriptions, or schemas). These are the same checks the
Verdict Row fleet's listings are graded against; each one exists
because a real indexer silently punishes its violation.

## Copy checks

- [ ] Every route description is **< 500 characters** (CDP catalog
      limit — longer descriptions are dropped or truncated at
      indexing, silently).
- [ ] Every description carries a **"Use this when…"** sentence
      naming the buyer's situation, not just the feature.
- [ ] No traction claims the chain can't back. Seeds are labelled
      seeds; inspector traffic is never merged with organic traffic.

## Schema checks

- [ ] Input schema is a full typed object schema with `required`
      fields named; the input example validates against it.
- [ ] Output schema is a full typed object schema — never the hollow
      `{"type": "object"}` shape.
- [ ] Output example serializes to **≤ ~1,450 bytes** (some indexers
      drop larger samples without telling you).
- [ ] Every error the route can return is a JSON body with an
      `error` field; failure semantics are stated in the description
      (502 = upstream failure, no settlement).

## Payment-surface checks

- [ ] Unpaid probe of every route returns **402** whose accepts
      exactly match the manifest entry (amount, asset, network,
      payTo) — the Verdict Row Verified battery
      (`badge/run_battery.py` in x402-loop-kits) automates this.
- [ ] `payTo` is the address you actually control, on the network
      the challenge names.
- [ ] A settled test payment lands in the intended catalog
      (facilitator choice = catalog choice; see README).

## Operations checks

- [ ] `/health` is 200 and reports storage durability honestly
      (volume-backed or ephemeral — say which).
- [ ] Keepalive is running somewhere that is not the stall itself.
- [ ] Pack/pass state survives a redeploy (or the re-baseline
      behavior is documented where buyers can read it).
