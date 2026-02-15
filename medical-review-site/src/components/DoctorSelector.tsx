'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  getDoctorsFromServer,
  registerDoctor,
  getReviewerName,
  setReviewerName,
  DoctorInfo,
} from '@/lib/storage';
import { useI18n } from '@/lib/i18n';
import { User, UserPlus, ChevronDown, Check } from 'lucide-react';
import { cn } from '@/lib/utils';

interface DoctorSelectorProps {
  onSelect: (name: string) => void;
  selectedName?: string;
}

export function DoctorSelector({ onSelect, selectedName }: DoctorSelectorProps) {
  const { t } = useI18n();
  const [doctors, setDoctors] = useState<DoctorInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [isOpen, setIsOpen] = useState(false);
  const [showNewDoctor, setShowNewDoctor] = useState(false);
  const [newDoctorName, setNewDoctorName] = useState('');
  const [registering, setRegistering] = useState(false);

  useEffect(() => {
    loadDoctors();
  }, []);

  const loadDoctors = async () => {
    try {
      const data = await getDoctorsFromServer();
      setDoctors(data);
    } catch (error) {
      console.error('Failed to load doctors:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectDoctor = (name: string) => {
    setReviewerName(name);
    onSelect(name);
    setIsOpen(false);
  };

  const handleRegisterDoctor = async () => {
    if (!newDoctorName.trim()) return;

    const trimmedName = newDoctorName.trim();
    setRegistering(true);

    try {
      const doctor = await registerDoctor(trimmedName);
      setDoctors(prev => {
        // Avoid duplicates
        if (prev.some(d => d.name === doctor.name)) return prev;
        return [...prev, doctor];
      });
      setReviewerName(doctor.name);
      onSelect(doctor.name);
    } catch (error) {
      console.error('Failed to register doctor on server:', error);
      // Fallback: just use the name locally even if server fails
      setDoctors(prev => {
        if (prev.some(d => d.name === trimmedName)) return prev;
        return [...prev, { name: trimmedName, reviewCount: 0 }];
      });
      setReviewerName(trimmedName);
      onSelect(trimmedName);
    } finally {
      setNewDoctorName('');
      setShowNewDoctor(false);
      setIsOpen(false);
      setRegistering(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleRegisterDoctor();
    } else if (e.key === 'Escape') {
      setShowNewDoctor(false);
      setNewDoctorName('');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <User className="h-4 w-4 animate-pulse" />
        {t('home.loading')}
      </div>
    );
  }

  return (
    <div className="relative">
      <Button
        variant="outline"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full justify-between"
      >
        <span className="flex items-center gap-2">
          <User className="h-4 w-4" />
          {selectedName || t('doctor.selectDoctor')}
        </span>
        <ChevronDown className={cn('h-4 w-4 transition-transform', isOpen && 'rotate-180')} />
      </Button>

      {isOpen && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-background border rounded-md shadow-lg z-50 max-h-64 overflow-auto">
          {doctors.length > 0 && (
            <div className="p-1">
              {doctors.map((doctor) => (
                <button
                  key={doctor.name}
                  onClick={() => handleSelectDoctor(doctor.name)}
                  className={cn(
                    'w-full flex items-center justify-between px-3 py-2 text-sm rounded hover:bg-muted transition-colors',
                    selectedName === doctor.name && 'bg-muted'
                  )}
                >
                  <span className="flex items-center gap-2">
                    <User className="h-4 w-4" />
                    {doctor.name}
                  </span>
                  <span className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">
                      {doctor.reviewCount} {t('doctor.reviews')}
                    </span>
                    {selectedName === doctor.name && (
                      <Check className="h-4 w-4 text-primary" />
                    )}
                  </span>
                </button>
              ))}
            </div>
          )}

          <div className="border-t p-2">
            {showNewDoctor ? (
              <div className="space-y-2">
                <Input
                  placeholder={t('home.namePlaceholder')}
                  value={newDoctorName}
                  onChange={(e) => setNewDoctorName(e.target.value)}
                  onKeyDown={handleKeyDown}
                  autoFocus
                />
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    onClick={handleRegisterDoctor}
                    disabled={!newDoctorName.trim() || registering}
                    className="flex-1"
                  >
                    {registering ? t('home.loading') : t('doctor.register')}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setShowNewDoctor(false);
                      setNewDoctorName('');
                    }}
                  >
                    {t('doctor.cancel')}
                  </Button>
                </div>
              </div>
            ) : (
              <Button
                variant="ghost"
                className="w-full justify-start"
                onClick={() => setShowNewDoctor(true)}
              >
                <UserPlus className="h-4 w-4 mr-2" />
                {t('doctor.addNew')}
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
