/**
 * Select Component
 * Dropdown select for choosing options
 */
import React, { useState, useRef, useEffect } from 'react';
import { cn } from '../../lib/utils';

export const Select = ({ value, onValueChange, children, placeholder = "Select..." }) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Extract options from children
  const options = React.Children.toArray(children);
  const selectedOption = options.find(child => child.props.value === value);

  return (
    <div ref={containerRef} className="relative inline-block w-full">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "w-full glass rounded-lg px-4 py-2 text-left",
          "border border-white/10 hover:border-white/20",
          "transition-colors duration-200",
          "flex items-center justify-between gap-2"
        )}
      >
        <span className={cn(
          "truncate",
          selectedOption ? 'text-white' : 'text-gh-fg-muted'
        )}>
          {selectedOption ? selectedOption.props.children : placeholder}
        </span>
        <span className={cn(
          "text-gh-fg-muted transform transition-transform",
          isOpen && "rotate-180"
        )}>
          ▼
        </span>
      </button>

      {isOpen && (
        <div className={cn(
          "absolute z-50 w-full mt-2",
          "glass rounded-lg border border-white/10",
          "shadow-xl overflow-hidden",
          "animate-fade-in"
        )}>
          {options.map((option) => (
            <SelectItem
              key={option.props.value}
              value={option.props.value}
              onSelect={(val) => {
                onValueChange(val);
                setIsOpen(false);
              }}
              isSelected={option.props.value === value}
            >
              {option.props.children}
            </SelectItem>
          ))}
        </div>
      )}
    </div>
  );
};

export const SelectItem = ({ value, onSelect, isSelected, children }) => {
  return (
    <button
      type="button"
      onClick={() => onSelect(value)}
      className={cn(
        "w-full px-4 py-2 text-left",
        "hover:bg-white/10 transition-colors",
        "text-white",
        isSelected && "bg-cyan-500/20 text-cyan-400"
      )}
    >
      {children}
    </button>
  );
};

export const SelectTrigger = ({ children }) => children;
export const SelectContent = ({ children }) => children;
export const SelectValue = ({ children }) => children;

export default Select;
