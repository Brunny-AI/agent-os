# {Entity Name} — Compliance Log (Template)

> **This template is extracted from Brunny AI's live compliance log (~7 months of operational use).** All `{placeholder}` values must be filled in on day 1. Sections are ordered by legal priority: governance first, work-log second, then exclusions, isolation, and expenses.

**Last Updated:** {YYYY-MM-DD}
**Evidence Vault (Drive / Git):** `{path_or_url}`

## Purpose

Central audit-ready record for:
1. Formation & governance milestones
2. Clean-room work logs to support any "duty of loyalty / invention assignment" posture if a founder has a day job with an adjacent employer
3. Repo / account / device isolation
4. Prohibited materials exclusions (what you intentionally did NOT use, and why)
5. Accountable-plan expenses and reimbursements

## How to Use

- Record every work session that touches product, code, prompts, datasets, architecture, or vendor accounts in **§2 CleanRoom WorkLog**.
- Record every repo, account, device, and credential boundary in **§4 Repo / Account Isolation**.
- Record every intentional exclusion (what was NOT used and why) in **§3 Prohibited Materials**.
- Record every expense with receipts and reimbursement status in **§5 Expenses**.
- Keep **§1 Governance Milestones** authoritative for dates and evidence references.

## Critical Rule

> Do not represent the entity as operating (contracts / commitments / payments) before your Secretary of State has accepted the formation filing. After acceptance, execute a Ratification Resolution and attach it to the evidence vault. Pre-formation expenses (domain, Workspace) are incurred by founders individually — not as entity commitments — until ratification.

## Day 1 Minimum Viable Entry Set

On the day you sign formation docs, fill in at minimum:
- §1 row for the formation filing (date, filing number, status, evidence path)
- §3 rows for every employer or prior IP source you are excluding (each founder)
- §4 rows for every device and account you will use for entity work

All other sections fill in as activity happens.

---

## 1. Governance Milestones

| Date          | Milestone / Activity                              | Platform             | Status  | Evidence Reference                              | Owner           | Notes            |
| ------------- | ------------------------------------------------- | -------------------- | ------- | ----------------------------------------------- | --------------- | ---------------- |
| {YYYY-MM-DD}  | Legal formation signed (founding package)         | {DocuSign / other}   | {Done}  | `Legal/{Foundational_Package}.pdf`              | {founder names} | Envelope ID: `{ID}` |
| {YYYY-MM-DD}  | {LLC-1 / Articles of Incorporation} filed         | {state registrar}    | {Done}  | `Finance/Receipt_{Filing}.pdf`                  | {founder}       | Receipt # `{filing_receipt_number}` |
| {YYYY-MM-DD}  | Execute Ratification Resolution                   | {DocuSign}           | {Done}  | `Legal/Ratification_Resolution.pdf`             | {founders}      | All pre-formation acts ratified nunc pro tunc to {formation_date} |
| {YYYY-MM-DD}  | Obtain EIN from IRS                               | IRS.gov              | {Done}  | `Tax/IRS_EIN_{CP575_or_SS4}.pdf`                | {founder}       | EIN: `{##-#######}`. Entity classification: `{single-member disregarded / partnership / corp}` |
| {YYYY-MM-DD}  | Register domain `{entity}.ai`                     | {registrar}          | {Done}  | `Finance/Receipt_Domain_{registrar}.pdf`        | {founder}       | DNS configured for {email provider} |
| {YYYY-MM-DD}  | Set up email tenant (`@{entity}.ai`)              | {Google Workspace / other} | {Done} | `Gov/{Email_Setup}.pdf`                     | {founder}       | All future vendor accounts use `@{entity}.ai` email |
| {YYYY-MM-DD}  | Open business bank account                        | {bank}               | {Done}  | `Finance/Bank_Opening_Packet.pdf`               | {founder}       | Applied `{YYYY-MM-DD}`. Funded `{YYYY-MM-DD}` via capital contribution |
| {YYYY-MM-DD}  | Initial capitalization (community property / capital contribution) | Bank transfer        | {Done}  | `Finance/Capital_Contribution_Receipts.pdf` | {founders}      | `${amount}` total. Verify via bank API transaction history |
| {YYYY-MM-DD}  | Adopt Technical Exclusion Policy                  | Local markdown       | {Done}  | `Legal/Technical_Exclusion_Policy.md`           | {founders}      | All founders sign. Covers employer-protected domains explicitly |
| {YYYY-MM-DD}  | {State / City Business License}                   | {portal URL}         | {Applied / Done} | `Gov/Business_License_Application.pdf`     | {founder}       | Confirmation # `{####}`. Renews {annually / by date} |
| {recurring-90d} | Statement of Information (or equivalent)        | {state registrar}    | {Due}   | `Gov/StatementOfInfo_Receipt.pdf`               | {founder}       | Due within {90d / state-specific} of formation |
| {annual}      | Annual franchise tax / equivalent                 | {FTB / state}        | {Due}   | `Tax/Annual_Tax_Receipt.pdf`                    | {founder}       | Check first-year waivers — may or may not apply |

