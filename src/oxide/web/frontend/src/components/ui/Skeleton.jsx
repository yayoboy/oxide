/**
 * Skeleton Component
 * Loading placeholder with shimmer animation
 */
import React from 'react';
import { cn } from '../../lib/utils';

export const Skeleton = ({ className, ...props }) => {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-lg bg-white/10",
        "before:absolute before:inset-0",
        "before:-translate-x-full before:animate-shimmer",
        "before:bg-gradient-to-r before:from-transparent before:via-white/10 before:to-transparent",
        className
      )}
      {...props}
    />
  );
};

export const SkeletonText = ({ lines = 3, className }) => (
  <div className={cn("space-y-2", className)}>
    {Array.from({ length: lines }).map((_, i) => (
      <Skeleton
        key={i}
        className={cn(
          "h-4",
          i === lines - 1 && "w-3/4", // Last line shorter
          i !== lines - 1 && "w-full"
        )}
      />
    ))}
  </div>
);

export const SkeletonCard = ({ className }) => (
  <div className={cn("glass rounded-xl p-4 space-y-4", className)}>
    <div className="flex items-center gap-4">
      <Skeleton className="w-12 h-12 rounded-full" />
      <div className="flex-1 space-y-2">
        <Skeleton className="h-4 w-1/2" />
        <Skeleton className="h-3 w-3/4" />
      </div>
    </div>
    <SkeletonText lines={3} />
  </div>
);

export default Skeleton;
