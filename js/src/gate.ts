/**
 * Gate: pre-execution policy enforcement with bilateral receipts.
 *
 *     const gate = new Gate({ covenant: Covenant.fromYaml("covenant.yaml") });
 *     const receipt = gate.authorize({ agentId: "loan-processor", actionName: "approve_loan",
 *                                      payload: { amount: 75000 }, context: { amount: 75000 } });
 *     if (receipt.authorized) {
 *       const result = await processLoan();
 *       gate.seal(receipt, { result, status: "success" });
 *     }
 *
 * Every authorization is signed and chained; every seal is chained. The
 * receipts directory and the chain format are the Python Gate's, so one
 * verifier reads both.
 */
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";

import { AuditChain } from "./chain.js";
import type { Context, Covenant, RuleAction } from "./covenant.js";
import { ActionReceipt, ReceiptSigner, hashPayload, hashResult, pythonUtcNow, type ReceiptStatus } from "./receipt.js";

export interface GateOptions {
  covenant: Covenant;
  /** 32-byte Ed25519 seed to resume a persisted signing identity. */
  signingKey?: Buffer | Uint8Array;
  /** HMAC key for the audit chain (separate from the Ed25519 key). */
  hmacKey?: string;
  /** Where receipts and the chain are written. Default ~/.air-blackbox/receipts. */
  runsDir?: string;
  /** Called when a rule says require_approval. Return true to approve. */
  onApprovalNeeded?: (receipt: ActionReceipt) => boolean | Promise<boolean>;
}

export interface AuthorizeArgs {
  agentId: string;
  actionName: string;
  /** Hashed into the receipt; never stored. */
  payload?: unknown;
  /** Values the covenant's `when`/`unless` guards read. */
  context?: Context;
  category?: string;
  parentReceipt?: ActionReceipt;
  metadata?: Record<string, unknown>;
}

export interface VerifyReport {
  receipt_id: string;
  signing_method: string;
  authorization_valid: boolean;
  seal_valid: boolean;
  is_sealed: boolean;
  has_parent: boolean;
  covenant_hash: string;
  chain_hash: string;
  authorized: boolean;
  decision: string;
  /** Cryptographic verdict only: a valid receipt for a DENIED action is overall=true. */
  overall: boolean;
}

export class Gate {
  readonly covenant: Covenant;
  readonly signer: ReceiptSigner;
  readonly runsDir: string;
  private readonly chain: AuditChain;
  private readonly receipts = new Map<string, ActionReceipt>();
  private readonly onApprovalNeeded?: GateOptions["onApprovalNeeded"];

  constructor(options: GateOptions) {
    this.covenant = options.covenant;
    this.signer = new ReceiptSigner({ privateKey: options.signingKey, hmacKey: options.hmacKey });
    this.runsDir = options.runsDir ?? path.join(os.homedir(), ".air-blackbox", "receipts");
    fs.mkdirSync(this.runsDir, { recursive: true });
    this.chain = new AuditChain(this.runsDir, options.hmacKey);
    this.onApprovalNeeded = options.onApprovalNeeded;
  }

  get publicKeyHex(): string | undefined {
    return this.signer.publicKeyHex;
  }

  get signingMethod(): string {
    return this.signer.method;
  }

  /**
   * Phase 1: evaluate the covenant, sign the decision, chain it. Synchronous
   * unless an approval callback is registered and returns a promise; use
   * `authorizeAsync` for that case.
   */
  authorize(args: AuthorizeArgs): ActionReceipt {
    const r = this.authorizeAsync(args);
    if (r instanceof Promise) {
      throw new TypeError("onApprovalNeeded returned a promise; use gate.authorizeAsync()");
    }
    return r;
  }

