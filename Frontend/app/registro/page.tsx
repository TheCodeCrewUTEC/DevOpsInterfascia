"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import AddableSelect from "../components/AddableSelect";

const requiredFields = [
  "nombre",
  "apellido",
  "email",
  "contrasena",
  "contrasena2",
  "departamentoResidencia",
  "departamentoActuacion",
  "instituciones",
  "roles",
];

const departamentos = [
  "Artigas",
  "Canelones",
  "Cerro Largo",
  "Colonia",
  "Durazno",
  "Flores",
  "Florida",
  "Lavalleja",
  "Maldonado",
  "Montevideo",
  "Paysandú",
  "Río Negro",
  "Rivera",
  "Rocha",
  "Salto",
  "San José",
  "Soriano",
  "Tacuarembó",
  "Treinta y Tres",
];

const instituciones = [
  "UTEC",
  "UDELAR",
  "CURE",
  "UTU",
  "ANII",
  "Otra",
];

const roles = [
  "Administrador",
  "Gestor/a de innovación",
  "Investigador/a",
  "Emprendedor/a",
  "Representante de Empresa",
  "Otros",
];

const pasos = [
  { numero: "01", titulo: "Contá quién sos", texto: "Territorio, institución y el rol con el que participás." },
  { numero: "02", titulo: "Encontrá recursos", texto: "Convocatorias y proyectos relacionados con tu trabajo." },
  { numero: "03", titulo: "Sumate a la red", texto: "Investigadores e instituciones del mismo campo." },
];

function missingRequired(form: HTMLFormElement) {
  const data = new FormData(form);
  return requiredFields.filter((name) =>
    data.getAll(name).every((value) => String(value).trim() === ""),
  );
}

export default function RegistroPage() {
  const [attempted, setAttempted] = useState(false);
  const [empty, setEmpty] = useState<string[]>([]);

  function registrar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const missing = missingRequired(event.currentTarget);
    setAttempted(true);
    setEmpty(missing);

    if (missing.length === 0) return;

    const first = event.currentTarget.elements.namedItem(missing[0]);
    const field = first instanceof RadioNodeList ? first[0] : first;
    if (field instanceof HTMLElement) field.focus();
  }

  function actualizar(event: FormEvent<HTMLFormElement>) {
    if (!attempted) return;
    setEmpty(missingRequired(event.currentTarget));
  }

  function invalido(name: string) {
    return empty.includes(name);
  }

  return (
    <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10">
      <div className="grid items-start gap-6 lg:grid-cols-[0.85fr_1.15fr]">
        <aside className="relative overflow-hidden rounded-[2rem] bg-pine-deep px-8 py-10 text-paper lg:sticky lg:top-24">
          <div className="blob pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full bg-pine/30 blur-2xl" />
          <p className="relative text-xs font-medium tracking-[0.16em] text-gold uppercase">
            Registro
          </p>
          <h2 className="font-display relative mt-3 text-4xl leading-tight">
            Una cuenta para el territorio
          </h2>
          <p className="relative mt-4 text-sm leading-relaxed text-paper/75">
            Interfascia conecta proyectos, fondos y capacidades de investigación en Uruguay.
          </p>
          <ol className="relative mt-8 flex flex-col gap-4">
            {pasos.map((paso) => (
              <li key={paso.numero} className="rounded-2xl bg-white/10 p-4 ring-1 ring-white/10">
                <span className="font-display text-gold">{paso.numero}</span>
                <p className="mt-1 text-lg">{paso.titulo}</p>
                <p className="mt-1 text-sm text-paper/75">{paso.texto}</p>
              </li>
            ))}
          </ol>
        </aside>

        <section className="rounded-[2rem] bg-paper px-6 py-8 shadow-sm ring-1 ring-pine/10 sm:px-8">
          {empty.length > 0 ? (
            <p className="mb-4 text-sm font-medium text-red-600" role="alert">
              Los campos resaltados son obligatorios
            </p>
          ) : null}
          <h1 className="font-display text-4xl text-ink">Crea una cuenta</h1>
          <p className="mt-2 text-sm text-ink/70">
            Los campos con * son obligatorios.
          </p>

          <form className="mt-6 flex flex-col gap-4" onSubmit={registrar} onChange={actualizar} noValidate>
            <Field label="Nombre*" id="nombre" name="nombre" required invalid={invalido("nombre")} />
            <Field label="Apellido*" id="apellido" name="apellido" required invalid={invalido("apellido")} />
            <Field label="Email*" id="email" name="email" type="email" required invalid={invalido("email")} />
            <Field
              label="Contraseña*"
              id="contrasena"
              name="contrasena"
              type="password"
              required
              invalid={invalido("contrasena")}
            />
            <Field
              label="Ingresa nuevamente tu contraseña*"
              id="contrasena2"
              name="contrasena2"
              type="password"
              required
              invalid={invalido("contrasena2")}
            />

            <AddableSelect
              id="departamento-residencia"
              name="departamentoResidencia"
              label="Departamento de residencia"
              placeholder="Selecciona un departamento..."
              options={departamentos}
              required
              invalid={invalido("departamentoResidencia")}
            />

            <AddableSelect
              id="departamento-actuacion"
              name="departamentoActuacion"
              label="Departamento/s de actuación"
              placeholder="Selecciona un departamento..."
              options={departamentos}
              required
              invalid={invalido("departamentoActuacion")}
            />

            <Field label="Celular" id="celular" name="celular" type="tel" />

            <AddableSelect
              id="instituciones"
              name="instituciones"
              label="Instituciones"
              placeholder="Selecciona institución..."
              options={instituciones}
              required
              invalid={invalido("instituciones")}
            />

            <AddableSelect
              id="roles"
              name="roles"
              label="Rol/es"
              placeholder="Selecciona rol..."
              options={roles}
              required
              invalid={invalido("roles")}
            />

            <button
              type="submit"
              className="mt-2 rounded-full bg-pine py-3 text-sm font-medium text-ink shadow-sm transition duration-200 hover:-translate-y-0.5 hover:bg-pine-hover"
            >
              Registrate
            </button>

            <p className="text-center text-sm text-ink/70">
              ¿Ya tenés cuenta?{" "}
              <Link href="/login" className="text-pine-text underline-offset-4 hover:underline">
                Iniciar sesión
              </Link>
            </p>
          </form>
        </section>
      </div>
    </main>
  );
}

const campo =
  "h-11 rounded-xl border border-pine/20 bg-foam/70 px-3 text-sm text-ink outline-none transition focus:border-pine focus:bg-paper";

const campoInvalido =
  "h-11 rounded-xl border border-red-600 bg-red-50 px-3 text-sm text-ink outline-none transition focus:border-red-600";

function Field({
  label,
  id,
  name,
  type = "text",
  required = false,
  invalid = false,
}: {
  label: string;
  id: string;
  name: string;
  type?: string;
  required?: boolean;
  invalid?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className={invalid ? "text-sm text-red-600" : "text-sm text-ink"}>
        {label}
      </label>
      <input
        id={id}
        name={name}
        type={type}
        aria-invalid={invalid}
        aria-required={required}
        className={invalid ? campoInvalido : campo}
      />
    </div>
  );
}
