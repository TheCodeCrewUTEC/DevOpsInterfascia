"use client";

import { useState } from "react";

const resultados = [
  {
    tipo: "Convocatoria",
    icono: "📢",
    titulo: "Validación de Idea de Negocio",
    descripcion:
      "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Vivamus at facilisis arcu, finibus auctor arcu.",
    estado: "Abierto",
    detalle: "Cierre: 16/10/2026",
  },
  {
    tipo: "Proyecto",
    icono: "📄",
    titulo: "Bio-contenedores de raíces Biocamarfa",
    descripcion:
      "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Vivamus at facilisis arcu, finibus auctor arcu.",
    estado: "Seguimiento",
    detalle: "Año: 2020",
  },
  {
    tipo: "Convocatoria",
    icono: "📢",
    titulo: "Fondos para I+D territorial",
    descripcion:
      "Phasellus eros mi, maximus et tellus vel, lacinia aliquet risus. Etiam faucibus laoreet placerat.",
    estado: "Abierto",
    detalle: "Cierre: 30/11/2026",
  },
  {
    tipo: "Proyecto",
    icono: "📄",
    titulo: "Innovación agropecuaria",
    descripcion:
      "Aenean a ante nisi. Phasellus eros mi, maximus et tellus vel, lacinia aliquet risus.",
    estado: "Seguimiento",
    detalle: "Año: 2024",
  },
];

const investigadores = [
  {
    nombre: "María Jesús Lopez",
    institucion: "UDELAR",
    ocupacion: "Psicologa",
    area: "Psicología",
  },
  {
    nombre: "Benito Perez",
    institucion: "UTEC",
    ocupacion: "Lic. en IT",
    area: "Tecnologías de la Información",
  },
  {
    nombre: "Ana Rodríguez",
    institucion: "CURE",
    ocupacion: "Estudiante",
    area: "Ciencias ambientales",
  },
  {
    nombre: "Carlos Méndez",
    institucion: "ANII",
    ocupacion: "Inversor",
    area: "Emprendimientos",
  },
];

