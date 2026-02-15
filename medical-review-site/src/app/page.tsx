'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { DoctorSelector } from '@/components/DoctorSelector';
import {
  getReviewerName,
  setReviewerName,
  getReviewCountForDoctor,
  getReviewsFromServer,
  downloadReviewsFromServer,
  downloadJudgeReviewsFromServer,
} from '@/lib/storage';
import { useI18n } from '@/lib/i18n';
import { Stethoscope, ArrowRight, Download, Activity, Users, Scale } from 'lucide-react';

export default function HomePage() {
  const router = useRouter();
  const { t } = useI18n();
  const [selectedDoctor, setSelectedDoctor] = useState('');
  const [myReviewCount, setMyReviewCount] = useState(0);
  const [totalReviewCount, setTotalReviewCount] = useState(0);
  const [mounted, setMounted] = useState(false);
  const [loadingCounts, setLoadingCounts] = useState(false);

  useEffect(() => {
    setMounted(true);
    const storedName = getReviewerName();
    if (storedName) {
      setSelectedDoctor(storedName);
    }
  }, []);

  useEffect(() => {
    if (selectedDoctor) {
      loadReviewCounts();
    }
  }, [selectedDoctor]);

  const loadReviewCounts = async () => {
    setLoadingCounts(true);
    try {
      const [myCount, allReviews] = await Promise.all([
        getReviewCountForDoctor(selectedDoctor),
        getReviewsFromServer(),
      ]);
      setMyReviewCount(myCount);
      setTotalReviewCount(allReviews.length);
    } catch (error) {
      console.error('Failed to load review counts:', error);
    } finally {
      setLoadingCounts(false);
    }
  };

  const handleDoctorSelect = (name: string) => {
    setSelectedDoctor(name);
    setReviewerName(name);
  };

  const handleStart = () => {
    if (selectedDoctor) {
      router.push('/cases');
    }
  };

  const handleExportMine = async () => {
    await downloadReviewsFromServer(selectedDoctor);
  };

  const handleExportAll = async () => {
    await downloadReviewsFromServer();
  };

  const handleExportJudgeMine = async () => {
    await downloadJudgeReviewsFromServer(selectedDoctor);
  };

  const handleExportJudgeAll = async () => {
    await downloadJudgeReviewsFromServer();
  };

  if (!mounted) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Activity className="h-5 w-5 animate-pulse" />
          {t('home.loading')}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[70vh] flex items-center justify-center px-4">
      <Card className="w-full max-w-md shadow-lg border-2">
        <CardHeader className="text-center space-y-4 pb-2">
          <div className="flex justify-center">
            <div className="p-4 rounded-full bg-gradient-to-br from-primary/20 to-primary/5 border border-primary/20">
              <Stethoscope className="h-10 w-10 text-primary" />
            </div>
          </div>
          <div className="space-y-2">
            <CardTitle className="text-2xl font-bold">{t('home.title')}</CardTitle>
            <CardDescription className="text-base">{t('home.subtitle')}</CardDescription>
          </div>
        </CardHeader>
        <CardContent className="space-y-6 pt-4">
          {/* Doctor Selector */}
          <div className="space-y-2">
            <label className="text-sm font-medium block text-center">
              {t('home.yourName')}
            </label>
            <DoctorSelector
              onSelect={handleDoctorSelect}
              selectedName={selectedDoctor}
            />
          </div>

          {/* Start Button */}
          <Button
            onClick={handleStart}
            disabled={!selectedDoctor}
            className="w-full h-12 text-base font-medium"
            size="lg"
          >
            {t('home.startReview')}
            <ArrowRight className="ml-2 h-5 w-5" />
          </Button>

          {/* Review Counts & Export */}
          {selectedDoctor && (
            <div className="pt-4 border-t space-y-4">
              {/* Review counts */}
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">{t('doctor.yourReviews')}</span>
                    <Badge variant="secondary" className="text-sm px-2">
                      {loadingCounts ? '...' : myReviewCount}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">{t('doctor.totalReviews')}</span>
                    <Badge variant="outline" className="text-sm px-2">
                      {loadingCounts ? '...' : totalReviewCount}
                    </Badge>
                  </div>
                </div>
              </div>

              {/* Export buttons - Doctor Reviews */}
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground font-medium">{t('home.exportReviews')}</p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    onClick={handleExportMine}
                    disabled={myReviewCount === 0}
                    className="flex-1"
                    size="sm"
                  >
                    <Download className="mr-2 h-4 w-4" />
                    {t('home.exportMine')}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={handleExportAll}
                    disabled={totalReviewCount === 0}
                    className="flex-1"
                    size="sm"
                  >
                    <Users className="mr-2 h-4 w-4" />
                    {t('home.exportAll')}
                  </Button>
                </div>
              </div>

              {/* Export buttons - Judge Reviews */}
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground font-medium">{t('home.exportJudgeReviews')}</p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    onClick={handleExportJudgeMine}
                    className="flex-1"
                    size="sm"
                  >
                    <Scale className="mr-2 h-4 w-4" />
                    {t('home.exportMine')}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={handleExportJudgeAll}
                    className="flex-1"
                    size="sm"
                  >
                    <Users className="mr-2 h-4 w-4" />
                    {t('home.exportAll')}
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* Info Footer */}
          <div className="text-center pt-4 border-t">
            <p className="text-sm text-muted-foreground">{t('home.info1')}</p>
            <p className="text-xs text-muted-foreground mt-1">{t('home.info2')}</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