---

## 2. CleanRoom WorkLog

All work sessions touching product, code, prompts, datasets, architecture, or vendor accounts must be logged here.

**Investigatory-phase framing (pre-launch):** If pre-revenue / pre-launch, document early work as **"Technical Research"** or **"Feasibility Investigation."** Do not represent the business as open or operational. In the US, startup expenditures may capitalize under IRC §195 until the entity begins an active trade or business under IRC §162 — check with your tax advisor.

**GPG-signing requirement (if using private git repo):** Use `git commit -S` for entries committed to the private repo — creates a cryptographic timestamp that cannot be backdated. Initialize GPG signing before the first technical commit.

**"Road Not Taken" entries:** When a technical approach is considered and rejected due to employer-adjacency or IP risk, log it here with a note explaining why it was rejected and what was chosen instead. These entries are as legally valuable as the prohibited-materials log.

**Employer-adjacency note (required on every entry for any founder still employed by a potentially-adjacent company):** Every entry must include an explicit statement in the Notes column: *"This contribution involves general-purpose {describe: database schema / CI-CD / UI component} and does not utilize any proprietary {employer-domain} logic, models, or patterns."* Omitting this note is a compliance gap.

| Date          | Contributor | Activity Description | Time Period | Hardware Used | Network / Location | Repo / Workspace | Employer Adjacency Check | Evidence Ref | Notes |
|---------------|-------------|----------------------|-------------|---------------|--------------------|-----------------|--------------------------|--------------|-------|
| {YYYY-MM-DD}  | {name}      | {activity}           | {HH:MM–HH:MM} | {device}    | {home / remote}    | {path / repo}   | {domain not applied}     | {evidence path} | {adjacency note + context} |

---

## 3. Prohibited Materials

Records of what was intentionally NOT used, to document clean-room separation from employer IP.

> **⚠ Must be fully populated before any development work begins. Timestamp ordering matters — entries without dates predate any code.**

| Date         | Contributor | Category               | Specific Item Excluded                                  | Reason / Risk                             | How Verified                                                  | Evidence Ref | Notes |
| ------------ | ----------- | ---------------------- | ------------------------------------------------------- | ----------------------------------------- | ------------------------------------------------------------- | ------------ | ----- |
| {YYYY-MM-DD} | {name}      | {employer} — Code      | {specific system or codebase}                           | {duty of loyalty / §2870 risk}            | No login, no local copies, no access outside employer network | —            | Verified via absence of access |
| {YYYY-MM-DD} | {name}      | {employer} — Heuristics| {architectural know-how or pattern}                     | {risk description}                        | Not applied in any {entity} design session                    | —            | Architecture uses only publicly documented patterns |
| {YYYY-MM-DD} | {name}      | Behavioral Tracking    | {behavioral-profiling, clickstream, cohort modeling}    | {would mirror employer domain}            | Not implemented; explicitly prohibited in Exclusion Policy    | —            | Auth via off-the-shelf provider only |
| {YYYY-MM-DD} | {name}      | Copyright              | Verbatim copying without fair-use basis                 | {AP v. Meltwater precedent}               | Not implemented; fair-use framework required before any content is processed | — | Blocked until fair-use framework drafted |

---

## 4. Repo / Account Isolation

Records of every repo, account, device, and credential boundary proving separation from employer resources.

> **⚠ Must be fully populated before any development work begins. Log entries should be operational, not legalistic — record facts, not compliance language.**

| Date         | Boundary Type | Name / Identifier                           | Owner     | Purpose                                  | Access Control                                                | Linked to Employer? | Evidence Ref | Notes |
| ------------ | ------------- | ------------------------------------------- | --------- | ---------------------------------------- | ------------------------------------------------------------- | ------------------- | ------------ | ----- |
| {YYYY-MM-DD} | Hardware      | {founder}'s personal {device} (serial: `{SERIAL}`) | {founder} | All entity development and admin work | Personal {Apple ID / account}; no employer MDM                | No                  | —            | Not employer-issued. Affirmed: device has never accessed {employer} VPN, Slack, or internal tools |
| {YYYY-MM-DD} | Account       | {email tenant} (`@{entity}.ai`)             | {founder} | Entity email, Drive, admin               | Entity credentials only; not linked to personal Gmail or employer GSuite | No     | `Finance/{Workspace_Receipt}.pdf` | `{founder}@{entity}.ai` active. Billing on personal card not used for employer accounts |
| {YYYY-MM-DD} | Account       | GitHub organization (`github.com/{Entity}`) | {founders} | Source code hosting                     | `@{entity}.ai` email; dedicated browser profile              | No                  | —            | Do NOT reuse any GitHub account linked to employer orgs; browser-level profile isolation required |
| {YYYY-MM-DD} | Account       | GitHub user (`@{entity}-{agent_or_role}`)   | {owner}   | {Agent / role-specific PR authoring}    | `{owner}@{entity}.ai` email; dedicated SSH key; scoped GH token | No                | —            | {CODEOWNERS role description}. Never used with employer-adjacent repos |
| {YYYY-MM-DD} | Account       | {domain registrar}                          | {founder} | Domain registration                     | Personal {registrar} account; personal email at registration; migrate to `@{entity}.ai` | No | `Finance/Receipt_Domain.pdf` | {entity}.ai domain active |
| {YYYY-MM-DD} | Account       | {AI subscription} (per-seat)                | {founder} | AI dev tooling                          | `@{entity}.ai` email; Mercury virtual card (or personal card pending corp-card setup) | No | `Finance/Invoice_{vendor}.pdf` | Billed to entity. `${amount}/mo` |
| {YYYY-MM-DD} | Payment       | {bank} virtual cards (per vendor)           | {founder} | Isolated payment method for all SaaS   | Issued from entity {bank} account; single-use per vendor     | No                  | —            | One virtual card per vendor — clean financial fingerprint |
| {YYYY-MM-DD} | Account       | {collab tool — Slack / Discord}             | {founder} | Internal business communication         | `@{entity}.ai` email; entity virtual card                    | No                  | `Finance/{Collab_Receipt}.pdf` | Prohibited: personal iMessage / Telegram for entity ops |