export default function ConsultorIAPage() {
  const [formulario, setFormulario] = useState<File | null>(null);
  const [documentos, setDocumentos] = useState<File[]>([]);

  const [subiendo, setSubiendo] = useState(false);
  const [jobId, setJobId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFormularioChange = (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const archivo = event.target.files?.[0] ?? null;

    setFormulario(archivo);
    setError(null);
  };

  const handleDocumentosChange = (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const archivos = Array.from(event.target.files ?? []);

    setDocumentos(archivos);
    setError(null);
  };

  const handleSubir = async () => {
    setError(null);
    setJobId(null);

    if (!formulario) {
      setError("Debe seleccionar un formulario de postulación.");
      return;
    }

    if (documentos.length === 0) {
      setError("Debe seleccionar al menos un documento del proyecto.");
      return;
    }

    setSubiendo(true);

    try {
      const formData = new FormData();

      formData.append("formulario", formulario);

      documentos.forEach((documento) => {
        formData.append("documentos", documento);
      });

      const response = await fetch(
        "http://localhost:8000/formularios/jobs",
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {
        const errorData = await response.json();

        throw new Error(
          errorData.detail || "Error al crear el job."
        );
      }

      const data = await response.json();

      console.log("Respuesta del backend:", data);

      setJobId(data.id);

    } catch (error) {
      console.error("Error al subir archivos:", error);

      if (error instanceof Error) {
        setError(error.message);
      } else {
        setError("Ocurrió un error al subir los archivos.");
      }

    } finally {
      setSubiendo(false);
    }
  };

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col px-6 py-8">

      {/* ========== SECCIÓN 1: Buscar recursos ========== */}
      <div className="flex items-center gap-4">
        <div className="h-px flex-1 bg-black" />
        <h1 className="text-2xl font-normal text-black">
          Consultor IA
        </h1>
        <div className="h-px flex-1 bg-black" />
      </div>

      <p className="mt-3 text-center text-sm text-black">
        Buscar recursos relacionados a mi proyecto
      </p>

      <div className="mt-8">
        <label htmlFor="proyecto" className="mb-2 block text-sm text-black">
          Cuentame de qué trata tu proyecto...
        </label>

        <div className="relative">
          <textarea
            id="proyecto"
            name="proyecto"
            rows={5}
            placeholder="Mi proyecto trata sobre..."
            className="w-full resize-none border border-black bg-neutral-200 px-4 py-3 pr-12 text-sm outline-none"
          />
          <button
            type="button"
            className="absolute right-3 top-3 flex h-8 w-8 items-center justify-center bg-neutral-700 text-white"
            aria-label="Enviar"
          >
            ✈
          </button>
        </div>
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-[2fr_1fr]">
        <div className="flex flex-col gap-4">
          {resultados.map((item) => (
            <article
              key={`${item.tipo}-${item.titulo}-${item.detalle}`}
              className="flex gap-4 bg-neutral-500 p-4 text-white"
            >
              <div className="flex h-12 w-12 shrink-0 items-center justify-center bg-neutral-700 text-2xl">
                {item.icono}
              </div>

              <div className="min-w-0 flex-1">
                <h2 className="text-base font-semibold">
                  “{item.titulo}”
                </h2>
                <p className="mt-2 text-xs leading-relaxed text-neutral-100">
                  <span className="font-semibold">Descripción:</span>{" "}
                  {item.descripcion}
                </p>
              </div>

              <div className="hidden shrink-0 text-right text-xs sm:block">
                <p>
                  <span className="font-semibold">Tipo:</span> {item.tipo}
                </p>
                <p className="mt-1">
                  <span className="font-semibold">Estado:</span> {item.estado}
                </p>
                <p className="mt-1">{item.detalle}</p>
              </div>
            </article>
          ))}
        </div>

        <aside className="bg-neutral-500 p-4 text-white">
          <div className="flex flex-col gap-5">
            {investigadores.map((persona) => (
              <div key={persona.nombre} className="flex gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-neutral-700 text-lg">
                  👤
                </div>
                <div className="text-xs leading-relaxed">
                  <p className="text-sm font-semibold">{persona.nombre}</p>
                  <p>
                    <span className="font-semibold">Institución:</span>{" "}
                    {persona.institucion}
                  </p>
                  <p>
                    <span className="font-semibold">Ocupación:</span>{" "}
                    {persona.ocupacion}
                  </p>
                  <p>
                    <span className="font-semibold">Área:</span> {persona.area}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </aside>
      </div>

      {/* ========== SECCIÓN 2: Formulario de postulación ========== */}
      <section className="mt-16">
        <div className="flex items-center gap-4">
          <div className="h-px flex-1 bg-black" />
          <h2 className="text-2xl font-normal text-black">
            Consultor IA
          </h2>
          <div className="h-px flex-1 bg-black" />
        </div>

        <p className="mt-3 text-center text-sm text-black">
          Completar un formulario de postulación
        </p>

        <div className="mx-auto mt-10 max-w-5xl">

        {/* FORMULARIO DE POSTULACIÓN */}

        <p className="mb-3 text-sm text-black">
          Selecciona el formulario de postulación
        </p>

        <label
          htmlFor="formulario-postulacion"
          className="flex min-h-32 cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-sky-500 bg-white px-6 py-8 text-center"
        >
          <span className="text-sm text-neutral-700">
            {formulario
              ? formulario.name
              : "Seleccionar formulario de postulación"}
          </span>

          <input
            id="formulario-postulacion"
            type="file"
            accept=".pdf"
            className="sr-only"
            onChange={handleFormularioChange}
          />
        </label>


        {/* DOCUMENTOS DEL PROYECTO */}

        <p className="mb-3 mt-8 text-sm text-black">
          Adjunta documentación sobre tu Proyecto...
        </p>

          <label
            htmlFor="archivos-proyecto"
            className="flex min-h-64 cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-sky-500 bg-white px-6 py-10 text-center"
          >
            <CloudUploadIcon />
            <span className="mt-4 text-sm text-neutral-700">
              Puede arrastrar y soltar archivos aquí para añadirlos
            </span>
            <input
              id="archivos-proyecto"
              name="documentos"
              type="file"
              multiple
              className="sr-only"
              onChange={handleDocumentosChange}
            />
          </label>

          {documentos.length > 0 && (
          <div className="mt-4 rounded-lg border border-neutral-300 bg-white p-4">

            <p className="mb-2 text-sm font-medium text-black">
              Documentos seleccionados:
            </p>

            <ul className="space-y-1">
              {documentos.map((documento, index) => (
                <li
                  key={`${documento.name}-${index}`}
                  className="text-sm text-neutral-700"
                >
                  {documento.name}
                </li>
              ))}
            </ul>

          </div>
        )}
        {error && (
          <div className="mt-4 rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {jobId && (
          <div className="mt-4 rounded-lg border border-green-300 bg-green-50 p-3 text-sm text-green-700">
            Job creado correctamente: #{jobId}
          </div>
        )}

          <div className="mt-4 flex justify-end">
            <button
              type="button"
              onClick={handleSubir}
              disabled={subiendo}
              className="border border-black bg-neutral-300 px-8 py-2 text-sm text-black disabled:cursor-not-allowed disabled:opacity-50"
            >
              {subiendo ? "Subiendo..." : "Subir"}
            </button>
          </div>
        </div>
      </section>

    </main>
  );
}

function CloudUploadIcon() {
  return (
    <svg
      width="72"
      height="72"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      className="text-black"
      aria-hidden="true"
    >
      <path d="M7 18a4.5 4.5 0 0 1 .4-9 5.5 5.5 0 0 1 10.7 1.5A3.5 3.5 0 0 1 17.5 18H7z" />
      <path d="M12 15V9" />
      <path d="M9.5 11.5 12 9l2.5 2.5" />
    </svg>
  );
}
