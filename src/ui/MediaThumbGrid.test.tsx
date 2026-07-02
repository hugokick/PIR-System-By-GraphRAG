import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { MediaThumbGrid } from './MediaThumbGrid';
import type { DocumentAsset, MediaAsset } from '../types';

const assets: MediaAsset[] = [
  {
    id: 'scene-image',
    type: 'image',
    name: '现场照片.png',
    url: 'http://assets.test/scene.png',
    note: '实施现场'
  },
  {
    id: 'demo-video',
    type: 'video',
    name: '互动演示.mp4',
    url: 'http://assets.test/demo.mp4'
  }
];

const documents: DocumentAsset[] = [
  {
    id: 'quote-pdf',
    name: 'quote.pdf',
    fileType: 'pdf',
    url: 'http://assets.test/quote.pdf',
    sourceNote: '报价文件',
    chunks: [
      { id: 'quote-pdf-1', text: '预算 20-30 万', sequence: 1 },
      { id: 'quote-pdf-2', text: '亚克力与金属结构', sequence: 2 }
    ]
  }
];

describe('MediaThumbGrid', () => {
  it('renders media assets as compact thumbnails', () => {
    render(
      <MediaThumbGrid
        assets={assets}
        onPreview={() => undefined}
        onRemove={() => undefined}
        downloadUrl={(url) => `${url}?download=1`}
      />
    );

    expect(document.querySelector('.media-gallery-grid')?.classList.contains('thumbnail-grid')).toBe(true);
    expect(screen.getByRole('button', { name: '预览媒体 现场照片.png' })).toBeTruthy();
    expect(screen.getByLabelText('互动演示.mp4 视频预览')).toBeTruthy();
    expect(screen.getByText('实施现场')).toBeTruthy();
  });

  it('opens preview when a previewable thumbnail is clicked', () => {
    const onPreview = vi.fn();
    render(
      <MediaThumbGrid
        assets={assets}
        onPreview={onPreview}
        onRemove={() => undefined}
        downloadUrl={(url) => `${url}?download=1`}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: '预览媒体 现场照片.png' }));

    expect(onPreview).toHaveBeenCalledWith(assets[0]);
  });

  it('renders document assets as compact thumbnails and previews PDFs', () => {
    const onPreviewDocument = vi.fn();
    render(
      <MediaThumbGrid
        assets={[]}
        documents={documents}
        onPreview={() => undefined}
        onPreviewDocument={onPreviewDocument}
        onRemove={() => undefined}
        downloadUrl={(url) => `${url}?download=1`}
      />
    );

    expect(screen.getByText('quote.pdf')).toBeTruthy();
    expect(screen.getAllByText('PDF').length).toBeGreaterThan(0);
    expect(screen.getByText('报价文件')).toBeTruthy();
    expect(screen.getByText('已生成 2 个引用片段')).toBeTruthy();

    fireEvent.click(screen.getByRole('button', { name: '预览资料 quote.pdf' }));

    expect(onPreviewDocument).toHaveBeenCalledWith(documents[0]);
  });

  it('shows an empty media state', () => {
    render(
      <MediaThumbGrid
        assets={[]}
        onPreview={() => undefined}
        onRemove={() => undefined}
        downloadUrl={(url) => `${url}?download=1`}
      />
    );

    expect(screen.getByText('暂无媒体档案')).toBeTruthy();
  });
});
