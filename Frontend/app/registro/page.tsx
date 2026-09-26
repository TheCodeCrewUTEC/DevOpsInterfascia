import AddableSelect from "../components/AddableSelect";

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
  "Investigador",
  "Inversor",
  "Emprendedor",
  "Estudiante",
  "Docente",
  "Otro",
];

export default function RegistroPage() {
  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 px-6 py-6">

      <div className="grid w-full grid-cols-1 gap-6 lg:grid-cols-2">

        {/* Imagen */}
        <div className="flex min-h-56 items-center justify-center border border-black bg-neutral-200 lg:min-h-0">
          <span className="text-4xl text-neutral-500">✕</span>
        </div>

        {/* Formulario */}
        <div>
          <h1 className="mb-4 text-2xl font-bold text-black">
            Crea una cuenta
          </h1>

          <form className="flex flex-col gap-2.5">

            <Field label="Nombre*" id="nombre" name="nombre" required />
            <Field label="Apellido*" id="apellido" name="apellido" required />
            <Field label="Email*" id="email" name="email" type="email" required />
            <Field
              label="Contraseña*"
              id="contrasena"
              name="contrasena"
              type="password"
              required
            />
            <Field
              label="Ingresa nuevamente tu contraseña*"
              id="contrasena2"
              name="contrasena2"
              type="password"
              required
            />

            <div className="flex flex-col gap-1">
              <label htmlFor="departamento-residencia" className="text-xs text-black">
                Departamento residencia*
              </label>
              <select
                id="departamento-residencia"
                name="departamentoResidencia"
                className="h-8 border border-black bg-neutral-300 px-2 text-sm text-black outline-none"
                required
                defaultValue=""
              >
                <option value="" disabled>
                  Selecciona un departamento...
                </option>
                {departamentos.map((departamento) => (
                  <option key={departamento} value={departamento}>
                    {departamento}
                  </option>
                ))}
              </select>
            </div>

            <AddableSelect
              id="departamento-actuacion"
              name="departamentoActuacion"
              label="Departamento/s de actuación"
              placeholder="Selecciona un departamento..."
              options={departamentos}
              required
            />

            <Field label="Celular" id="celular" name="celular" type="tel" />

            <AddableSelect
              id="instituciones"
              name="instituciones"
              label="Instituciones"
              placeholder="Selecciona institución..."
              options={instituciones}
              required
            />

            <AddableSelect
              id="roles"
              name="roles"
              label="Rol/es"
              placeholder="Selecciona rol..."
              options={roles}
              required
            />

            <button
              type="submit"
              className="mx-auto mt-3 w-40 border border-black bg-neutral-300 py-1.5 text-sm text-black"
            >
              Registrate
            </button>

          </form>
        </div>

      </div>

    </main>
  );
}

function Field({
  label,
  id,
  name,
  type = "text",
  required = false,
}: {
  label: string;
  id: string;
  name: string;
  type?: string;
  required?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-xs text-black">
        {label}
      </label>
      <input
        id={id}
        name={name}
        type={type}
        className="h-8 border border-black bg-neutral-300 px-2 text-sm outline-none"
        required={required}
      />
    </div>
  );
}
