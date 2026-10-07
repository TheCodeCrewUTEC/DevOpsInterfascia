"use client";

import { useActionState } from "react";
import AddableSelect from "@/app/components/AddableSelect";
import { DEPARTAMENTOS, INSTITUCIONES } from "@/lib/opciones-perfil";
import { guardarPerfil } from "./actions";
import { Aviso, Campo, ESTILO_INPUT } from "./campos";

export type Perfil = {
  email: string | null;
  nombre: string | null;
  apellido: string | null;
  celular: string | null;
  departamento_residencia: string | null;
  departamentos_actuacion: string[];
  instituciones: string[];
  perfil: string | null;
  perfil_otro: string | null;
};

export default function FormularioPerfil({ perfil }: { perfil: Perfil }) {
  const [estado, accion, guardando] = useActionState(guardarPerfil, null);

  return (
    <form
      action={accion}
      className="flex flex-col gap-5 rounded-3xl border border-pine/10 bg-paper p-6 shadow-sm"
    >
      <div className="grid gap-5 sm:grid-cols-2">
        <Campo id="nombre" label="Nombre" requerido>
          <input id="nombre" name="nombre" required defaultValue={perfil.nombre ?? ""} autoComplete="given-name" className={ESTILO_INPUT} />
        </Campo>
        <Campo id="apellido" label="Apellido" requerido>
          <input id="apellido" name="apellido" required defaultValue={perfil.apellido ?? ""} autoComplete="family-name" className={ESTILO_INPUT} />
        </Campo>
      </div>

      <Campo id="email" label="Correo electrónico" ayuda="Es tu usuario para iniciar sesión; no se puede cambiar.">
        <input id="email" value={perfil.email ?? ""} readOnly disabled className={ESTILO_INPUT} />
      </Campo>

      <Campo id="celular" label="Celular">
        <input
          id="celular"
          name="celular"
          type="tel"
          autoComplete="tel"
          pattern="\+?[0-9 ]{8,15}"
          title="Entre 8 y 15 dígitos, puede empezar con +"
          defaultValue={perfil.celular ?? ""}
          className={ESTILO_INPUT}
        />
      </Campo>

      <Campo id="departamento_residencia" label="Departamento de residencia" requerido>
        <select
          id="departamento_residencia"
          name="departamento_residencia"
          required
          defaultValue={perfil.departamento_residencia ?? ""}
          className={ESTILO_INPUT}
        >
          <option value="" disabled>
            Seleccioná un departamento
          </option>
          {DEPARTAMENTOS.map((departamento) => (
            <option key={departamento} value={departamento}>
              {departamento}
            </option>
          ))}
        </select>
      </Campo>

      <AddableSelect
        id="departamentos_actuacion"
        name="departamentos_actuacion"
        label="Departamentos de actuación"
        placeholder="Seleccioná un departamento"
        options={DEPARTAMENTOS}
        defaultValues={perfil.departamentos_actuacion}
        required
      />

      <AddableSelect
        id="instituciones"
        name="instituciones"
        label="Instituciones donde trabajás"
        placeholder="Seleccioná una institución"
        options={INSTITUCIONES}
        defaultValues={perfil.instituciones}
        required
      />

      <Campo id="perfil" label="Rol" ayuda="Lo asigna un administrador.">
        <input id="perfil" value={perfil.perfil ?? "Sin rol"} readOnly disabled className={ESTILO_INPUT} />
      </Campo>

      {perfil.perfil === "Otros" ? (
        <Campo id="perfil_otro" label="Especificá tu rol" requerido>
          <input
            id="perfil_otro"
            name="perfil_otro"
            required
            maxLength={255}
            defaultValue={perfil.perfil_otro ?? ""}
            className={ESTILO_INPUT}
          />
        </Campo>
      ) : null}

      {estado ? <Aviso ok={estado.ok} texto={estado.mensaje} /> : null}

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={guardando}
          className="rounded-full bg-pine px-5 py-2 text-sm font-medium text-ink shadow-sm transition hover:bg-pine-hover disabled:cursor-wait disabled:opacity-60"
        >
          {guardando ? "Guardando..." : "Guardar cambios"}
        </button>
      </div>
    </form>
  );
}
