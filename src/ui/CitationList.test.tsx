import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { CitationList } from './CitationList';
import type { Exhibit, GraphRagAnswer, GraphRagCitation } from '../types';

const exhibit: Exhibit = {
  id: 'thermal-studio',
  name: '热学互动台',
  category: '基础科学',
  theme: '热学',
  venueType: '儿童科技馆',
  budgetMin: 180000,
  budgetMax: 260000,
  materials: ['亚克力'],
  dimensions: '3000x1600x1800mm',
  interactions: ['动手实验'],
  supplier: '启思互动工坊',
  projectName: '青禾儿童科技馆更新项目',
  projectYear: 2025,
  owner: '青禾儿童科技馆',
  status: '制作中',
  reviewStatus: '待审核',
  description: '通过温差实验理解热传导。',
  tags: ['热学'],
  media: [],
  documents: [
    {
      id: 'thermal-plan',
      name: '热学方案.pdf',
      fileType: 'pdf',
      url: 'http://assets.test/thermal-plan.pdf',
      sourceNote: '方案资料'
    }
  ],
  relatedProjectIds: [],
  relatedExhibitIds: []
};

const citation: GraphRagCitation = {
  sourceId: 'thermal-plan',
  sourceType: 'document',
  title: '热学方案.pdf',
  snippet: '热学互动方案依据'
};

function answerWithCitation(): GraphRagAnswer {
  return {
    query: '热学',
    answer: '基于资料回答。',
    confidence: 0.8,
    warnings: [],
    citations: [citation],
    items: [
      {
        exhibit,
        score: 8,
        reasons: ['匹配资料：热学方案.pdf'],
        citations: [citation],
        graph: { nodes: [], edges: [] }
      }
    ]
  };
}

describe('CitationList', () => {
  it('renders clear citation source cards with exhibit ownership', () => {
    render(
      <CitationList
        answer={answerWithCitation()}
        citations={[citation]}
        onSelectCitation={() => undefined}
        downloadUrl={(url) => `${url}?download=1`}
      />
    );

    const card = screen.getByText('热学方案.pdf').closest('.graphrag-citation-card') as HTMLElement;
    expect(card).toBeTruthy();
    expect(within(card).getByText('来源类型：资料文档')).toBeTruthy();
    expect(within(card).queryByText('source_type: document')).toBeNull();
    expect(within(card).getByText('热学互动方案依据')).toBeTruthy();
    expect(within(card).getByText('对应展项：热学互动台')).toBeTruthy();
    expect(within(card).getByRole('link', { name: '打开资料' }).getAttribute('href')).toBe('http://assets.test/thermal-plan.pdf');
    expect(within(card).getByRole('link', { name: '下载资料' }).getAttribute('href')).toBe('http://assets.test/thermal-plan.pdf?download=1');
  });

  it('renders exhibit citations with a business-facing source type label', () => {
    const exhibitCitation: GraphRagCitation = {
      sourceId: exhibit.id,
      sourceType: 'exhibit',
      title: exhibit.name,
      snippet: exhibit.description
    };

    render(
      <CitationList
        answer={{
          ...answerWithCitation(),
          citations: [exhibitCitation],
          items: [{ ...answerWithCitation().items[0], citations: [exhibitCitation] }]
        }}
        citations={[exhibitCitation]}
        onSelectCitation={() => undefined}
        downloadUrl={(url) => `${url}?download=1`}
      />
    );

    const card = screen.getByText('热学互动台').closest('.graphrag-citation-card') as HTMLElement;
    expect(within(card).getByText('来源类型：展项档案')).toBeTruthy();
    expect(within(card).queryByText('source_type: exhibit')).toBeNull();
  });

  it('selects the citation from its card', () => {
    const onSelectCitation = vi.fn();
    render(
      <CitationList
        answer={answerWithCitation()}
        citations={[citation]}
        onSelectCitation={onSelectCitation}
        downloadUrl={(url) => `${url}?download=1`}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: '引用来源 [1] 热学方案.pdf' }));

    expect(onSelectCitation).toHaveBeenCalledWith(citation);
  });

  it('shows an empty citation state', () => {
    render(
      <CitationList
        answer={{ ...answerWithCitation(), citations: [] }}
        citations={[]}
        onSelectCitation={() => undefined}
        downloadUrl={(url) => `${url}?download=1`}
      />
    );

    expect(screen.getByText('暂无可引用来源')).toBeTruthy();
  });
});
