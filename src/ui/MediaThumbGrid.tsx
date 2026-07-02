import { FileText, Trash2 } from 'lucide-react';
import type { SyntheticEvent } from 'react';
import type { MediaAsset } from '../types';

type MediaThumbGridProps = {
  assets: MediaAsset[];
  canDelete?: boolean;
  deletingAssetId?: string | null;
  isDeleteProtected?: boolean;
  onPreview: (asset: MediaAsset) => void;
  onRemove: (assetId: string) => void;
  downloadUrl: (url: string) => string;
  imageFallback?: (event: SyntheticEvent<HTMLImageElement>) => void;
};

function canPreviewMedia(asset: MediaAsset) {
  return asset.type === 'image' || asset.type === 'video';
}

export function MediaThumbGrid({
  assets,
  canDelete = false,
  deletingAssetId = null,
  isDeleteProtected = false,
  onPreview,
  onRemove,
  downloadUrl,
  imageFallback
}: MediaThumbGridProps) {
  if (assets.length === 0) {
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
    </div>
  );
}
