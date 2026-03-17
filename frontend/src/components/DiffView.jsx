/**
 * Git-style diff view for reconciliation results.
 * Each record is shown as one line of tokens: field=value.
 * Color coding: mismatch (amber), missing in target (red), new in target (green).
 */
import { useMemo } from "react";

const DIFF_TYPE = {
  MATCHED_DISCREPANCY: "matched_discrepancy",
  UNMATCHED_SOURCE: "unmatched_source",
  UNMATCHED_TARGET: "unmatched_target",
};

function formatLine(record = {}, diffFieldIds = []) {
  const fields = Object.keys(record).sort();
  return fields.map((k) => ({ k, v: record[k], isDiff: diffFieldIds.includes(k) }));
}

function Line({ prefix, tokens, highlight }) {
  return (
    <div className={`gitline ${highlight}`}>
      <span className="gitprefix">{prefix}</span>
      <span className="gittokens">
        {tokens.length === 0 ? (
          <span className="gittoken">
            <span className="gitval">(no fields)</span>
          </span>
        ) : (
          tokens.map((t) => (
            <span key={t.k} className={t.isDiff ? "gittoken gittoken-diff" : "gittoken"}>
              <span className="gitkey">{t.k}</span>
              <span className="gitsep">=</span>
              <span className="gitval">{t.v === null || t.v === undefined ? "—" : String(t.v)}</span>
            </span>
          ))
        )}
      </span>
    </div>
  );
}

function RecordRowGit({
  type,
  sourceRecord,
  targetRecord,
  diffFieldIds = [],
  recordKey,
  sourceMetadata,
  targetMetadata,
}) {
  const srcTokens = useMemo(
    () => formatLine(sourceRecord || {}, diffFieldIds),
    [sourceRecord, diffFieldIds]
  );
  const tgtTokens = useMemo(
    () => formatLine(targetRecord || {}, diffFieldIds),
    [targetRecord, diffFieldIds]
  );

  const srcLineNo = sourceMetadata?.row_number ?? sourceMetadata?.line_number;
  const tgtLineNo = targetMetadata?.row_number ?? targetMetadata?.line_number;

  const headerRight =
    srcLineNo !== undefined || tgtLineNo !== undefined
      ? ` (src line ${srcLineNo ?? "—"} / tgt line ${tgtLineNo ?? "—"})`
      : "";

  return (
    <div className="diff-record">
      <div className="diff-record-key">
        <strong>Record key:</strong> {recordKey || "(no key)"}{headerRight}
        {type === DIFF_TYPE.UNMATCHED_SOURCE && (
          <span className="diff-badge diff-badge-missing">Missing in target</span>
        )}
        {type === DIFF_TYPE.UNMATCHED_TARGET && (
          <span className="diff-badge diff-badge-added">New in target</span>
        )}
        {type === DIFF_TYPE.MATCHED_DISCREPANCY && (
          <span className="diff-badge diff-badge-mismatch">Has mismatches</span>
        )}
      </div>
      <div className="gitdiff">
        {type !== DIFF_TYPE.UNMATCHED_TARGET ? (
          <Line
            prefix="-"
            tokens={srcTokens}
            highlight={type === DIFF_TYPE.UNMATCHED_SOURCE ? "git-missing" : ""}
          />
        ) : null}
        {type !== DIFF_TYPE.UNMATCHED_SOURCE ? (
          <Line
            prefix="+"
            tokens={tgtTokens}
            highlight={type === DIFF_TYPE.UNMATCHED_TARGET ? "git-added" : ""}
          />
        ) : null}
      </div>
    </div>
  );
}

export default function DiffView({ data }) {
  const items = useMemo(() => {
    if (!data) return [];
    const matched = (data.matched_with_discrepancies || []).map((item) => ({
      ...item,
      type: DIFF_TYPE.MATCHED_DISCREPANCY,
    }));
    const unmatchedSrc = (data.unmatched_source || []).map((item) => ({
      ...item,
      type: DIFF_TYPE.UNMATCHED_SOURCE,
      record_key: item.record_key || "(no key)",
    }));
    const unmatchedTgt = (data.unmatched_target || []).map((item) => ({
      ...item,
      type: DIFF_TYPE.UNMATCHED_TARGET,
      record_key: item.record_key || "(no key)",
    }));
    return [...matched, ...unmatchedSrc, ...unmatchedTgt];
  }, [data]);

  if (!data) {
    return (
      <div className="diff-view-empty">
        <p>Load a job to see the Git-style diff view.</p>
      </div>
    );
  }

  const counts = {
    matched: (data.matched_with_discrepancies || []).length,
    unmatchedSource: (data.unmatched_source || []).length,
    unmatchedTarget: (data.unmatched_target || []).length,
  };

  return (
    <div className="diff-view">
      <div className="diff-view-summary">
        <span className="diff-summary-item">
          <span className="diff-summary-count diff-count-mismatch">{counts.matched}</span>
          Matched with mismatches
        </span>
        <span className="diff-summary-item">
          <span className="diff-summary-count diff-count-missing">{counts.unmatchedSource}</span>
          Missing in target
        </span>
        <span className="diff-summary-item">
          <span className="diff-summary-count diff-count-added">{counts.unmatchedTarget}</span>
          New in target
        </span>
      </div>
      <div className="diff-view-legend">
        <span>
          <span className="diff-legend-swatch diff-swatch-mismatch" />
          Mismatch
        </span>
        <span>
          <span className="diff-legend-swatch diff-swatch-missing" />
          Missing in target
        </span>
        <span>
          <span className="diff-legend-swatch diff-swatch-added" />
          New in target
        </span>
      </div>
      <div className="diff-view-list">
        {items.length === 0 ? (
          <div className="diff-view-empty">No discrepancies or unmatched records.</div>
        ) : (
          items.map((item, idx) => (
            <RecordRowGit
              key={`${item.type}-${item.record_key ?? idx}-${idx}`}
              type={item.type}
              sourceRecord={item.source_record}
              targetRecord={item.target_record}
              diffFieldIds={item.diff_field_ids || []}
              recordKey={item.record_key}
              sourceMetadata={item.source_metadata}
              targetMetadata={item.target_metadata}
            />
          ))
        )}
      </div>
    </div>
  );
}

