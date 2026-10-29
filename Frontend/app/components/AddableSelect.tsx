"use client";

import { useState } from "react";
import Combobox from "./Combobox";

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
            <Combobox
              id={`${id}-${index}`}
              name={name}
              value={value}
              onChange={(nuevo) => update(index, nuevo)}
              options={available}
              placeholder={placeholder}
              required={required && index === 0}
              invalid={rowInvalid}
              className="flex-1"
            />

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
