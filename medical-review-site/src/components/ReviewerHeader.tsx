'use client';

import { useState, useEffect } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useI18n } from '@/lib/i18n';
import { User } from 'lucide-react';

const STORAGE_KEY = 'medical-review-reviewer-name';

export function ReviewerHeader() {
  const { t } = useI18n();
  const [name, setName] = useState<string>('');
  const [isEditing, setIsEditing] = useState(false);
  const [inputValue, setInputValue] = useState('');

  useEffect(() => {
    const storedName = localStorage.getItem(STORAGE_KEY);
    if (storedName) {
      setName(storedName);
    } else {
      setIsEditing(true);
    }
  }, []);

  const handleSave = () => {
    if (inputValue.trim()) {
      localStorage.setItem(STORAGE_KEY, inputValue.trim());
      setName(inputValue.trim());
      setIsEditing(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSave();
    }
  };

  if (isEditing) {
    return (
      <div className="flex items-center gap-2">
        <Input
          placeholder={t('home.namePlaceholder')}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          className="w-48"
          autoFocus
        />
        <Button onClick={handleSave} size="sm">
          {t('review.save')}
        </Button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <Badge variant="secondary" className="flex items-center gap-1 px-3 py-1">
        <User className="h-3 w-3" />
        {name}
      </Badge>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => {
          setInputValue(name);
          setIsEditing(true);
        }}
      >
        {t('nav.change')}
      </Button>
    </div>
  );
}
