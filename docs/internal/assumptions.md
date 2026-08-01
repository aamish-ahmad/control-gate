# Control Gate Assumptions

These assumptions document only conventions already embodied in the verified
partial Phase 2 code. They do not expand the frozen product boundary.

1. The actual invoice amount is represented as a decimal string in
   inputs.amount; constraints.max_autonomous_payment_usd is the policy limit,
   not the invoice amount.
2. Missing material values remain explicit as None, or as unresolved only
   where the frozen contract requires a non-empty goal or actor string.
3. The deterministic fixture schema adds evaluator-only expected_finding_codes
   and categories because the frozen logical case schema does not define
   static expected findings or serialized field names.
4. The canonical approval-rule spelling used by fixtures is amount > 10000
   with required role finance_manager.
5. Bounded request roles are automated_finance_operator,
   accounts_payable_operator, and finance_manager. Other roles produce a
   static policy conflict until a later source-backed authority distinction is
   implemented.
6. The bounded tool registry is invoice.parse, vendor.lookup, po.lookup,
   payment.submit, and optional audit.write.
7. Wildcard * and fixture permission scope unbounded represent unbounded
   permission.
8. The partial unsafe-assumption vocabulary is limited to bypassing vendor
   lookup, purchase-order lookup, or payment confirmation.
9. The in-memory request catalog uses USD amounts only. No historical or live
   FX rate is inferred.
10. A valid finance-manager approval rule on an amount above USD 10,000 is not
    a static validation error; it is expected to become ESCALATE in Phase 3.

## Superseding checkpoint assumptions

12. A wildcard-bearing unbounded permission is an explicit prohibited request
    and rejects; an unbounded request with no named requested tool clarifies.
13. A threshold approval rule using amount > 10000 does not itself require
    escalation below that threshold. A rule with when equal to always does.
14. The explicit submit_payment and do_not_submit_payment requirement pair is
    irreconcilable and rejects; a currency constraint conflict remains
    clarifiable.

11. Static findings have no total precedence. Phase 3 must record a narrow,
    deterministic precedence decision before implementation.

## CLI checkpoint assumption

15. The local CLI recognizes a deliberately small, explicit request syntax:
    `INV-*`, `SUP-*`/`VENDOR-*`, `PO-*`, USD/EUR/GBP amounts, the literal
    `finance_agent`, and documented validation/policy phrases. It does not
    infer missing identifiers, actor authority, or business facts from prose.
