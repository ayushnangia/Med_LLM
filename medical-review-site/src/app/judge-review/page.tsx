'use client';

import { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { getAllCases, getModelIds, getCaseCorrectCount } from '@/lib/data';
import { getJudgeReviewsFromServer, getReviewerName } from '@/lib/storage';
import { REQUIRED_MODEL_IDS, JUDGE_MODEL_IDS, getJudgeDisplayName } from '@/lib/types';
import { useI18n } from '@/lib/i18n';
import { Search, X, Filter, Scale, CheckCircle, ChevronRight } from 'lucide-react';
import { CountBadge } from '@/components/ScoreBadge';

type FilterType = 'all' | 'metastatic' | 'non-metastatic';

export default function JudgeReviewListPage() {
  const { t } = useI18n();
  const allCases = getAllCases();
  const modelIds = getModelIds();

  const [searchQuery, setSearchQuery] = useState('');
  const [filter, setFilter] = useState<FilterType>('all');
  const [showUnreviewedOnly, setShowUnreviewedOnly] = useState(true);
  const [judgeReviewedSet, setJudgeReviewedSet] = useState<Set<string>>(new Set());
  const [loadingReviews, setLoadingReviews] = useState(true);

  // Fetch all judge reviews for the current doctor
  useEffect(() => {
    const fetchReviews = async () => {
      const reviewerName = getReviewerName();
      if (!reviewerName) {
        setLoadingReviews(false);
        return;
      }

      try {
        const reviews = await getJudgeReviewsFromServer({ doctor: reviewerName });
        const set = new Set<string>();
        for (const review of reviews) {
          // Key: case_id__model_id__judge_model
          set.add(`${review.case_id}__${review.model_id}__${review.judge_model}`);
        }
        setJudgeReviewedSet(set);
      } catch (error) {
        console.error('Failed to load judge reviews:', error);
      } finally {
        setLoadingReviews(false);
      }
    };

    fetchReviews();
  }, []);

  // Total expected judge reviews per case: required_models × judges (that have evaluations)
  const caseJudgeStats = useMemo(() => {
    const map = new Map<string, { reviewed: number; total: number }>();
    for (const caseItem of allCases) {
      let total = 0;
      let reviewed = 0;
      for (const modelId of REQUIRED_MODEL_IDS) {
        const pred = caseItem.predictions[modelId];
        if (!pred) continue;
        const judgeIds = pred.judge_evaluations
          ? Object.keys(pred.judge_evaluations)
          : [];
        for (const judgeId of judgeIds) {
          total++;
          if (judgeReviewedSet.has(`${caseItem.case_id}__${modelId}__${judgeId}`)) {
            reviewed++;
          }
        }
      }
      map.set(caseItem.case_id, { reviewed, total });
    }
    return map;
  }, [allCases, judgeReviewedSet]);

  const filteredCases = useMemo(() => {
    let cases = allCases;

    if (filter === 'metastatic') {
      cases = cases.filter(c => c.ground_truth.metastatic);
    } else if (filter === 'non-metastatic') {
      cases = cases.filter(c => !c.ground_truth.metastatic);
    }

    if (showUnreviewedOnly && !loadingReviews) {
      cases = cases.filter(c => {
        const stats = caseJudgeStats.get(c.case_id);
        return stats && stats.reviewed < stats.total;
      });
    }

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      cases = cases.filter(
        c =>
          c.case_id.toLowerCase().includes(query) ||
          c.patient.name.toLowerCase().includes(query) ||
          c.diagnosis.diagnose_kurz.toLowerCase().includes(query)
      );
    }

    // Sort by most unreviewed first
    if (showUnreviewedOnly && !loadingReviews) {
      cases = [...cases].sort((a, b) => {
        const aStats = caseJudgeStats.get(a.case_id);
        const bStats = caseJudgeStats.get(b.case_id);
        const aRemaining = (aStats?.total ?? 0) - (aStats?.reviewed ?? 0);
        const bRemaining = (bStats?.total ?? 0) - (bStats?.reviewed ?? 0);
        return bRemaining - aRemaining;
      });
    }

    return cases;
  }, [allCases, filter, searchQuery, showUnreviewedOnly, loadingReviews, caseJudgeStats]);

  const metastaticCount = allCases.filter(c => c.ground_truth.metastatic).length;
  const nonMetastaticCount = allCases.length - metastaticCount;

  const totalRemaining = Array.from(caseJudgeStats.values()).reduce(
    (sum, s) => sum + (s.total - s.reviewed), 0
  );
  const casesWithRemaining = Array.from(caseJudgeStats.values()).filter(
    s => s.reviewed < s.total
  ).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
          <Scale className="h-8 w-8 text-purple-600" />
          {t('judgeList.title')}
        </h1>
        <p className="text-muted-foreground mt-2">
          {t('judgeList.subtitle', { count: allCases.length, judges: String(JUDGE_MODEL_IDS.length) })}
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
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

      {/* Unreviewed toggle + progress */}
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
              {t('judgeList.remaining', { cases: casesWithRemaining, count: totalRemaining })}
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
        </div>
      )}

      {/* Cards Grid */}
      {filteredCases.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredCases.map(caseItem => {
            const stats = caseJudgeStats.get(caseItem.case_id);
            const reviewed = stats?.reviewed ?? 0;
            const total = stats?.total ?? 0;
            const allDone = total > 0 && reviewed >= total;
            const correctCount = getCaseCorrectCount(caseItem);
            const totalModels = Object.keys(caseItem.predictions).length;

            return (
              <Link key={caseItem.case_id} href={`/judge-review/${caseItem.case_id}`}>
                <Card className={`hover:border-purple-400 transition-colors cursor-pointer h-full ${allDone ? 'opacity-60' : ''}`}>
                  <CardHeader className="pb-2">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <CardTitle className="text-lg">{caseItem.case_id}</CardTitle>
                        {allDone && (
                          <CheckCircle className="h-4 w-4 text-green-600" />
                        )}
                      </div>
                      <div className="flex items-center gap-1">
                        <Badge
                          variant={allDone ? 'secondary' : 'outline'}
                          className={`text-xs ${!allDone ? 'border-purple-400 text-purple-700 dark:text-purple-400' : ''}`}
                        >
                          {allDone
                            ? t('cases.allReviewed')
                            : `${reviewed}/${total}`}
                        </Badge>
                        <CountBadge correct={correctCount} total={totalModels} />
                      </div>
                    </div>
                    <p className="text-sm text-muted-foreground">{caseItem.patient.name}</p>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {/* Patient Info */}
                    <div className="flex flex-wrap gap-2 text-sm">
                      {caseItem.patient.age && (
                        <Badge variant="outline">{caseItem.patient.age} Jahre</Badge>
                      )}
                      {caseItem.patient.ecog !== null && (
                        <Badge variant="outline">ECOG {caseItem.patient.ecog}</Badge>
                      )}
                    </div>

                    {/* Diagnosis */}
                    <div className="space-y-1">
                      <p className="text-sm font-medium line-clamp-2">
                        {caseItem.diagnosis.diagnose_kurz}
                      </p>
                      <div className="flex flex-wrap gap-2">
                        <Badge variant={caseItem.ground_truth.metastatic ? 'destructive' : 'secondary'}>
                          {caseItem.ground_truth.metastatic ? t('cases.metastatic') : t('cases.nonMetastatic')}
                        </Badge>
                      </div>
                    </div>

                    {/* Judge progress per judge model */}
                    <div className="pt-2 border-t space-y-1">
                      <p className="text-xs text-muted-foreground">{t('judgeList.judgeProgress')}</p>
                      {JUDGE_MODEL_IDS.map(judgeId => {
                        let judgeTotal = 0;
                        let judgeReviewed = 0;
                        for (const modelId of REQUIRED_MODEL_IDS) {
                          const pred = caseItem.predictions[modelId];
                          if (!pred?.judge_evaluations?.[judgeId]) continue;
                          judgeTotal++;
                          if (judgeReviewedSet.has(`${caseItem.case_id}__${modelId}__${judgeId}`)) {
                            judgeReviewed++;
                          }
                        }
                        if (judgeTotal === 0) return null;
                        const done = judgeReviewed >= judgeTotal;
                        return (
                          <div key={judgeId} className="flex items-center justify-between text-xs">
                            <span className="text-muted-foreground">{getJudgeDisplayName(judgeId)}</span>
                            <Badge
                              variant={done ? 'secondary' : 'outline'}
                              className={`text-xs ${done ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : ''}`}
                            >
                              {judgeReviewed}/{judgeTotal}
                            </Badge>
                          </div>
                        );
                      })}
                    </div>

                    {/* Progress bar */}
                    {total > 0 && (
                      <div className="pt-1">
                        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                          <div
                            className={`h-1.5 rounded-full transition-all ${allDone ? 'bg-green-500' : 'bg-purple-500'}`}
                            style={{ width: `${(reviewed / total) * 100}%` }}
                          />
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </Link>
            );
          })}
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
