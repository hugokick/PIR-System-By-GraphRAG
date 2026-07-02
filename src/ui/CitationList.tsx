import type { DocumentAsset, GraphRagAnswer, GraphRagCitation, GraphRagHit } from '../types';

type CitationListProps = {
  answer: GraphRagAnswer | null;
  citations: GraphRagCitation[];
  onSelectCitation: (citation: GraphRagCitation) => void;
  downloadUrl: (url: string) => string;
};

type CitationOwner = {
  hit: GraphRagHit;
  document: DocumentAsset | null;
};

const citationSourceTypeLabels: Record<string, string> = {
  document: '资料文档',
  exhibit: '展项档案',
  media_asset: '媒体资产'
};

function citationSourceTypeLabel(sourceType: string) {
  return citationSourceTypeLabels[sourceType] ?? sourceType;
}

function sameCitation(left: GraphRagCitation, right: GraphRagCitation) {
  return left.sourceType === right.sourceType && left.sourceId === right.sourceId;
}

function citationOwner(answer: GraphRagAnswer | null, citation: GraphRagCitation): CitationOwner | null {
  if (!answer) return null;

  for (const hit of answer.items) {
    const ownsCitation =
      (citation.sourceType === 'exhibit' && hit.exhibit.id === citation.sourceId)
      || hit.citations.some((itemCitation) => sameCitation(itemCitation, citation));
    if (!ownsCitation) continue;

    return {
      hit,
      document:
        citation.sourceType === 'document'
          ? hit.exhibit.documents.find((document) => document.id === citation.sourceId) ?? null
          : null
    };
  }

  return null;
}

export function CitationList({
  answer,
  citations,
  onSelectCitation,
  downloadUrl
}: CitationListProps) {
  if (citations.length === 0) {
    return <p className="graphrag-citation-empty">暂无可引用来源</p>;
  }

  return (
    <div className="graphrag-citations">
      {citations.map((citation, index) => {
        const owner = citationOwner(answer, citation);
        return (
          <article className="graphrag-citation-card" key={`${citation.sourceType}-${citation.sourceId}`}>
            <button
              type="button"
              className="graphrag-citation-main"
              aria-label={`引用来源 [${index + 1}] ${citation.title}`}
              onClick={() => onSelectCitation(citation)}
            >
              <em>[{index + 1}]</em>
              <small>来源类型：{citationSourceTypeLabel(citation.sourceType)}</small>
              <strong>{citation.title}</strong>
              {owner && <b>对应展项：{owner.hit.exhibit.name}</b>}
              <span>{citation.snippet}</span>
            </button>
            {owner?.document && (
              <div className="graphrag-citation-actions">
                <a href={owner.document.url} target="_blank" rel="noreferrer">
                  打开资料
                </a>
                <a href={downloadUrl(owner.document.url)} download={owner.document.name}>
                  下载资料
                </a>
              </div>
            )}
          </article>
        );
      })}
    </div>
  );
}