  authorizeAsync(args: AuthorizeArgs): ActionReceipt | Promise<ActionReceipt> {
    const context: Context = { ...(args.context ?? {}) };
    const metadata = { ...(args.metadata ?? {}) };
    if (args.category) context["category"] = args.category;
    const decision = this.covenant.evaluate(args.actionName, context);

    const finish = (authorized: boolean, status: ReceiptStatus): ActionReceipt => {
      const receipt = new ActionReceipt({
        agent_id: args.agentId,
        action_name: args.actionName,
        action_category: args.category ?? "",
        payload_hash: args.payload != null && args.payload !== "" ? hashPayload(args.payload) : "",
        covenant_hash: this.covenant.hash,
        decision,
        authorized,
        parent_receipt_id: args.parentReceipt?.receipt_id ?? null,
        status,
        metadata,
      });
      this.signer.signAuthorization(receipt);
      receipt.chain_hash = this.chain.write({ ...receipt.toDict() });
      this.receipts.set(receipt.receipt_id, receipt);
      this.writeReceipt(receipt);
      return receipt;
    };

    if (decision === "permit") return finish(true, "authorized");
    if (decision === "forbid") return finish(false, "denied");
    // require_approval: no callback means the safe default, deny.
    if (!this.onApprovalNeeded) return finish(false, "denied");
    const preliminary = new ActionReceipt({
      agent_id: args.agentId,
      action_name: args.actionName,
      action_category: args.category ?? "",
      payload_hash: args.payload != null && args.payload !== "" ? hashPayload(args.payload) : "",
      covenant_hash: this.covenant.hash,
      decision,
      status: "pending",
      metadata,
    });
    const approved = this.onApprovalNeeded(preliminary);
    const settle = (ok: boolean): ActionReceipt => (ok ? finish(true, "authorized") : finish(false, "denied"));
    return approved instanceof Promise ? approved.then(settle) : settle(approved);
  }

  /** Phase 2: attach the result hash, seal with a second signature, chain it. */
  seal(receipt: ActionReceipt, options: { result?: unknown; status?: "success" | "failure" | "error" } = {}): ActionReceipt {
    const status = options.status ?? "success";
    receipt.result_hash = options.result !== undefined && options.result !== null ? hashResult(options.result) : "";
    receipt.result_status = status;
    receipt.sealed_at = pythonUtcNow();
    receipt.status = status === "success" ? "sealed" : "failed";
    this.signer.signSeal(receipt);
    receipt.chain_hash = this.chain.write({
      type: "seal",
      receipt_id: receipt.receipt_id,
      result_hash: receipt.result_hash,
      result_status: receipt.result_status,
      seal_sig: receipt.seal_sig,
      sealed_at: receipt.sealed_at,
    });
    this.receipts.set(receipt.receipt_id, receipt);
    this.writeReceipt(receipt);
    return receipt;
  }

  verify(receipt: ActionReceipt): VerifyReport {
    const authValid = this.signer.verifyAuthorization(receipt);
    const sealValid = receipt.seal_sig ? this.signer.verifySeal(receipt) : false;
    return {
      receipt_id: receipt.receipt_id,
      signing_method: this.signer.method,
      authorization_valid: authValid,
      seal_valid: sealValid,
      is_sealed: receipt.status === "sealed" || receipt.status === "failed",
      has_parent: receipt.parent_receipt_id !== null,
      covenant_hash: receipt.covenant_hash,
      chain_hash: receipt.chain_hash,
      authorized: receipt.authorized,
      decision: receipt.decision,
      overall: authValid && (sealValid || !receipt.seal_sig),
    };
  }

  /** Root-first list of receipts from a delegated action back to its origin. */
  walkDelegationChain(receipt: ActionReceipt): ActionReceipt[] {
    const chain = [receipt];
    const seen = new Set([receipt.receipt_id]);
    let current = receipt;
    while (current.parent_receipt_id) {
      if (seen.has(current.parent_receipt_id)) break;
      const parent = this.receipts.get(current.parent_receipt_id);
      if (!parent) break;
      seen.add(parent.receipt_id);
      chain.push(parent);
      current = parent;
    }
    return chain.reverse();
  }

  getReceipt(id: string): ActionReceipt | undefined {
    return this.receipts.get(id);
  }

  get receiptCount(): number {
    return this.receipts.size;
  }

  private writeReceipt(receipt: ActionReceipt): void {
    try {
      fs.writeFileSync(path.join(this.runsDir, `${receipt.receipt_id}.receipt.json`), JSON.stringify(receipt.toDict(), null, 2));
    } catch {
      /* non-blocking, as in the Python gate */
    }
  }
}

export type { RuleAction };
