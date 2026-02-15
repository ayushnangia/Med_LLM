'use client';

import { getModelDisplayName, OPTIONAL_MODEL_IDS } from '@/lib/types';
import { setSelectedModels } from '@/lib/storage';
import { useI18n } from '@/lib/i18n';
import { cn } from '@/lib/utils';
import { CheckCircle } from 'lucide-react';

interface ModelSelectorProps {
  availableModels: string[];
  selectedModels: string[];
  onChange?: (selected: string[]) => void;
  reviewedModels?: Set<string>;
}

export function ModelSelector({
  availableModels,
  selectedModels,
  onChange,
  reviewedModels,
}: ModelSelectorProps) {
  const { t } = useI18n();

  const handleToggle = (modelId: string) => {
    let newSelected: string[];
    if (selectedModels.includes(modelId)) {
      newSelected = selectedModels.filter(m => m !== modelId);
    } else {
      newSelected = [...selectedModels, modelId];
    }
    setSelectedModels(newSelected);
    onChange?.(newSelected);
  };

  const handleSelectAll = () => {
    setSelectedModels(availableModels);
    onChange?.(availableModels);
  };

  const handleSelectNone = () => {
    setSelectedModels([]);
    onChange?.([]);
  };

  const allSelected = selectedModels.length === availableModels.length;
  const noneSelected = selectedModels.length === 0;
  const isOptional = (modelId: string) => (OPTIONAL_MODEL_IDS as readonly string[]).includes(modelId);
  const isReviewed = (modelId: string) => reviewedModels?.has(modelId) ?? false;

  return (
    <div className="p-3 bg-muted/50 rounded-lg">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium">{t('models.select')}</span>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">
            {selectedModels.length} / {availableModels.length}
          </span>
          <button
            onClick={handleSelectAll}
            disabled={allSelected}
            className="text-xs px-2 py-0.5 rounded border hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {t('models.all')}
          </button>
          <button
            onClick={handleSelectNone}
            disabled={noneSelected}
            className="text-xs px-2 py-0.5 rounded border hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {t('models.none')}
          </button>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {availableModels.map(modelId => {
          const isSelected = selectedModels.includes(modelId);
          const reviewed = isReviewed(modelId);
          const optional = isOptional(modelId);
          return (
            <button
              key={modelId}
              onClick={() => handleToggle(modelId)}
              className={cn(
                'px-3 py-1.5 text-sm rounded-md border transition-colors flex items-center gap-1.5',
                isSelected
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'bg-background hover:bg-muted border-border',
                reviewed && !isSelected && 'opacity-60'
              )}
            >
              {reviewed && <CheckCircle className="h-3.5 w-3.5 text-green-500" />}
              {isSelected && !reviewed && <span className="mr-0">&#10003;</span>}
              {getModelDisplayName(modelId)}
              {optional && (
                <span className="text-xs opacity-60 ml-1">{t('models.optional')}</span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
