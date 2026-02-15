'use client';

import { useState, useEffect, useMemo } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { CaseCard } from '@/components/CaseCard';
import { getAllCases, getModelIds } from '@/lib/data';
import { getReviewsFromServer, getReviewerName } from '@/lib/storage';
import { REQUIRED_MODEL_IDS } from '@/lib/types';
import { useI18n } from '@/lib/i18n';
import { Search, X, Filter } from 'lucide-react';

type FilterType = 'all' | 'metastatic' | 'non-metastatic';

export default function CasesPage() {
  const { t } = useI18n();
  const allCases = getAllCases();
  const modelIds = getModelIds();

  const [searchQuery, setSearchQuery] = useState('');
  const [filter, setFilter] = useState<FilterType>('all');
  const [showUnreviewedOnly, setShowUnreviewedOnly] = useState(true);
  const [reviewedSet, setReviewedSet] = useState<Set<string>>(new Set());
  const [loadingReviews, setLoadingReviews] = useState(true);

  // Fetch all reviews for the current doctor on mount
  useEffect(() => {
    const fetchReviews = async () => {
      const reviewerName = getReviewerName();
      if (!reviewerName) {
        setLoadingReviews(false);
        return;
      }

      try {
        const reviews = await getReviewsFromServer({ doctor: reviewerName });
        const set = new Set<string>();
        for (const review of reviews) {
          set.add(`${review.case_id}__${review.model_id}`);
        }
        setReviewedSet(set);
      } catch (error) {
        console.error('Failed to load reviews:', error);
      } finally {
        setLoadingReviews(false);
      }
    };

    fetchReviews();
  }, []);

  // Compute unreviewed count per case
  const caseUnreviewedMap = useMemo(() => {
    const map = new Map<string, number>();
    for (const caseItem of allCases) {
      const availableRequired = REQUIRED_MODEL_IDS.filter(
        modelId => caseItem.predictions[modelId]
      );
      const reviewedCount = availableRequired.filter(
        modelId => reviewedSet.has(`${caseItem.case_id}__${modelId}`)
      ).length;
      map.set(caseItem.case_id, availableRequired.length - reviewedCount);
    }
    return map;
  }, [allCases, reviewedSet]);

  // Compute reviewed required count per case (for progress display)
  const caseReviewedRequiredMap = useMemo(() => {
    const map = new Map<string, number>();
    for (const caseItem of allCases) {
      const availableRequired = REQUIRED_MODEL_IDS.filter(
        modelId => caseItem.predictions[modelId]
      );
      const reviewedCount = availableRequired.filter(
        modelId => reviewedSet.has(`${caseItem.case_id}__${modelId}`)
      ).length;
      map.set(caseItem.case_id, reviewedCount);
    }
    return map;
  }, [allCases, reviewedSet]);

  const filteredCases = useMemo(() => {
    let cases = allCases;

    // Filter by metastatic status
    if (filter === 'metastatic') {
      cases = cases.filter(c => c.ground_truth.metastatic);
    } else if (filter === 'non-metastatic') {
      cases = cases.filter(c => !c.ground_truth.metastatic);
    }

    // Filter by unreviewed only
    if (showUnreviewedOnly && !loadingReviews) {
      cases = cases.filter(c => (caseUnreviewedMap.get(c.case_id) ?? 0) > 0);
    }

    // Search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      cases = cases.filter(
        c =>
          c.case_id.toLowerCase().includes(query) ||
          c.patient.name.toLowerCase().includes(query) ||
          c.diagnosis.diagnose_kurz.toLowerCase().includes(query)
      );
    }

    // Sort by most unreviewed first when filter is active
    if (showUnreviewedOnly && !loadingReviews) {
      cases = [...cases].sort((a, b) => {
        const aUnreviewed = caseUnreviewedMap.get(a.case_id) ?? 0;
        const bUnreviewed = caseUnreviewedMap.get(b.case_id) ?? 0;
        return bUnreviewed - aUnreviewed;
      });
    }

    return cases;
  }, [allCases, filter, searchQuery, showUnreviewedOnly, loadingReviews, caseUnreviewedMap]);

  const metastaticCount = allCases.filter(c => c.ground_truth.metastatic).length;
  const nonMetastaticCount = allCases.length - metastaticCount;

  // Summary stats
  const totalUnreviewed = Array.from(caseUnreviewedMap.values()).reduce((sum, n) => sum + n, 0);
  const casesWithUnreviewed = Array.from(caseUnreviewedMap.values()).filter(n => n > 0).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">{t('cases.title')}</h1>
        <p className="text-muted-foreground mt-2">
          {t('cases.subtitle', { count: allCases.length, models: modelIds.length })}
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder={t('cases.search')}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
          {searchQuery && (
            <Button
              variant="ghost"
              size="sm"
              className="absolute right-1 top-1/2 transform -translate-y-1/2 h-7 w-7 p-0"
              onClick={() => setSearchQuery('')}
            >
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>

        {/* Filter Buttons */}
        <div className="flex gap-2 flex-wrap">
          <Button
            variant={filter === 'all' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter('all')}
          >
            {t('cases.all')} ({allCases.length})
          </Button>
          <Button
            variant={filter === 'metastatic' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter('metastatic')}
          >
            {t('cases.metastatic')} ({metastaticCount})
          </Button>
          <Button
            variant={filter === 'non-metastatic' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter('non-metastatic')}
          >
            {t('cases.nonMetastatic')} ({nonMetastaticCount})
          </Button>
        </div>
      </div>

      {/* Unreviewed toggle + progress summary */}
      {!loadingReviews && (
        <div className="flex items-center justify-between flex-wrap gap-3">
          <Button
            variant={showUnreviewedOnly ? 'default' : 'outline'}
            size="sm"
            onClick={() => setShowUnreviewedOnly(!showUnreviewedOnly)}
          >
            <Filter className="h-4 w-4 mr-1.5" />
            {showUnreviewedOnly ? t('cases.showUnreviewed') : t('cases.showAll')}
          </Button>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Badge variant="secondary">
              {t('cases.remaining', { cases: casesWithUnreviewed, count: totalUnreviewed })}
            </Badge>
          </div>
        </div>
      )}

      {/* Results Count */}
      {(searchQuery || filter !== 'all') && (
        <div className="flex items-center gap-2">
          <Badge variant="secondary">
            {t('cases.results', { count: filteredCases.length })}
          </Badge>
          {filter !== 'all' && (
            <Badge variant="outline">
              {t('cases.filter')} {filter === 'metastatic' ? t('cases.metastatic') : t('cases.nonMetastatic')}
            </Badge>
          )}
        </div>
      )}

      {/* Cases Grid */}
      {filteredCases.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredCases.map(caseItem => (
            <CaseCard
              key={caseItem.case_id}
              caseItem={caseItem}
              reviewedRequiredCount={caseReviewedRequiredMap.get(caseItem.case_id) ?? 0}
              totalRequiredCount={REQUIRED_MODEL_IDS.filter(m => caseItem.predictions[m]).length}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <p className="text-muted-foreground">{t('cases.noResults')}</p>
          <Button
            variant="link"
            onClick={() => {
              setSearchQuery('');
              setFilter('all');
              setShowUnreviewedOnly(false);
            }}
          >
            {t('cases.resetFilter')}
          </Button>
        </div>
      )}
    </div>
  );
}
