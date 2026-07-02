import { Download, X } from 'lucide-react';
import type { SyntheticEvent } from 'react';
import type { DocumentAsset, MediaAsset } from '../types';

export type PreviewAsset =
  | (MediaAsset & { kind: 'media' })
  | (DocumentAsset & { kind: 'document' });

type AssetPreviewModalProps = {
  asset: PreviewAsset;
  onClose: () => void;
  downloadUrl?: (url: string) => string;
  imageFallback?: (event: SyntheticEvent<HTMLImageElement>) => void;
};

function isImage(asset: PreviewAsset) {
  return asset.kind === 'media' && asset.type === 'image';
}

function isVideo(asset: PreviewAsset) {
  return asset.kind === 'media' && asset.type === 'video';
}

function isPdf(asset: PreviewAsset) {
  return asset.kind === 'document' && asset.fileType.toLowerCase() === 'pdf';
}

export function AssetPreviewModal({
  asset,
  onClose,
  downloadUrl = (url) => url,
  imageFallback
}: AssetPreviewModalProps) {
  return (
    <div className="media-preview-backdrop" onClick={onClose}>
      <section
        className="media-preview-dialog asset-preview-dialog"
        role="dialog"
        aria-modal="true"
        aria-label={asset.name}
        onClick={(event) => event.stopPropagation()}
      >
        <header>
          <strong>{asset.name}</strong>
          <div className="asset-preview-actions">
            <a href={downloadUrl(asset.url)} download={asset.name}>
              <Download size={16} />
              下载原文件
            </a>
            <button type="button" onClick={onClose} aria-label="关闭预览">
              <X size={18} />
            </button>
          </div>
        </header>
        <div className="media-preview-body">
          {isImage(asset) && <img src={asset.url} alt={asset.name} onError={imageFallback} />}
          {isVideo(asset) && (
            <video
              src={asset.url}
              controls
              playsInline
              aria-label={`${asset.name} 播放器`}
            />
          )}
          {isPdf(asset) && (
            <iframe
              className="document-preview in-modal"
              src={asset.url}
              title={`${asset.name} 预览`}
            />
          )}
        </div>
        {'note' in asset && asset.note && <p>{asset.note}</p>}
        {'sourceNote' in asset && asset.sourceNote && <p>{asset.sourceNote}</p>}
      </section>
    </div>
  );
}
