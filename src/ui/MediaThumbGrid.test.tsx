import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { MediaThumbGrid } from './MediaThumbGrid';
import type { MediaAsset } from '../types';

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
