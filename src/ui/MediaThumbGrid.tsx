import { FileText, Trash2 } from 'lucide-react';
import type { ReactNode, SyntheticEvent } from 'react';
import type { DocumentAsset, MediaAsset } from '../types';

type MediaThumbGridProps = {
  assets: MediaAsset[];
  documents?: DocumentAsset[];
  canDelete?: boolean;
  canWrite?: boolean;
  deletingAssetId?: string | null;
  isDeleteProtected?: boolean;
  onPreview: (asset: MediaAsset) => void;
  onPreviewDocument?: (document: DocumentAsset) => void;
  onRemove: (assetId: string) => void;
  onRequestDocumentExtraction?: (document: DocumentAsset) => void;
  downloadUrl: (url: string) => string;
  imageFallback?: (event: SyntheticEvent<HTMLImageElement>) => void;
  loadingDocumentExtractionId?: string | null;
  renderDocumentDetails?: (document: DocumentAsset) => ReactNode;
};

function canPreviewMedia(asset: MediaAsset) {
  return asset.type === 'image' || asset.type === 'video';
}

function isPdfDocument(document: DocumentAsset) {
  return document.fileType.toLowerCase() === 'pdf';
}

function documentStatusLabel(document: DocumentAsset) {
  const chunkCount = document.chunks?.length ?? 0;
  return chunkCount > 0 ? `已生成 ${chunkCount} 个引用片段` : '未生成引用片段';
}

export function MediaThumbGrid({
  assets,
  documents = [],
  canDelete = false,
  canWrite = false,
  deletingAssetId = null,
  isDeleteProtected = false,
  onPreview,
  onPreviewDocument,
  onRemove,
  onRequestDocumentExtraction,
  downloadUrl,
  imageFallback,
  loadingDocumentExtractionId = null,
  renderDocumentDetails
}: MediaThumbGridProps) {
  if (assets.length === 0 && documents.length === 0) {
    return <p className="asset-empty-state">暂无媒体档案</p>;
  }

  return (
    <div className="media-gallery-grid thumbnail-grid">
      {assets.map((asset) => (
        <article key={asset.id} className={canPreviewMedia(asset) ? 'media-card previewable' : 'media-card'}>
          {asset.type === 'image' && (
            <button
              type="button"
              className="media-thumbnail"
              onClick={() => onPreview(asset)}
              aria-label={`预览媒体 ${asset.name}`}
            >
              <img src={asset.url} alt={asset.name} onError={imageFallback} />
            </button>
          )}
          {asset.type === 'video' && (
            <button
              type="button"
              className="media-thumbnail"
              onClick={() => onPreview(asset)}
              aria-label={`预览媒体 ${asset.name}`}
            >
              <video
                src={asset.url}
                muted
                playsInline
                preload="metadata"
                aria-label={`${asset.name} 视频预览`}
              />
            </button>
          )}
          {!canPreviewMedia(asset) && (
            <a className="media-file-link" href={downloadUrl(asset.url)} download={asset.name}>
              <FileText size={22} />
              <span>{asset.name}</span>
            </a>
          )}
          <div>
            {canPreviewMedia(asset) ? (
              <button type="button" className="media-title-link" onClick={() => onPreview(asset)}>
                {asset.name}
              </button>
            ) : (
              <strong>{asset.name}</strong>
            )}
            <span>{asset.type}</span>
            {asset.note && <small>{asset.note}</small>}
            {canDelete && (
              <button
                type="button"
                className="asset-delete-action"
                onClick={() => onRemove(asset.id)}
                disabled={deletingAssetId === asset.id || isDeleteProtected}
                aria-label={`删除媒体 ${asset.name}`}
              >
                <Trash2 size={14} />
                删除
              </button>
            )}
          </div>
        </article>
      ))}
      {documents.map((document) => {
        const canPreviewDocument = Boolean(onPreviewDocument && isPdfDocument(document));
        const fileType = document.fileType.toUpperCase();

        return (
          <article
            key={document.id}
            className={canPreviewDocument ? 'media-card document-thumb-card previewable' : 'media-card document-thumb-card'}
          >
            {canPreviewDocument ? (
              <button
                type="button"
                className="media-thumbnail document-thumbnail"
                onClick={() => onPreviewDocument?.(document)}
                aria-label={`预览资料 ${document.name}`}
              >
                <FileText size={26} />
                <strong>{fileType}</strong>
              </button>
            ) : (
              <a className="media-file-link document-thumbnail" href={downloadUrl(document.url)} download={document.name}>
                <FileText size={26} />
                <strong>{fileType}</strong>
              </a>
            )}
            <div>
              {canPreviewDocument ? (
                <button type="button" className="media-title-link" onClick={() => onPreviewDocument?.(document)}>
                  {document.name}
                </button>
              ) : (
                <a className="media-title-link" href={downloadUrl(document.url)} download={document.name}>
                  {document.name}
                </a>
              )}
              <span>{fileType}</span>
              {document.sourceNote && <small>{document.sourceNote}</small>}
              <small
                className={
                  document.chunks && document.chunks.length > 0
                    ? 'document-rag-status indexed'
                    : 'document-rag-status empty'
                }
              >
                {documentStatusLabel(document)}
              </small>
              {canDelete && (
                <button
                  type="button"
                  className="asset-delete-action"
                  onClick={() => onRemove(document.id)}
                  disabled={deletingAssetId === document.id || isDeleteProtected}
                  aria-label={`删除资料 ${document.name}`}
                >
                  <Trash2 size={14} />
                  删除
                </button>
              )}
              {canWrite && onRequestDocumentExtraction && (
                <button
                  type="button"
                  className="document-suggestion-action"
                  onClick={() => onRequestDocumentExtraction(document)}
                  disabled={loadingDocumentExtractionId !== null}
                  aria-label={`抽取字段建议 ${document.name}`}
                >
                  {loadingDocumentExtractionId === document.id ? '分析中' : '字段建议'}
                </button>
              )}
            </div>
            {renderDocumentDetails?.(document)}
          </article>
        );
      })}
    </div>
  );
}
