import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { AssetPreviewModal, type PreviewAsset } from './AssetPreviewModal';

describe('AssetPreviewModal', () => {
  it('renders image previews', () => {
    const asset: PreviewAsset = {
      kind: 'media',
      id: 'image-asset',
      type: 'image',
      name: '效果图.png',
      url: 'http://assets.test/render.png'
    };

    render(<AssetPreviewModal asset={asset} onClose={() => undefined} />);

    const dialog = screen.getByRole('dialog', { name: '效果图.png' });
    expect(within(dialog).getByAltText('效果图.png')).toBeTruthy();
  });

  it('renders video previews with controls', () => {
    const asset: PreviewAsset = {
      kind: 'media',
      id: 'video-asset',
      type: 'video',
      name: '演示.mp4',
      url: 'http://assets.test/demo.mp4'
    };

    render(<AssetPreviewModal asset={asset} onClose={() => undefined} />);

    const video = screen.getByLabelText('演示.mp4 播放器') as HTMLVideoElement;
    expect(video.tagName).toBe('VIDEO');
    expect(video.controls).toBe(true);
  });

  it('renders PDF previews in the same dialog pattern', () => {
    const asset: PreviewAsset = {
      kind: 'document',
      id: 'pdf-doc',
      name: '报价说明.pdf',
      fileType: 'pdf',
      url: 'http://assets.test/quote.pdf'
    };

    render(<AssetPreviewModal asset={asset} onClose={() => undefined} downloadUrl={(url) => `${url}?download=1`} />);

    const frame = screen.getByTitle('报价说明.pdf 预览') as HTMLIFrameElement;
    expect(frame.getAttribute('src')).toBe('http://assets.test/quote.pdf');
    expect(screen.getByRole('link', { name: '下载原文件' }).getAttribute('href')).toBe('http://assets.test/quote.pdf?download=1');
  });

  it('closes from the dialog close action', () => {
    const onClose = vi.fn();
    const asset: PreviewAsset = {
      kind: 'media',
      id: 'image-asset',
      type: 'image',
      name: '效果图.png',
      url: 'http://assets.test/render.png'
    };

    render(<AssetPreviewModal asset={asset} onClose={onClose} />);

    fireEvent.click(screen.getByRole('button', { name: '关闭预览' }));

    expect(onClose).toHaveBeenCalled();
  });
});
