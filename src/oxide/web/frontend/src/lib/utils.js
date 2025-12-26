/**
 * Utility functions
 */

/**
 * Merges className strings with tailwind-merge for proper Tailwind class handling
 * @param {...string} classes - Class names to merge
 * @returns {string} Merged class names
 */
export function cn(...classes) {
  return classes.filter(Boolean).join(' ');
}

/**
 * Format duration in seconds to human-readable format
 * @param {number} duration - Duration in seconds
 * @returns {string} Formatted duration
 */
export function formatDuration(duration) {
  if (!duration) return 'N/A';
  if (duration < 1) return `${(duration * 1000).toFixed(0)}ms`;
  if (duration < 60) return `${duration.toFixed(2)}s`;
  const minutes = Math.floor(duration / 60);
  const seconds = Math.floor(duration % 60);
  return `${minutes}m ${seconds}s`;
}

/**
 * Format timestamp to human-readable time
 * @param {number} timestamp - Unix timestamp
 * @returns {string} Formatted time
 */
export function formatTimestamp(timestamp) {
  if (!timestamp) return 'N/A';
  const date = new Date(timestamp * 1000);
  return date.toLocaleTimeString();
}

/**
 * Get color based on percentage value
 * @param {number} percent - Percentage value
 * @param {Object} thresholds - Color thresholds
 * @returns {string} Tailwind color class
 */
export function getPercentageColor(percent, thresholds = { low: 50, medium: 75 }) {
  if (!percent) return 'text-gh-success';
  if (percent < thresholds.low) return 'text-gh-success';
  if (percent < thresholds.medium) return 'text-gh-attention';
  return 'text-gh-danger';
}
