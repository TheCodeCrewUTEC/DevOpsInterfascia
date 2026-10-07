"use client";

import { useState } from "react";

const chevron =
  "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' fill='none' stroke='%23102a3c' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M5 7.5 10 12.5 15 7.5'/%3E%3C/svg%3E\")";

interface AddableSelectProps {
  id: string;
  name: string;
  label: string;
  placeholder: string;
  options: string[];
  required?: boolean;
  invalid?: boolean;
  defaultValues?: string[];
}

export default function AddableSelect({
  id,
  name,
  label,
  placeholder,
  options,
  required = false,
  invalid = false,
  defaultValues = [],
}: AddableSelectProps) {
  const [values, setValues] = useState<string[]>(defaultValues.length > 0 ? defaultValues : [""]);

  const selected = new Set(values.filter((value) => value !== ""));
  const canAdd =
    values.every((value) => value !== "") && selected.size < options.length;

  function update(index: number, value: string) {
    setValues((current) =>
      current.map((item, itemIndex) => (itemIndex === index ? value : item)),
    );
  }

  function add() {
    setValues((current) => [...current, ""]);
  }

  function remove(index: number) {
    setValues((current) => {
      const next = current.filter((_, itemIndex) => itemIndex !== index);
      return next.length > 0 ? next : [""];
    });
  }

  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={`${id}-0`} className={invalid ? "text-sm text-red-600" : "text-sm text-ink"}>
        {label}
        {required ? "*" : ""}
      </label>

      {values.map((value, index) => {
        const available = options.filter(
          (option) => option === value || !selected.has(option),
        );
        const canRemove = value !== "" || values.length > 1;
        const rowInvalid = invalid && value === "";

        return (
          <div key={`${id}-${index}`} className="flex items-center gap-3">
            <select
              key={`${id}-${index}-${value}`}
              id={`${id}-${index}`}
              name={name}
              value={value}
              onChange={(event) => update(index, event.target.value)}
              aria-invalid={rowInvalid}
              aria-required={required && index === 0}
              className={
                rowInvalid
                  ? "h-11 flex-1 appearance-none rounded-xl border border-red-600 bg-red-50 bg-[length:16px] bg-[position:right_1.25rem_center] bg-no-repeat px-4 pr-14 text-sm text-ink outline-none transition focus:border-red-600"
                  : "h-11 flex-1 appearance-none rounded-xl border border-pine/20 bg-foam/70 bg-[length:16px] bg-[position:right_1.25rem_center] bg-no-repeat px-4 pr-14 text-sm text-ink outline-none transition focus:border-pine focus:bg-paper"
              }
              style={{ backgroundImage: chevron }}
            >
              <option value="" disabled>
                {placeholder}
              </option>
              {available.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>

            {canRemove ? (
              <button
                type="button"
                onClick={() => remove(index)}
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-clay/30 text-lg text-clay transition hover:bg-clay/10"
                aria-label={`Quitar ${value || "selección"}`}
              >
                ×
              </button>
            ) : null}

            {index === values.length - 1 && canAdd ? (
              <button
                type="button"
                onClick={add}
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-pine text-lg text-ink transition hover:bg-pine-hover"
                aria-label="Agregar otro"
              >
                +
              </button>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
