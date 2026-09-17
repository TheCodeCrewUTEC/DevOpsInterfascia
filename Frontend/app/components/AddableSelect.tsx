"use client";

import { useState } from "react";

interface AddableSelectProps {
  id: string;
  name: string;
  label: string;
  placeholder: string;
  options: string[];
  required?: boolean;
}

export default function AddableSelect({
  id,
  name,
  label,
  placeholder,
  options,
  required = false,
}: AddableSelectProps) {
  const [count, setCount] = useState(1);

  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={`${id}-0`} className="text-xs text-black">
        {label}
        {required ? "*" : ""}
      </label>

      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="flex items-center gap-1.5">
          <select
            id={`${id}-${index}`}
            name={index === 0 ? name : `${name}-${index}`}
            className="h-8 flex-1 border border-black bg-neutral-300 px-2 text-sm text-black outline-none"
            required={required && index === 0}
            defaultValue=""
          >
            <option value="" disabled>
              {placeholder}
            </option>
            {options.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>

          {index === count - 1 && (
            <button
              type="button"
              onClick={() => setCount((value) => value + 1)}
              className="flex h-8 w-8 shrink-0 items-center justify-center border border-black bg-neutral-300 text-lg text-black"
              aria-label="Agregar otro"
            >
              +
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