---

## 5. Expenses (Accountable Plan)

All expenses must have a receipt attached before entity reimbursement. Reimbursement occurs after the business bank account is opened.

**Reimbursement batching policy:** All pre-formation and pre-bank-account expenses must be reimbursed within **{N} days of bank account opening** (7 days is a defensible default). Attach matching receipt to each reimbursement transaction. This prevents characterization of personal spending as business expenses recharacterized after the fact.

**Pre-formation expense disclaimer:** All expenses incurred before SOS acceptance were incurred by the founders in their **individual capacity** and are not commitments of the entity. They are subject to reimbursement under the Accountable Plan once the entity is operational.

**Community-property note (if applicable):** Capital contributions may be treated as community property contributions for tax purposes. Internal ledger entries do not imply partnership classification or separate capital accounts in the tax sense. Check with your tax advisor.

**Home-office deduction:** {elected / not elected}.

**Startup-cost capitalization strategy:** {e.g., IRC §195 pre-launch capitalization strategy, with launch event triggering § 162 active-trade status — check with tax advisor.}

| Expense Date | Item                         | Vendor                | Amount   | Billing  | Currency | Payment Method        | Paid By | Receipt Attached? | Business Purpose                         | Category       | Reimbursable? | Reimbursed Date | Reimbursed Amount | Evidence Ref                      | Notes                                                   |
| ------------ | ---------------------------- | --------------------- | -------- | -------- | -------- | --------------------- | ------- | ----------------- | ---------------------------------------- | -------------- | ------------- | --------------- | ----------------- | --------------------------------- | ------------------------------------------------------- |
| {YYYY-MM-DD} | {Formation fee}              | {SOS}                 | ${amt}   | One-time | USD      | Personal card (*####) | {founder} | YES             | Entity formation filing                  | Formation      | YES           | {YYYY-MM-DD}    | ${amt}            | `Finance/Receipt_{filing}.pdf`    | Reimbursed via {bank} ACH. Txn ID: `{txn_id}` |
| {YYYY-MM-DD} | {Domain registration}        | {registrar}           | ${amt}   | {2yr}    | USD      | Personal card (*####) | {founder} | YES             | Domain registration                      | Software       | YES           | {YYYY-MM-DD}    | ${amt}            | `Finance/Receipt_Domain.pdf`      | Reimbursed via ACH. Txn ID: `{txn_id}` |
| {YYYY-MM-DD} | {AI subscription — 1mo}      | {vendor}              | ${amt}   | Monthly  | USD      | Personal card (*####) | {founder} | YES             | AI dev tooling                           | Software       | YES           | {YYYY-MM-DD}    | ${amt}            | `Finance/Invoice_{vendor}.pdf`    | Reimbursed via ACH. Migrate billing to entity virtual card when ready |

---

## Appendix: Evidence-Vault Structure

Recommended directory layout for an immutable evidence vault (Git or Drive):

```
{entity}-corp/
├── Legal/                 # Formation docs, exclusion policies, signed resolutions
├── Finance/               # Bank opening packets, receipts, capitalization proofs
├── Gov/                   # Government filings, licenses, certificates
├── Tax/                   # IRS confirmations, tax filings, W-8/W-9
├── Notes/                 # Internal decision logs, design sessions
└── compliance-archive/    # Weekly GPG-signed snapshots of this log
```

## Appendix: Weekly Compliance Snapshot

Every Sunday (or chosen cadence): export this log + any changed Drive docs as PDF or Markdown, commit to `compliance-archive/` with `git commit -S` (GPG-signed). This creates an independent timestamped record that survives edits to the live log.

---

**Template version:** v1 (2026-04-17 extraction from Brunny AI live compliance log)
**Feedback:** open an issue or PR against the `agent-os` repo
