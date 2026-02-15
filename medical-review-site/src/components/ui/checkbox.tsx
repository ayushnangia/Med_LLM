'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { Check } from 'lucide-react';

export interface CheckboxProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, label, id, ...props }, ref) => {
    const inputId = id || React.useId();

    return (
      <div className="flex items-center space-x-2">
        <div className="relative">
          <input
            type="checkbox"
            ref={ref}
            id={inputId}
            className="peer sr-only"
            {...props}
          />
          <div
            className={cn(
              'h-4 w-4 shrink-0 rounded-sm border border-primary ring-offset-background',
              'peer-focus-visible:outline-none peer-focus-visible:ring-2 peer-focus-visible:ring-ring peer-focus-visible:ring-offset-2',
              'peer-disabled:cursor-not-allowed peer-disabled:opacity-50',
              'peer-checked:bg-primary peer-checked:text-primary-foreground',
              'flex items-center justify-center cursor-pointer',
              className
            )}
            onClick={() => {
              const input = document.getElementById(inputId) as HTMLInputElement;
              if (input && !input.disabled) {
                input.click();
              }
            }}
          >
            <Check
              className={cn(
                'h-3 w-3 text-current opacity-0 peer-checked:opacity-100',
                'hidden'
              )}
            />
          </div>
          <Check
            className="absolute top-0.5 left-0.5 h-3 w-3 text-primary-foreground opacity-0 peer-checked:opacity-100 pointer-events-none"
          />
        </div>
        {label && (
          <label
            htmlFor={inputId}
            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
          >
            {label}
          </label>
        )}
      </div>
    );
  }
);
Checkbox.displayName = 'Checkbox';

export { Checkbox };
